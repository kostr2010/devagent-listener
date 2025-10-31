import os.path
import git
import time
import shutil
import json
import subprocess
import tempfile
import hashlib
import asyncio

from app.api.v1.devagent.tasks.task_info.actions.set import task_info_set
from app.api.v1.devagent.tasks.task_info.actions.get import task_info_get
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.remote.get_diff import get_diff
from app.postgres.models import Error
from app.postgres.infrastructure import save_patch_if_does_not_exist
from app.postgres.database import SQL_SESSION

DEVAGENT_ROOT = "/devagent"
DEVAGENT_RULES_REPO = "arkcompiler_development_rules"
DEVAGENT_REVIEW_RULES_DIR = "REVIEW_RULES"
DEVAGENT_REVIEW_RULES_CONFIG = ".REVIEW_RULES"

PATCHES_DIR = ".patches.d"


def populate_workdir(wd: str) -> None:
    DEVAGENT_CONFIG_PATH = "/.devagent.toml"
    assert os.path.exists(DEVAGENT_CONFIG_PATH)

    repos = [
        ("arkcompiler_runtime_core", "openharmony", "OpenHarmony_feature_20250702"),
        ("arkcompiler_ets_frontend", "openharmony", "OpenHarmony_feature_20250702"),
        (DEVAGENT_RULES_REPO, "nazarovkonstantin", "main"),
    ]

    for r in repos:
        repo, owner, branch = r
        clone_dst = os.path.abspath(os.path.join(wd, repo))
        url = f"https://gitcode.com/{owner}/{repo}.git"

        should_retry = True
        tries_left = 5

        while should_retry:
            try:
                git.Repo.clone_from(
                    url,
                    clone_dst,
                    allow_unsafe_protocols=True,
                    branch=branch,
                    depth=1,
                )
            except Exception as e:
                if tries_left > 0:
                    tries_left -= 1
                    print(
                        f"[tries left: {tries_left}] Repo clone failed with the exception {e}"
                    )
                    time.sleep(5 * (5 - tries_left))
                else:
                    raise e
            else:
                should_retry = False

        local_devagent_config_path = os.path.abspath(
            os.path.join(clone_dst, ".devagent.toml")
        )
        shutil.copyfile(DEVAGENT_CONFIG_PATH, local_devagent_config_path)

        assert os.path.exists(local_devagent_config_path)

    patches_dir = os.path.abspath(os.path.join(wd, PATCHES_DIR))
    os.makedirs(patches_dir, exist_ok=False)
    assert os.path.exists(patches_dir)


def get_diffs(urls: list) -> list:
    return [get_diff(url) for url in urls]


def load_rules(wd: str) -> dict:
    repo_root = os.path.abspath(os.path.join(wd, DEVAGENT_RULES_REPO))

    review_rules = _load_rules_from_repo_root(repo_root)

    normalized_rules = _normalize_rules(wd, repo_root, review_rules)

    for dir, rules in normalized_rules.items():
        assert os.path.exists(dir)
        for rule in rules:
            assert os.path.exists(rule)

    return normalized_rules


def prepare_tasks(
    task_id: str, wd: str, rules: dict, diffs: list[dict]
) -> list[tuple[str, str, str]]:
    rules_to_diffs = _match_rules_to_diffs(wd, rules, diffs)

    tasks = []

    emitted_diffs = {}

    for repo_root, repo_rules_to_diffs in rules_to_diffs.items():
        for rule, diff in repo_rules_to_diffs.items():
            diff_hash = hashlib.sha256(diff.encode()).hexdigest()
            existing_patch = emitted_diffs.get(diff_hash, None)
            patch = None
            if existing_patch:
                patch = existing_patch
            else:
                patch = _emit_diff(task_id, wd, diff)
                emitted_diffs.update({diff_hash: patch})
            tasks.append((repo_root, patch, rule))

    return tasks


