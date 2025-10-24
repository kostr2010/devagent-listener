import subprocess
import os.path
import shutil
import json
import git
import tempfile
import time
import logging
import celery

from .utils.timer import Timer
from .remote.get_diff import get_diff
from .celery import celery_instance
from .config import CONFIG

DEVAGENT_LOG = logging.getLogger(__name__)
DEVAGENT_LOG.setLevel(logging.INFO)

DEVAGENT_SUPPORTED_REPOS = ["arkcompiler_runtime_core", "arkcompiler_ets_frontend"]
DEVAGENT_REVIEW_RULES_CONFIG = "REVIEW_RULES"
DEVAGENT_REVIEW_RULES_DIR = ".REVIEW_RULES"

DEVAGENT_WORKER_NAME = "devagent_worker"

devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.DEVAGENT_REDIS_DB)


def devagent_review(urls: list):
    workdir = tempfile.mkdtemp()
    return celery.chain(devagent_review_setup.s(workdir), devagent_review_prs.s(urls))


def devagent_cleanup(
    wd: str,
):
    shutil.rmtree(wd, ignore_errors=True)


def devagent_review_prettify(devagent_review: list):
    results = {}
    errors = {}

    for elem in devagent_review:
        print(json.dumps(elem, indent=2))
        repo = elem["repo"]
        if "error" in elem:
            error = elem["error"]
            res = errors.get(repo, [])
            res.append(error)
            errors.update({repo: res})
        elif "result" in elem:
            violations = json.loads(elem["result"])["violations"]
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

    final_result = {"errors": errors, "results": results_filtered}

    return final_result


@devagent_worker.task
def devagent_review_wrapup(devagent_review: list, wd: str):
    devagent_cleanup(wd)
    return devagent_review_prettify(devagent_review)


@devagent_worker.task
def devagent_review_setup(wd: str) -> str:
    with Timer():
        for repo in DEVAGENT_SUPPORTED_REPOS:
            clone_dst = os.path.abspath(os.path.join(wd, repo))
            url = f"https://gitcode.com/nazarovkonstantin/{repo}.git"

            should_retry = True
            tries_left = 5

            while should_retry:
                try:
                    git.Repo.clone_from(
                        url,
                        clone_dst,
                        allow_unsafe_protocols=True,
                        branch="feature/review_rules_test",
                        depth=1,
                    )
                except Exception as e:
                    if tries_left > 0:
                        tries_left -= 1
                        DEVAGENT_LOG.info(
                            f"[tries left: {tries_left}] Repo clone failed with the exception {e}"
                        )
                        time.sleep(5 * (5 - tries_left))
                    else:
                        raise e
                else:
                    should_retry = False
    return wd


@devagent_worker.task
def devagent_get_diff(url: str) -> dict:
    get_diff(url)


def load_rules(workdir: str) -> dict:
    dir_to_rules = {}

    with Timer():
        for repo in DEVAGENT_SUPPORTED_REPOS:
            repo_root = os.path.abspath(os.path.join(workdir, repo))
            rules_config = os.path.abspath(
                os.path.join(repo_root, DEVAGENT_REVIEW_RULES_CONFIG)
            )
            rules_dir = os.path.abspath(
                os.path.join(repo_root, DEVAGENT_REVIEW_RULES_DIR)
            )

            with open(rules_config) as cfg:
                for line in cfg:
                    parsed_line = line.strip().split()
                    path = parsed_line[0].removeprefix("/")
                    rules = parsed_line[1:]
                    abs_path = os.path.abspath(os.path.join(repo_root, path))
                    abs_rules = list(
                        map(
                            lambda rule: os.path.abspath(os.path.join(rules_dir, rule)),
                            rules,
                        )
                    )
                    dir_to_rules.update({abs_path: abs_rules})

    return dir_to_rules


def group_diffs_by_rule(diffs: list, rules: dict, wd: str) -> dict:
    rule_to_diffs = {}

    for diff in diffs:
        diff_repo = diff["repo"]
        diff_files = diff["files"]

        diff_repo_abspath = os.path.abspath(os.path.join(wd, diff_repo))

        for diff_file in diff_files:
            diff_file_path = diff_file["file"]
            diff_file_abspath = os.path.abspath(
                os.path.join(diff_repo_abspath, diff_file_path)
            )

            applicable_rules = set()

            for dir_abspath, rules_abspaths in rules.items():
                if dir_abspath == os.path.commonpath([dir_abspath, diff_file_abspath]):
                    applicable_rules.update(rules_abspaths)

            if len(applicable_rules) == 0:
                continue

            for rule in applicable_rules:
                rule_combined_diff = rule_to_diffs.get(rule, [])
                rule_combined_diff.append(diff_file["diff"])
                rule_to_diffs[rule] = rule_combined_diff

    return rule_to_diffs


def diff_to_patch(diff: str) -> str:
    # FIXME: remove this. generate temp patch file while devagent can't parse input as string

    temp = tempfile.NamedTemporaryFile(suffix=f".patch", delete=False)
    temp.write(diff.encode("utf-8"))
    patch_path = temp.name
    temp.close()

    return patch_path


def extract_repo_from_rule_path(rule_path: str) -> str:
    rule_dir = os.path.dirname(rule_path)
    repo_dir = os.path.abspath(os.path.join(rule_dir, ".."))

    return repo_dir


@devagent_worker.task
def devagent_review_patch(cwd: str, patch_path: str, rule_path: str):
    try:
        cmd = ["devagent", "review", "--json", "--rule", rule_path, patch_path]

        DEVAGENT_LOG.info(f"Started devagent:\ncwd={cwd}\ncmd={' '.join(cmd)}")

        devagent_result = None
        with Timer():
            devagent_result = subprocess.run(
                cmd,
                capture_output=True,
                cwd=cwd,
            )

        stderr = devagent_result.stderr.decode("utf-8")
        if len(stderr) > 0 and "Error" in stderr:
            return {
                "repo": os.path.basename(cwd),
                "error": {"message": stderr, "patch": patch_path, "rule": rule_path},
            }

        stdout = devagent_result.stdout.decode("utf-8")

        return {"repo": os.path.basename(cwd), "result": stdout}
    except Exception as e:
        return {"repo": os.path.basename(cwd), "error": f"{str(e)}"}


@devagent_worker.task()
def devagent_review_prs(
    wd: str,
    urls: list,
):
    rules = load_rules(wd)
    diffs = [get_diff(url) for url in urls]

    diffs_by_rule = group_diffs_by_rule(diffs, rules, wd)

    diff_by_rule = {rule: "\n\n".join(diffs) for rule, diffs in diffs_by_rule.items()}

    patch_by_rule = {rule: diff_to_patch(diff) for rule, diff in diff_by_rule.items()}

    return celery.chord(
        devagent_review_patch.s(
            extract_repo_from_rule_path(rule_path), patch_path, rule_path
        )
        for rule_path, patch_path in patch_by_rule.items()
    )(devagent_review_wrapup.s(wd))
