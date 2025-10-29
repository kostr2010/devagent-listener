import os.path
import shutil
import hashlib
import asyncio
import tempfile
import subprocess
import git
import time


from app.api.v1.devagent.tasks.task_info.actions.set import task_info_set
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.remote.get_diff import get_diff
from app.utils.validation import validate_result
from app.utils.path import abspath_join

ARKCOMPILER_DEVELOPMENT_RULES_REPO = (
    "arkcompiler_development_rules",
    "nazarovkonstantin",
    "main",
)


def populate_workdir(wd: str, diffs: list[dict]) -> None:
    repo, owner, branch = ARKCOMPILER_DEVELOPMENT_RULES_REPO
    dir = abspath_join(wd, repo)
    url = f"https://gitcode.com/{owner}/{repo}.git"
    repo = _clone(dir=dir, url=url)
    repo.git.checkout(branch)

    for diff in diffs:
        repo = diff["repo"]
        owner = diff["owner"]
        base_sha = diff["summary"]["base_sha"]

        dir = abspath_join(wd, repo)
        url = f"https://gitcode.com/{owner}/{repo}.git"
        repo = _clone(dir=dir, url=url)
        repo.git.checkout(base_sha)

        global_devagent_config = "/.devagent.toml"
        assert os.path.exists(global_devagent_config)

        local_devagent_config = abspath_join(dir, ".devagent.toml")
        shutil.copyfile(global_devagent_config, local_devagent_config)
        assert os.path.exists(local_devagent_config)


def get_diffs(urls: list[str]) -> list[dict]:
    return [get_diff(url) for url in urls]


@validate_result(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "load_rules return value shema",
        "description": "Return value schema of load_rules API",
        "type": "object",
        "patternProperties": {
            # TODO: fix when new rules are added or patch format changes
            "^.*$": {
                "description": "Directory name mapped to the relevant rules for it",
                "type": "array",
                "items": {"type": "string", "pattern": "^.*ETS.*.md$"},
            },
        },
        "additionalProperties": False,
    }
)
def load_rules(wd: str) -> dict:
    repo, _, _ = ARKCOMPILER_DEVELOPMENT_RULES_REPO
    repo_root = abspath_join(wd, repo)

    review_rules = _load_rules_from_repo_root(repo_root)

    normalized_rules = _normalize_rules(wd, repo_root, review_rules)

    filtered_rules = _filter_rules(normalized_rules)

    return filtered_rules


def prepare_tasks(
    task_id: str, wd: str, rules: dict, diffs: list[dict]
) -> list[tuple[str, str, str]]:
    rules_to_diffs = _match_rules_to_diffs(wd, rules, diffs)

    tasks = []

    emitted_diffs = {}

    for repo_root, repo_rules_to_diffs in rules_to_diffs.items():
        for rule, diff in repo_rules_to_diffs.items():
            diff_hash = _diff_hash(diff)
            existing_patch = emitted_diffs.get(diff_hash, None)
            patch = None
            if existing_patch:
                patch = existing_patch
            else:
                patch = _emit_patch(task_id, wd, diff)
                emitted_diffs.update({diff_hash: patch})
            tasks.append((repo_root, patch, rule))

    return tasks


def store_task_info_to_redis(task_id: str, wd: str, tasks: list) -> None:
    task_info = {}

    arkcompiler_development_rules, _, _ = ARKCOMPILER_DEVELOPMENT_RULES_REPO
    task_info.update(
        {
            "rev_arkcompiler_development_rules": _get_revision(
                abspath_join(wd, arkcompiler_development_rules)
            )
        }
    )
    task_info.update({"rev_devagent": _get_revision("/devagent")})

    unique_patches = set()
    unique_repos = set()

    for task in tasks:
        repo, patch_path, rule_path = task
        unique_repos.add(repo)
        unique_patches.add(patch_path)
        rule_name = os.path.splitext(os.path.basename(rule_path))[0]
        patch_name = os.path.basename(patch_path)
        task_info.update({rule_name: patch_name})

    for patch in unique_patches:
        patch_content = open(patch).read()
        patch_name = os.path.basename(patch)
        task_info.update({patch_name: patch_content})

    task_info.update(
        {
            f"rev_{os.path.basename(repo_root)}": _get_revision(repo_root)
            for repo_root in unique_repos
        }
    )

    task_info.update({"task_id": task_id})

    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)

    asyncio.get_event_loop().run_until_complete(
        task_info_set(redis=conn, query_params=task_info)
    )

    asyncio.get_event_loop().run_until_complete(conn.close())


###########
# private #
###########


