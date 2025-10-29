import os.path
import json
import subprocess

from app.utils.validation import validate_result


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


@validate_result(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "devagent_review_patch return value shema",
        "description": "Return value schema of devagent_review_patch API",
        "type": "object",
        "properties": {
            "repo": {"type": "string"},
            "error": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "patch": {"type": "string"},
                    "rule": {"type": "string"},
                },
                "required": ["message", "patch", "rule"],
                "additionalProperties": False,
            },
            "result": {
                "type": "object",
                "properties": {
                    "violations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file": {"type": "string"},
                                "line": {"type": "number"},
                                "severity": {"type": "string"},
                                "rule": {"type": "string"},
                                "message": {"type": "string"},
                                "code_snippet": {"type": "string"},
                            },
                            "required": [
                                "file",
                                "line",
                                "rule",
                                "message",
                            ],
                            # FIXME: remove after devagent fixes it's schema
                            "additionalProperties": True,
                        },
                    },
                },
                "required": [
                    "violations",
                ],
                "additionalProperties": True,
            },
        },
        "required": ["repo"],
        "additionalProperties": False,
    }
)
def devagent_review_patch(repo_root: str, patch_path: str, rule_path: str) -> dict:
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