def store_task_info_to_redis(task_id: str, wd: str, tasks: list) -> None:
    task_info = {}

    task_info.update(
        {
            "rev_arkcompiler_development_rules": _get_arkcompiler_development_rules_revision(
                wd
            )
        }
    )
    task_info.update({"rev_devagent": _get_devagent_revision()})

    unique_patches = set()

    for task in tasks:
        _, patch_path, rule_path = task
        unique_patches.add(patch_path)
        rule_name = os.path.splitext(os.path.basename(rule_path))[0]
        patch_name = os.path.basename(patch_path)
        task_info.update({rule_name: patch_name})

    for patch in unique_patches:
        patch_content = open(patch).read()
        patch_name = os.path.basename(patch)
        task_info.update({patch_name: patch_content})

    task_info.update({"task_id": task_id})

    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)

    res = asyncio.get_event_loop().run_until_complete(
        task_info_set(redis=conn, query_params=task_info)
    )

    values_written = res.get(task_id)

    assert values_written != None
    assert values_written == 1

    asyncio.get_event_loop().run_until_complete(conn.close())


def devagent_review_patch(repo_root: str, patch_path: str, rule_path: str) -> dict:
    try:
        devagent_result = None

        cmd = ["devagent", "review", "--json", "--rule", rule_path, patch_path]

        print(f"Started devagent:\ncwd={repo_root}\ncmd={' '.join(cmd)}")

        devagent_result = subprocess.run(
            cmd,
            capture_output=True,
            cwd=repo_root,
        )

        stderr = devagent_result.stderr.decode("utf-8")
        if len(stderr) > 0 and "Error" in stderr:
            return {
                "repo": os.path.basename(repo_root),
                "error": {
                    "message": stderr,
                    "patch": os.path.basename(patch_path),
                    "rule": os.path.basename(rule_path),
                },
            }

        stdout = devagent_result.stdout.decode("utf-8")

        return {"repo": os.path.basename(repo_root), "result": json.loads(stdout)}
    except Exception as e:
        return {
            "repo": os.path.basename(repo_root),
            "error": {
                "message": f"{str(e)}",
                "patch": os.path.basename(patch_path),
                "rule": os.path.basename(rule_path),
            },
        }


def worker_get_range(n_tasks: int, group_idx: int, group_size: int) -> tuple[int, int]:
    assert group_size > 0
    assert 0 <= group_idx
    assert group_idx < group_size

    per_worker = n_tasks // group_size
    n_residue_tasks = n_tasks % group_size
    per_residue_worker = 1
    is_residue_worker = group_idx < n_residue_tasks

    # first n workers separate residue between themselves

    n_residue_workers_before = n_residue_tasks - is_residue_worker * (
        n_residue_tasks - group_idx
    )
    start_idx = group_idx * per_worker + n_residue_workers_before * per_residue_worker
    end_idx = (group_idx + 1) * per_worker + (
        n_residue_workers_before + 1 * is_residue_worker
    ) * per_residue_worker

    return start_idx, end_idx


def store_errors_to_postgres(
    task_id: str,
    wd: str,
    processed_review: dict,
) -> None:
    errors: dict = processed_review.get("errors", {})

    if len(errors.items()) == 0:
        return

    asyncio.get_event_loop().run_until_complete(
        _store_errors_to_postgres(task_id, wd, errors)
    )


def clean_workdir(wd: str) -> None:
    shutil.rmtree(wd, ignore_errors=True)


def process_review_result(rules: dict, devagent_review: list) -> dict:
    results = {}
    errors = {}

    devagent_review_flat = []
    for review_chunk in devagent_review:
        for review in review_chunk:
            devagent_review_flat.append(review)

    for review in devagent_review_flat:
        repo = review["repo"]
        if "error" in review:
            error = review["error"]
            res = errors.get(repo, [])
            res.append(error)
            errors.update({repo: res})
        elif "result" in review:
            violations = review["result"]["violations"]
            res = results.get(repo, [])
            res.append(violations)
            results.update({repo: res})
        else:
            continue

    flattened_results = {
        repo: [
            violation for violation_list in violations for violation in violation_list
        ]
        for repo, violations in results.items()
    }

    # FIXME: filter results by rules

    final_result = {
        "errors": errors,
        "results": results_filtered,
    }

    return final_result


