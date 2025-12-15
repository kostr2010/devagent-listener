import os.path
import subprocess
import pydantic
import typing

from app.devagent.stages.review_init import DevagentTask
from app.utils.path import is_subpath


class DevagentError(pydantic.BaseModel):
    patch: str
    rule: str
    message: str


class DevagentViolation(pydantic.BaseModel):
    file: str
    line: int
    severity: typing.Optional[str] = None
    rule: str
    rule_url: typing.Optional[str] = None
    message: str
    change_type: typing.Optional[str] = None
    code_snippet: typing.Optional[str] = None


class DevagentReview(pydantic.BaseModel):
    violations: list[DevagentViolation]


class ReviewPatchResult(pydantic.BaseModel):
    project: str
    error: DevagentError | None
    result: DevagentReview | None


def worker_get_range(n_tasks: int, group_idx: int, group_size: int) -> tuple[int, int]:
    assert group_size > 0, "Invalid group size"
    assert 0 <= group_idx, "Invalid group index"
    assert group_idx < group_size, "Invalid group index"

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


def review_patch(
    repo_root: str, patch_path: str, rule_path: str, context: str
) -> ReviewPatchResult:
    project = os.sep.join(os.path.normpath(repo_root).split(os.sep)[-2:])

    cmd = [
        "devagent",
        "--context",
        context,
        "review",
        "--json",
        "--rule",
        rule_path,
        patch_path,
    ]

    print(f"Started devagent:\ncwd={repo_root}\ncmd={' '.join(cmd)}")

    devagent_result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=repo_root,
    )

    rule = os.path.splitext(os.path.basename(rule_path))[0]

    stderr = devagent_result.stderr.decode("utf-8")
    if len(stderr) > 0 and "Error" in stderr:
        return ReviewPatchResult(
            project=project,
            error=DevagentError(
                message=stderr,
                patch=os.path.basename(patch_path),
                rule=rule,
            ),
            result=None,
        )

    stdout = devagent_result.stdout.decode("utf-8")
    if len(stdout) == 0:
        raise Exception(
            f"[review_patch] Received empty stdout for cmd: {cmd}. stderr = {stderr}"
        )

    result = DevagentReview.model_validate_json(stdout)

    print(f"RULE: {rule}\n\nRESULT: {stdout}")

    for violation in result.violations:
        # NOTE: fixup for LLM rule name hallucinations
        violation.rule = rule
        violation.rule_url = f"https://gitcode.com/nazarovkonstantin/arkcompiler_development_rules/tree/main/REVIEW_RULES/{rule}.md"

    return ReviewPatchResult(
        project=project,
        error=None,
        result=result,
    )


def filter_violations(res: ReviewPatchResult, task: DevagentTask) -> ReviewPatchResult:
    if res.result == None:
        return res

    filtered_violations = [
        violation
        for violation in res.result.violations
        if _is_violation_valid(violation, task)
    ]

    if task.rule_once and len(filtered_violations) > 1:
        filtered_violations = [filtered_violations[0]]

    return ReviewPatchResult(
        project=res.project,
        error=res.error,
        result=DevagentReview(violations=filtered_violations),
    )


###########
# private #
###########


def _is_violation_valid(violation: DevagentViolation, task: DevagentTask) -> bool:
    alarm_rule = violation.rule

    if alarm_rule not in task.rule_path:
        return False

    alarm_file = violation.file
    alarm_file_path = os.path.join(task.project, alarm_file)

    for dir in task.rule_skip:
        if is_subpath(dir, alarm_file_path):
            return False

    for dir in task.rule_dirs:
        if is_subpath(dir, alarm_file_path):
            return True

    return False
