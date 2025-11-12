import os.path
import shutil
import hashlib
import asyncio
import tempfile
import subprocess
import git
import time

from app.routes.api.v1.devagent.tasks.task_info.actions.set import action_set
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.gitcode.get_diff import get_diff, Diff
from app.utils.path import abspath_join

# project_root, patch_path, rule_path
DevagentTask = tuple[str, str, str]


ARKCOMPILER_DEVELOPMENT_RULES: tuple[str, str] = (
    "nazarovkonstantin/arkcompiler_development_rules",
    "main",
)


def populate_workdir(wd: str, diffs: list[Diff]) -> None:
    assert os.path.exists(wd), f"Working widectory {wd} does not exist"
    local_devagent_config = _create_devagent_config(wd)
    assert os.path.exists(
        local_devagent_config
    ), f"Local devagent config {local_devagent_config} does not exist"

    project, branch = ARKCOMPILER_DEVELOPMENT_RULES
    _clone_project(wd, project, branch)

    for diff in diffs:
        _clone_project(wd, diff.project, diff.summary.base_sha)


def get_diffs(urls: list[str]) -> list[Diff]:
    return [get_diff(url) for url in urls]


def load_rules(wd: str) -> dict[str, list[str]]:
    ark_dev_rules_root = _arkcompiler_development_rules_root(wd)

    review_rules = _load_rules_from_repo_root(ark_dev_rules_root)

    normalized_rules = _normalize_rules(wd, ark_dev_rules_root, review_rules)

    filtered_rules = dict(
        filter(lambda tupl: os.path.exists(tupl[0]), normalized_rules.items())
    )

    for dir, rules in filtered_rules.items():
        assert os.path.exists(dir), f"No directory {dir} was found"
        for rule in rules:
            assert os.path.exists(rule), f"No rule {rule} was found"

    return filtered_rules


def prepare_tasks(
    task_id: str, wd: str, rules: dict[str, list[str]], diffs: list[Diff]
) -> list[DevagentTask]:
    rules_to_diffs = _map_applicable_rules_to_diffs(wd, rules, diffs)

    tasks = list[DevagentTask]()

    emitted_diffs = dict[str, str]()

    for project_root, repo_rules_to_diffs in rules_to_diffs.items():
        assert os.path.exists(
            project_root
        ), f"Project root {project_root} does not exist"
        for rule, diff in repo_rules_to_diffs.items():
            diff_hash = _diff_hash(diff)
            existing_patch = emitted_diffs.get(diff_hash, None)
            if existing_patch:
                patch = existing_patch
            else:
                patch = _emit_patch(task_id, wd, diff)
                emitted_diffs.update({diff_hash: patch})
            tasks.append((project_root, patch, rule))

    return tasks


def store_task_info_to_redis(task_id: str, wd: str, tasks: list[DevagentTask]) -> None:
    task_info = dict()

    ark_dev_rules_root = _arkcompiler_development_rules_root(wd)
    task_info.update(
        {
            "rev_nazarovkonstantin/arkcompiler_development_rules": _get_revision(
                ark_dev_rules_root
            )
        }
    )

    task_info.update({"rev_egavrin/devagent": _get_revision("/devagent")})

    unique_patches = set()
    unique_projects = set()

    for task in tasks:
        project_root, patch_path, rule_path = task
        unique_projects.add(project_root)
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
            # last 2 folders of the path == project
            f"rev_{os.sep.join(os.path.normpath(project_path).split(os.sep)[-2:])}": _get_revision(
                project_path
            )
            for project_path in unique_projects
        }
    )

    task_info.update({"task_id": task_id})

    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)

    asyncio.get_event_loop().run_until_complete(
        action_set(redis=conn, query_params=task_info)
    )

    asyncio.get_event_loop().run_until_complete(conn.close())


###########
# private #
###########


def _map_applicable_rules_to_diffs(
    wd: str, rules: dict[str, list[str]], diffs: list[Diff]
) -> dict[str, dict[str, str]]:
    mapping = dict[str, dict[str, str]]()

    for diff in diffs:
        project_root = abspath_join(wd, f"{diff.project}")
        combined_diff = _combine_diff(diff)

        applicable_rules = set[str]()
        for file in diff.files:
            diff_file_abspath = abspath_join(project_root, file.file)
            for rule_dir, dir_rules in rules.items():
                if rule_dir == os.path.commonpath([rule_dir, diff_file_abspath]):
                    applicable_rules.update(dir_rules)

        mapping.update(
            {project_root: {rule: combined_diff for rule in applicable_rules}}
        )

    return mapping