###########
# private #
###########


def _get_devagent_revision() -> str:
    return _get_repo_revision(DEVAGENT_ROOT)


def _get_arkcompiler_development_rules_revision(wd: str) -> str:
    root = os.path.abspath(os.path.join(wd, DEVAGENT_RULES_REPO))
    return _get_repo_revision(root)


def _get_repo_revision(root: str) -> str:
    cmd = ["git", "-C", root, "rev-parse", "HEAD"]

    res = subprocess.run(
        cmd,
        capture_output=True,
    )

    assert res.returncode == 0
    stdout = res.stdout.decode("utf-8")

    return stdout.strip()


def _match_rules_to_diffs(
    wd: str,
    rules: dict,
    diffs: list,
) -> dict:
    combined_diffs = {}

    for diff in diffs:
        diff_repo = diff["repo"]
        diff_files = diff["files"]

        diff_repo_root = os.path.abspath(os.path.join(wd, diff_repo))

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


def _emit_diff(task_id: str, wd: str, diff: str) -> str:
    dir = os.path.abspath(os.path.join(wd, PATCHES_DIR))
    temp = tempfile.NamedTemporaryFile(
        prefix=f"{task_id}-", suffix="-patch", dir=dir, delete=False
    )
    temp.write(diff.encode("utf-8"))
    patch_path = temp.name
    temp.close()

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

    rules_config_name = DEVAGENT_REVIEW_RULES_CONFIG
    rules_config = os.path.abspath(os.path.join(repo_root, rules_config_name))
    if not os.path.exists(rules_config):
        print(f"No {rules_config_name} file was found in the repo root {repo_root}")
        return review_rules

    with open(rules_config) as cfg:
        content = cfg.read()
        review_rules = _load_rules_from_config(content)

    return review_rules


def _normalize_rules(wd: str, rules_repo_root: str, rules: dict):
    rules_dir = os.path.abspath(
        os.path.join(rules_repo_root, DEVAGENT_REVIEW_RULES_DIR)
    )
    review_rules = {}
    if not os.path.exists(rules_dir):
        print(
            f"No {DEVAGENT_REVIEW_RULES_DIR} dir was found in the repo root {rules_repo_root}"
        )
        return review_rules
    for dir, rules in rules.items():
        dir_abs = os.path.abspath(os.path.join(wd, dir))
        rules_abs = list(
            map(
                lambda rule: os.path.abspath(os.path.join(rules_dir, rule)),
                rules,
            )
        )
        review_rules.update({dir_abs: sorted(rules_abs)})

    return review_rules


async def _store_errors_to_postgres(
    task_id: str,
    wd: str,
    errors: dict,
) -> None:
    rev_arkcompiler_development_rules = _get_arkcompiler_development_rules_revision(wd)
    rev_devagent = _get_devagent_revision()

    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)
    task_info = await task_info_get(payload=task_id, redis=conn)
    await conn.close()

    if task_info == None or len(task_info.keys()) == 0:
        print(f"No task info for task_id {task_id}")
        return

    async with SQL_SESSION() as postgres:
        orm_errors: list[Error] = []

        for _, errors in errors.items():
            for error in errors:
                patch = error["patch"]
                rule = error["rule"]
                message = error["message"]
                content = task_info[patch]

                await save_patch_if_does_not_exist(postgres, patch, content)

                orm_error: Error = Error(
                    rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
                    rev_devagent=rev_devagent,
                    patch=patch,
                    rule=rule,
                    message=message,
                )

                orm_errors.append(orm_error)

        postgres.add_all(orm_errors)
        await postgres.commit()