def _diff_hash(diff: str) -> str:
    return hashlib.sha256(diff.encode()).hexdigest()


def _match_rules_to_diffs(
    wd: str,
    rules: dict,
    diffs: list,
) -> dict:
    combined_diffs = {}

    for diff in diffs:
        diff_repo = diff["repo"]
        diff_files = diff["files"]

        diff_repo_root = abspath_join(wd, diff_repo)

        repo_combined_diffs = {}

        for diff_file in diff_files:
            # diff_file_path = diff_file["file"]
            # diff_file_abspath = os.path.abspath(
            #     os.path.join(diff_repo_root, diff_file_path)
            # )

            applicable_rules = set()

            for rule_dir, review_rules in rules.items():
                # NOTE: old matching algorithm -- minimal patch for each rule
                # if rule_dir == os.path.commonpath([rule_dir, diff_file_abspath]):
                if diff_repo_root == os.path.commonpath([diff_repo_root, rule_dir]):
                    applicable_rules.update(review_rules)

            if len(applicable_rules) == 0:
                continue

            for rule in applicable_rules:
                rule_combined_diff = repo_combined_diffs.get(rule, "")
                rule_combined_diff += diff_file["diff"] + "\n\n"
                repo_combined_diffs[rule] = rule_combined_diff

        combined_diffs[diff_repo_root] = repo_combined_diffs

    return combined_diffs


def _emit_patch(task_id: str, wd: str, diff: str) -> str:
    patches_dir = abspath_join(wd, ".patches.d")
    os.makedirs(patches_dir, exist_ok=True)
    assert os.path.exists(patches_dir)

    temp = tempfile.NamedTemporaryFile(
        prefix=f"patch_{task_id}_", dir=patches_dir, delete=False
    )
    temp.write(diff.encode("utf-8"))
    patch_path = temp.name
    temp.close()

    assert os.path.exists(patch_path)

    return patch_path


def _load_rules_from_config(cfg: str) -> dict:
    lines = cfg.split("\n")

    review_rules = {}

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("#"):
            continue

        parsed_line = line.split()

        if len(parsed_line) < 2:
            continue

        dir = parsed_line[0].removeprefix("/").removesuffix("/")
        rules = parsed_line[1:]
        existing_rules = set(review_rules.get(dir, []))
        existing_rules.update(rules)
        review_rules.update({dir: existing_rules})
    return review_rules


def _load_rules_from_repo_root(repo_root: str) -> dict:
    review_rules = {}

    rules_config = abspath_join(repo_root, ".REVIEW_RULES")
    if not os.path.exists(rules_config):
        print(f"No {rules_config} file was found in the repo root {repo_root}")
        return review_rules

    with open(rules_config) as cfg:
        content = cfg.read()
        review_rules = _load_rules_from_config(content)

    return review_rules


def _filter_rules(normalized_rules: dict) -> dict:
    relevant_rules = {}

    for dir, rules in normalized_rules.items():
        if not os.path.exists(dir):
            # e.g. rules for the other repos
            continue
        for rule in rules:
            assert os.path.exists(rule)
        relevant_rules.update({dir: rules})

    return relevant_rules


def _normalize_rules(wd: str, rules_repo_root: str, rules: dict):
    review_rules = {}

    rules_dir = abspath_join(rules_repo_root, "REVIEW_RULES")
    if not os.path.exists(rules_dir):
        print(f"No {rules_dir} dir was found in the repo root {rules_repo_root}")
        return review_rules

    for dir, rules in rules.items():
        dir_abs = abspath_join(wd, dir)
        rules_abs = list(
            map(
                lambda rule: abspath_join(rules_dir, rule),
                rules,
            )
        )
        review_rules.update({dir_abs: sorted(rules_abs)})

    return review_rules


def _clone(url: str, dir: str | None = None, retries: int = 5) -> git.Repo:
    tries_left = retries

    while tries_left > 0:
        try:
            return git.Repo.clone_from(
                url,
                dir,
                allow_unsafe_protocols=True,
                # depth=1,
            )
        except Exception as e:
            if tries_left > 0:
                tries_left -= 1
                print(
                    f"[tries left: {tries_left}] Repo clone failed with the exception {e}"
                )
                time.sleep(5 * (5 - tries_left))

    return git.Repo.clone_from(
        url,
        dir,
        allow_unsafe_protocols=True,
    )


def _get_revision(root: str) -> str:
    cmd = ["git", "-C", root, "rev-parse", "HEAD"]

    res = subprocess.run(
        cmd,
        capture_output=True,
    )

    assert res.returncode == 0
    stdout = res.stdout.decode("utf-8")

    return stdout.strip()
