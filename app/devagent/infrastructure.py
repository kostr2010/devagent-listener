import os.path
import git
import time
import shutil
import json
import subprocess
import tempfile

from app.remote.get_diff import get_diff

DEVAGENT_RULES_REPO = "arkcompiler_development_rules"
DEVAGENT_REVIEW_RULES_DIR = "REVIEW_RULES"
DEVAGENT_REVIEW_RULES_CONFIG = ".REVIEW_RULES"


def worker_get_range(n_tasks: int, group_idx: int, group_size: int):
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


def devagent_review_patch(repo_root: str, patch_path: str, rule_path: str):
    try:
        devagent_result = None

        with tempfile.TemporaryDirectory(dir=repo_root) as cwd:
            cmd = ["devagent", "review", "--json", "--rule", rule_path, patch_path]

            print(f"Started devagent:\ncwd={cwd}\ncmd={' '.join(cmd)}")

            devagent_result = subprocess.run(
                cmd,
                capture_output=True,
                cwd=cwd,
            )

        stderr = devagent_result.stderr.decode("utf-8")
        if len(stderr) > 0 and "Error" in stderr:
            return {
                "repo": os.path.basename(repo_root),
                "error": {"message": stderr, "patch": patch_path, "rule": rule_path},
            }

        stdout = devagent_result.stdout.decode("utf-8")

        return {"repo": os.path.basename(repo_root), "result": stdout}
    except Exception as e:
        return {"repo": os.path.basename(repo_root), "error": f"{str(e)}"}


def clean_workdir(wd: str):
    shutil.rmtree(wd, ignore_errors=True)


def process_review_result(devagent_review: list):
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
            violations = json.loads(review["result"])["violations"]
            res = results.get(repo, [])
            res.append(violations)
            results.update({repo: res})
        else:
            continue

    results_filtered = {
        repo: [
            violation for violation_list in violations for violation in violation_list
        ]
        for repo, violations in results.items()
    }

    final_result = {
        "errors": errors,
        "results": results_filtered,
    }

    return final_result


def populate_workdir(wd: str):
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


def get_diffs(urls: list):
    return [get_diff(url) for url in urls]


def _combine_diffs_by_rules(
    wd: str,
    rules: dict,
    diffs: list,
) -> dict:
    combined_diffs = {}

    for diff in diffs:
        diff_repo = diff["repo"]
        diff_files = diff["files"]

        repo_combined_diffs = {}

        diff_repo_root = os.path.abspath(os.path.join(wd, diff_repo))

        for diff_file in diff_files:
            diff_file_path = diff_file["file"]
            diff_file_abspath = os.path.abspath(
                os.path.join(diff_repo_root, diff_file_path)
            )

            applicable_rules = set()

            for rule_dir, review_rules in rules.items():
                if rule_dir == os.path.commonpath([rule_dir, diff_file_abspath]):
                    applicable_rules.update(review_rules)

            if len(applicable_rules) == 0:
                continue

            for rule in applicable_rules:
                rule_combined_diff = repo_combined_diffs.get(rule, "")
                rule_combined_diff += diff_file["diff"] + "\n\n"
                repo_combined_diffs[rule] = rule_combined_diff

        combined_diffs[diff_repo_root] = repo_combined_diffs

    return combined_diffs


def _emit_diff(diff: str) -> str:
    # FIXME: remove this. generate temp patch file while devagent can't parse input as string

    temp = tempfile.NamedTemporaryFile(suffix=f".patch", delete=False)
    temp.write(diff.encode("utf-8"))
    patch_path = temp.name
    temp.close()

    return patch_path


def prepare_tasks(wd: str, rules: dict, diffs: list) -> list:
    combined_diffs = _combine_diffs_by_rules(wd, rules, diffs)

    tasks = []

    for repo_root, repo_combined_diffs in combined_diffs.items():
        for rule, diff in repo_combined_diffs.items():
            patch = _emit_diff(diff)
            tasks.append((repo_root, patch, rule))

    return tasks


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


def load_rules(wd: str) -> dict:
    repo_root = os.path.abspath(os.path.join(wd, DEVAGENT_RULES_REPO))

    review_rules = _load_rules_from_repo_root(repo_root)

    normalized_rules = _normalize_rules(wd, repo_root, review_rules)

    for dir, rules in normalized_rules.items():
        assert os.path.exists(dir)
        for rule in rules:
            assert os.path.exists(rule)

    return normalized_rules
