import shutil
import asyncio
import os.path

from app.api.v1.devagent.tasks.task_info.actions.get import task_info_get
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.postgres.models import Error
from app.postgres.infrastructure import save_patch_if_does_not_exist
from app.postgres.database import SQL_SESSION
from app.utils.validation import validate_result
from app.utils.path import abspath_join


def store_errors_to_postgres(
    task_id: str,
    processed_review: dict,
) -> None:
    errors: dict = processed_review.get("errors", {})

    if len(errors.items()) == 0:
        return

    asyncio.get_event_loop().run_until_complete(
        _store_errors_to_postgres(task_id, errors)
    )


def clean_workdir(wd: str) -> None:
    shutil.rmtree(wd, ignore_errors=True)


@validate_result(
    {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "process_review_result return value shema",
        "description": "Return value schema of process_review_result API",
        "type": "object",
        "properties": {
            "errors": {
                "type": "object",
                "patternProperties": {
                    "^.*$": {
                        "description": "Repo name mapped to the list of errors found for it",
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"},
                                "patch": {"type": "string"},
                                "rule": {"type": "string"},
                            },
                            "required": ["message", "patch", "rule"],
                            "additionalProperties": False,
                        },
                    },
                },
                "additionalProperties": False,
            },
            "results": {
                "type": "object",
                "patternProperties": {
                    "^.*$": {
                        "description": "Repo name mapped to the list of alarms raised for it",
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
                            # FIXME: make True when devagent specifies it's output
                            "additionalProperties": True,
                        },
                    },
                },
                "additionalProperties": False,
            },
        },
        "required": ["errors", "results"],
        "additionalProperties": False,
    }
)
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

    filtered_results = {
        repo: list(
            filter(
                lambda violation: _is_alarm_applicable(rules, repo, violation),
                violations,
            )
        )
        for repo, violations in flattened_results.items()
    }

    return {
        "errors": errors,
        "results": filtered_results,
    }


###########
# private #
###########


def _is_alarm_applicable(rules: dict, repo: str, alarm: dict) -> bool:
    alarm_rule = alarm["rule"]
    alarm_file = alarm["file"]

    for dir, dir_rules in rules.items():
        if repo not in dir:
            continue

        repo_root = abspath_join(dir.split(repo)[0], repo)
        alarm_file_abspath = abspath_join(repo_root, alarm_file)
        if dir != os.path.commonpath([dir, alarm_file_abspath]):
            continue

        for rule in dir_rules:
            if alarm_rule in rule:
                return True

    return False


async def _store_errors_to_postgres(
    task_id: str,
    errors: dict,
) -> None:
    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)
    task_info = await task_info_get(redis=conn, query_params={"task_id": task_id})
    await conn.close()

    rev_arkcompiler_development_rules = task_info["rev_arkcompiler_development_rules"]
    rev_devagent = task_info["rev_devagent"]

    async with SQL_SESSION() as postgres:
        orm_errors: list[Error] = []

        for repo, errors in errors.items():
            rev = task_info[f"rev_{repo}"]
            for error in errors:
                patch = error["patch"]
                rule = error["rule"]
                message = error["message"]
                content = task_info[patch]

                await save_patch_if_does_not_exist(postgres, patch, content)

                orm_error: Error = Error(
                    rev_arkcompiler_development_rules=rev_arkcompiler_development_rules,
                    rev_devagent=rev_devagent,
                    repo=repo,
                    rev=rev,
                    patch=patch,
                    rule=rule,
                    message=message,
                )

                orm_errors.append(orm_error)

        postgres.add_all(orm_errors)
        await postgres.commit()
