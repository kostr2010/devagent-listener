import os.path
import json
import subprocess
import jsonschema
import pydantic


class DevagentError(pydantic.BaseModel):
    patch: str
    rule: str
    message: str


class DevagentViolation(pydantic.BaseModel):
    file: str
    line: int
    severity: str
    rule: str
    message: str
    change_type: str
    code_snippet: str


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


def review_patch(repo_root: str, patch_path: str, rule_path: str) -> ReviewPatchResult:
    project = os.sep.join(os.path.normpath(repo_root).split(os.sep)[-2:])

    cmd = ["devagent", "review", "--json", "--rule", rule_path, patch_path]

    print(f"Started devagent:\ncwd={repo_root}\ncmd={' '.join(cmd)}")

    devagent_result = subprocess.run(
        cmd,
        capture_output=True,
        cwd=repo_root,
    )

    stderr = devagent_result.stderr.decode("utf-8")
    if len(stderr) > 0 and "Error" in stderr:
        return ReviewPatchResult(
            project=project,
            error=DevagentError(
                message=stderr,
                patch=os.path.basename(patch_path),
                rule=os.path.basename(rule_path),
            ),
            result=None,
        )

    return ReviewPatchResult(
        project=project,
        error=None,
        result=DevagentReview.model_validate_json(
            devagent_result.stdout.decode("utf-8")
        ),
    )