def _combine_diff(diff: Diff) -> str:
    diffs = list[str]()

    for file in diff.files:
        diffs.append(file.diff)

    return "\n\n".join(diffs)


def _arkcompiler_development_rules_root(wd: str) -> str:
    project, _ = ARKCOMPILER_DEVELOPMENT_RULES
    return abspath_join(wd, project)


def _clone_project(wd: str, project: str, branch: str) -> None:
    root = abspath_join(wd, project)
    os.makedirs(root, exist_ok=True)
    assert os.path.exists(root), f"Root {root} for cloning does not exist"
    clone = _clone(dir=root, url=f"https://gitcode.com/{project}.git")
    clone.git.checkout(branch)


def _diff_hash(diff: str) -> str:
    return hashlib.sha256(diff.encode()).hexdigest()


def _emit_patch(task_id: str, wd: str, diff: str) -> str:
    patches_dir = abspath_join(wd, ".patches.d")
    os.makedirs(patches_dir, exist_ok=True)
    assert os.path.exists(patches_dir), f"Patches dir {patches_dir} does not exist"

    temp = tempfile.NamedTemporaryFile(
        prefix=f"patch_{task_id}_", dir=patches_dir, delete=False
    )
    temp.write(diff.encode("utf-8"))
    patch_path = temp.name
    temp.close()

    assert os.path.exists(patch_path), f"Patch {patch_path} does not exist"

    return patch_path


def _load_rules_from_config(cfg: str) -> dict[str, set[str]]:
    lines = cfg.split("\n")

    review_rules = dict[str, set[str]]()

    for raw_line in lines:
        line = raw_line.strip()

        if line.startswith("#"):
            continue

        parsed_line = line.split()

        if len(parsed_line) < 2:
            continue

        dir = parsed_line[0].removeprefix("/").removesuffix("/")
        rules = parsed_line[1:]
        existing_rules = review_rules.get(dir, set())
        existing_rules.update(rules)
        review_rules.update({dir: existing_rules})
    return review_rules


def _load_rules_from_repo_root(project_root: str) -> dict[str, set[str]]:
    assert os.path.exists(
        project_root
    ), f"No project root {project_root} for development rules was found"

    review_rules = dict[str, set[str]]()

    rules_config = abspath_join(project_root, ".REVIEW_RULES")
    assert os.path.exists(
        rules_config
    ), f"No config file {rules_config} was found in the project root {project_root}"

    with open(rules_config) as cfg:
        content = cfg.read()
        review_rules = _load_rules_from_config(content)

    return review_rules


def _normalize_rules(
    wd: str, rules_project_root: str, rules: dict[str, set[str]]
) -> dict[str, list[str]]:
    review_rules = dict[str, list[str]]()

    rules_dir = abspath_join(rules_project_root, "REVIEW_RULES")
    assert os.path.exists(
        rules_dir
    ), f"No rules dir {rules_dir} was found in the project_root root {rules_project_root}"

    for dir, dir_rules in rules.items():
        dir_abs = abspath_join(wd, dir)
        rules_abs = list(
            map(
                lambda rule: abspath_join(rules_dir, rule),
                dir_rules,
            )
        )
        review_rules.update({dir_abs: sorted(rules_abs)})

    return review_rules


def _clone(url: str, dir: str, retries: int = 5) -> git.Repo:
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

    assert (
        res.returncode == 0
    ), f"Return code of cmd {cmd} was {res.returncode}. expected 0"
    stdout = res.stdout.decode("utf-8")

    return stdout.strip()


def _create_devagent_config(wd: str) -> str:
    devagent_config_path = os.path.abspath(os.path.join(wd, ".devagent.toml"))
    with open(devagent_config_path, "w") as cfg:
        cfg.write(f"provider = {CONFIG.DEVAGENT_PROVIDER}\n")
        cfg.write(f"model = {CONFIG.DEVAGENT_MODEL}\n")
        cfg.write(f"api_key = {CONFIG.DEVAGENT_API_KEY}\n")
        cfg.write(f"auto_approve_code = false\n")
    return devagent_config_path
