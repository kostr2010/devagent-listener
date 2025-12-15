import os
import os.path
import hashlib
import asyncio
import tempfile
import subprocess
import git
import time
import pydantic
import typing
import json

from app.redis.async_redis import AsyncRedisConfig, AsyncRedis
from app.diff.models.diff import Diff
from app.utils.path import abspath_join, is_subpath
from app.patch.analyzer import PatchAnalyzer
from app.redis.schemas.task_info import (
    task_info_task_id_key,
    task_info_rules_revision_key,
    task_info_devagent_revision_key,
    task_info_project_revision_key,
    task_info_patch_context_key,
    task_info_patch_content_key,
)

_RULES_PROJECT = "review_rules"


class DevagentRule(pydantic.BaseModel):
    name: str
    dirs: list[str]
    skip: list[str] = []
    once: bool = False
    disable: bool = False


class DevagentTask(pydantic.BaseModel):
    wd: str
    project: str
    patch_path: str
    context_path: str
    rule_path: str
    rule_dirs: list[str]
    rule_skip: list[str]
    rule_once: bool


class ProjectInfo(pydantic.BaseModel):
    remote: str
    project: str
    revision: str


def extract_project_info(diff: Diff) -> ProjectInfo:
    return ProjectInfo(
        remote=diff.remote, project=diff.project, revision=diff.summary.base_sha
    )


def populate_workdir(
    wd: str, rules_info: ProjectInfo, projects_info: list[ProjectInfo]
) -> None:
    assert os.path.exists(wd), f"Working widectory {wd} does not exist"

    _init_rules_project(wd, rules_info)

    for project_info in projects_info:
        _init_project(wd, project_info)


def load_rules(wd: str) -> list[DevagentRule]:
    ark_dev_rules_root = _rules_root(wd)
    assert os.path.exists(
        ark_dev_rules_root
    ), f"[load_rules] No project root {ark_dev_rules_root} for development rules was found"

    rules_config_path = abspath_join(ark_dev_rules_root, ".REVIEW_RULES.json")
    assert os.path.exists(
        rules_config_path
    ), f"[load_rules] No config file {rules_config_path} was found in the project root {ark_dev_rules_root}"

    with open(rules_config_path) as cfg:
        rules = [DevagentRule.model_validate(rule) for rule in json.loads(cfg.read())]

    filtered_rules = [rule for rule in rules if rule.disable == False]

    assert len(filtered_rules) == len(
        set([rule.name for rule in filtered_rules])
    ), "[load_rules] Loaded rules have duplicates, please check"

    for rule in filtered_rules:
        rule_path = _rule_abspath(wd, rule.name)
        assert os.path.exists(
            rule_path
        ), f"[load_rules] Rule does not exist: {rule_path}"

    return filtered_rules


def prepare_tasks(
    task_id: str, wd: str, rules: list[DevagentRule], diffs: list[Diff]
) -> list[DevagentTask]:
    tasks = list[DevagentTask]()

    for diff in diffs:
        mapping = _map_applicable_rules_to_diffs(rules, diff)

        if len(mapping) == 0:
            continue

        emitted_diffs = dict[str, str]()
        patch_contexts = dict[str, str]()

        for rule, rule_diff in mapping:
            diff_hash = _diff_hash(rule_diff)
            existing_patch = emitted_diffs.get(diff_hash, None)
            if existing_patch:
                patch_path = existing_patch
            else:
                patch_path = _emit_content(wd, ".content.d", task_id, rule_diff)
                emitted_diffs.update({diff_hash: patch_path})

            patch_context = patch_contexts.get(patch_path, None)
            if patch_context:
                context_path = patch_context
            else:
                patch_context = _generate_patch_context(patch_path)
                context_path = _emit_content(wd, ".context.d", task_id, patch_context)
                patch_contexts.update({patch_path: context_path})

            task = DevagentTask(
                wd=wd,
                project=diff.project,
                patch_path=patch_path,
                context_path=context_path,
                rule_path=_rule_abspath(wd, rule.name),
                rule_dirs=rule.dirs,
                rule_skip=rule.skip,
                rule_once=rule.once,
            )

            tasks.append(task)

    return tasks


def store_task_info_to_redis(
    redis_cfg: AsyncRedisConfig, task_id: str, wd: str, tasks: list[DevagentTask]
) -> None:
    task_info = _create_task_info(task_id, wd, tasks)
    redis = AsyncRedis(redis_cfg)
    asyncio.get_event_loop().run_until_complete(redis.set_task_info(task_info))
    asyncio.get_event_loop().run_until_complete(redis.close())


###########
# private #
###########


