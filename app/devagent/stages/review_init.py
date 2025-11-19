import os.path
import hashlib
import asyncio
import tempfile
import subprocess
import git
import time
import pydantic

from app.routes.api.v1.devagent.tasks.task_info.actions.set import action_set
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.gitcode.get_diff import get_diff, Diff
from app.utils.path import abspath_join
from app.patch.analyzer import PatchAnalyzer
from app.redis.models import (
    task_info_project_revision_key,
    task_info_patch_context_key,
    task_info_patch_content_key,
)


class DevagentTask(pydantic.BaseModel):
    wd: str
    project: str
    patch_path: str
    context_path: str
    rule_path: str
    rule_dirs: list[str]


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
    filtered_rules = _remove_non_existing_dirs(wd, review_rules)
    rule_to_dirs = _invert_loaded_rules(filtered_rules)

    for rule, dirs in rule_to_dirs.items():
        rule_path = _rule_abspath(wd, rule)
        assert os.path.exists(
            rule_path
        ), f"[load_rules] Sanity check failed for rule {rule_path}"
        for dir in dirs:
            dir_path = abspath_join(wd, dir)
            assert os.path.exists(
                dir_path
            ), f"[load_rules] Sanity check failed for dir {dir_path}"

    return rule_to_dirs


def prepare_tasks(
    task_id: str, wd: str, rules: dict[str, list[str]], diffs: list[Diff]
) -> list[DevagentTask]:
    tasks = list[DevagentTask]()

    for diff in diffs:
        mapping = _map_applicable_rules_to_diffs(rules, diff)

        emitted_diffs = dict[str, str]()
        patch_contexts = dict[str, str]()

        for rule, rule_diff in mapping.items():
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
                rule_path=_rule_abspath(wd, rule),
                rule_dirs=rules[rule],
            )

            tasks.append(task)

    return tasks


def store_task_info_to_redis(task_id: str, wd: str, tasks: list[DevagentTask]) -> None:
    task_info = dict()

    task_info.update({"task_id": task_id})

    ark_dev_rules_root = _arkcompiler_development_rules_root(wd)
    ark_dev_rules_rev = _get_revision(ark_dev_rules_root)
    ark_dev_rules_rev_key = task_info_project_revision_key(
        "nazarovkonstantin/arkcompiler_development_rules"
    )
    task_info.update({ark_dev_rules_rev_key: ark_dev_rules_rev})

    devagent_root = "/devagent"
    devagent_rev = _get_revision(devagent_root)
    devagent_rev_key = task_info_project_revision_key("egavrin/devagent")
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

    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)

    asyncio.get_event_loop().run_until_complete(
        action_set(redis=conn, query_params=task_info)
    )

    asyncio.get_event_loop().run_until_complete(conn.close())


###########
# private #
###########


def _generate_patch_context(patch_path: str) -> str:
    pa = PatchAnalyzer(patch_path)
    if pa.analyze():
        patch_summary = pa.verboseTestSummary()
    else:
        patch_summary = ""
    return patch_summary


def _map_applicable_rules_to_diffs(
    rules: dict[str, list[str]], diff: Diff
) -> dict[str, str]:
    mapping = dict[str, str]()

    combined_diff = _combine_diff(diff)
    applicable_rules = _get_relevant_rules(rules, diff)

    mapping.update({rule: combined_diff for rule in applicable_rules})

    return mapping


def _rule_abspath(wd: str, rule: str) -> str:
    rules_project_root = _arkcompiler_development_rules_root(wd)
    rules_dir = abspath_join(rules_project_root, "REVIEW_RULES")
    rule_abspath = abspath_join(rules_dir, rule)

    return rule_abspath


def _get_relevant_rules(rules: dict[str, list[str]], diff: Diff) -> set[str]:
    applicable_rules = set[str]()

    for file in diff.files:
        file_path = os.path.join(diff.project, file.file)
        for rule, rule_dirs in rules.items():
            for rule_dir in rule_dirs:
                if rule_dir == os.path.commonpath([rule_dir, file_path]):
                    applicable_rules.add(rule)
                    break

    return applicable_rules


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


def _remove_non_existing_dirs(
    wd: str, review_rules: dict[str, set[str]]
) -> dict[str, set[str]]:
    filtered_rules = dict()

    for dir, rules in review_rules.items():
        dir_path = abspath_join(wd, dir)
        if not os.path.exists(dir_path):
            continue

        filtered_rules.update({dir: rules})

    return filtered_rules


def _invert_loaded_rules(review_rules: dict[str, set[str]]) -> dict[str, list[str]]:
    inverted_rules = dict[str, list[str]]()

    for dir, rules in review_rules.items():
        for rule in rules:
            dirs = inverted_rules.get(rule, list())
            superdirs = [d for d in dirs if d == os.path.commonpath([d, dir])]
            if len(superdirs) == 0:
                dirs.append(dir)
            inverted_rules.update({rule: dirs})

    return inverted_rules


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
        cfg.write(f'provider = "{CONFIG.DEVAGENT_PROVIDER}"\n')
        cfg.write(f'model = "{CONFIG.DEVAGENT_MODEL}"\n')
        cfg.write(f'api_key = "{CONFIG.DEVAGENT_API_KEY}"\n')
        cfg.write(f"auto_approve_code = false\n")
    return devagent_config_path