def _create_task_info(
    task_id: str, wd: str, tasks: list[DevagentTask]
) -> dict[str, typing.Any]:
    task_info = dict()

    task_info.update({task_info_task_id_key(): task_id})

    ark_dev_rules_root = _rules_root(wd)
    ark_dev_rules_rev = _get_revision(ark_dev_rules_root)
    ark_dev_rules_rev_key = task_info_rules_revision_key()
    task_info.update({ark_dev_rules_rev_key: ark_dev_rules_rev})

    devagent_root = "/devagent"
    devagent_rev = _get_revision(devagent_root)
    devagent_rev_key = task_info_devagent_revision_key()
    task_info.update({devagent_rev_key: devagent_rev})

    for task in tasks:
        project_root = abspath_join(task.wd, task.project)
        project_rev_key = task_info_project_revision_key(task.project)
        if not (project_rev_key in task_info):
            task_info.update({project_rev_key: _get_revision(project_root)})

        # patch_name is a basename of the patch
        patch_name = os.path.basename(task.patch_path)
        patch_content_key = task_info_patch_content_key(patch_name)
        if not (patch_content_key in task_info):
            p = open(task.patch_path)
            task_info.update({patch_content_key: p.read()})
            p.close()

        patch_context_key = task_info_patch_context_key(patch_name)
        if not (patch_context_key in task_info):
            c = open(task.context_path)
            task_info.update({patch_context_key: c.read()})
            c.close()

        # rule name is the file name of the rule without file extension
        rule_name = os.path.splitext(os.path.basename(task.rule_path))[0]
        task_info.update({rule_name: patch_name})

    return task_info


def _generate_patch_context(patch_path: str) -> str:
    pa = PatchAnalyzer(patch_path)
    patch_summary = ""
    if pa.analyze():
        patch_summary += pa.verboseRuntimeSummary()
        patch_summary += pa.verboseFrontEndSummary()
        patch_summary += pa.verboseTestSummary()
    return patch_summary


def _map_applicable_rules_to_diffs(
    rules: list[DevagentRule], diff: Diff
) -> list[tuple[DevagentRule, str]]:
    changed_files = [os.path.join(diff.project, file.file) for file in diff.files]

    relevant_rules = [
        rule
        for rule in rules
        if any(_is_rule_applicable(rule, file) for file in changed_files)
    ]

    combined_diff = "\n\n".join([file.diff for file in diff.files])

    return [(rule, combined_diff) for rule in relevant_rules]


def _is_rule_applicable(rule: DevagentRule, file: str) -> bool:
    for dir in rule.skip:
        if is_subpath(dir, file):
            print(f"skipping {file} for rule {rule}")
            return False

    for dir in rule.dirs:
        if is_subpath(dir, file):
            return True

    return False


def _rule_abspath(wd: str, rule: str) -> str:
    rules_project_root = _rules_root(wd)
    rules_dir = abspath_join(rules_project_root, "REVIEW_RULES")
    rule_abspath = abspath_join(rules_dir, rule)

    return rule_abspath


def _rules_root(wd: str) -> str:
    return abspath_join(wd, _RULES_PROJECT)


def _init_rules_project(wd: str, info: ProjectInfo) -> None:
    root = abspath_join(wd, _RULES_PROJECT)
    os.makedirs(root, exist_ok=False)
    _init_project_at_root(root, info.remote, info.project, info.revision)


def _init_project(wd: str, info: ProjectInfo) -> None:
    root = abspath_join(wd, info.project)
    os.makedirs(root, exist_ok=True)
    _init_project_at_root(root, info.remote, info.project, info.revision)


def _init_project_at_root(root: str, remote: str, project: str, rev: str) -> None:
    assert os.path.exists(root), f"Root {root} for cloning does not exist"
    repo = git.Repo.init(path=root, mkdir=False)
    remote_name = "origin"
    repo.create_remote(remote_name, f"https://{remote}/{project}.git")
    tries_left = 5
    while tries_left > 0:
        try:
            repo.git.fetch("origin", rev, "--depth=1")
            # os.system(f"(cd {root} && git fetch {remote_name} {rev} --depth=1)")
            break
        except Exception as e:
            if tries_left > 0:
                tries_left -= 1
                print(
                    f"[tries left: {tries_left}] git fetch failed with the exception {e}"
                )
                time.sleep(5 * (5 - tries_left))
            else:
                raise e
    repo.git.checkout(rev)


def _diff_hash(diff: str) -> str:
    return hashlib.sha256(diff.encode()).hexdigest()


def _emit_content(wd: str, subdir: str, task_id: str, content: str) -> str:
    dir = abspath_join(wd, subdir)
    os.makedirs(dir, exist_ok=True)
    assert os.path.exists(dir), f"Created dir {dir} does not exist"

    temp = tempfile.NamedTemporaryFile(prefix=f"{task_id}_", dir=dir, delete=False)
    temp.write(content.encode("utf-8"))
    path = temp.name
    temp.close()

    assert os.path.exists(path), f"Emitted file {path} does not exist"

    return path


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
