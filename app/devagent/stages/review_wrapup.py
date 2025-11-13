import shutil
import asyncio
import os.path
import pydantic

from app.routes.api.v1.devagent.tasks.task_info.actions.get import action_get
from app.config import CONFIG
from app.redis.redis import init_async_redis_conn
from app.postgres.models import Error
from app.postgres.infrastructure import save_patch_if_does_not_exist
from app.postgres.database import SQL_SESSION
from app.utils.path import abspath_join
from app.devagent.stages.review_patches import (
    DevagentError,
    DevagentViolation,
    ReviewPatchResult,
)
from app.redis.models import (
    task_info_patch_content_key,
    task_info_patch_context_key,
    task_info_project_revision_key,
)


class ProcessedReview(pydantic.BaseModel):
    errors: dict[str, list[DevagentError]]
    results: dict[str, list[DevagentViolation]]


def store_errors_to_postgres(
    task_id: str,
    processed_review: ProcessedReview,
) -> None:
    errors = processed_review.errors

    if len(errors.items()) == 0:
        return

    asyncio.get_event_loop().run_until_complete(
        _store_errors_to_postgres(task_id, errors)
    )


def clean_workdir(wd: str) -> None:
    shutil.rmtree(wd, ignore_errors=True)


def process_review_result(
    rules: dict[str, list[str]], devagent_review: list[list[ReviewPatchResult]]
) -> ProcessedReview:
    results = dict[str, list[DevagentViolation]]()
    errors = dict[str, list[DevagentError]]()

    devagent_review_flat = list[ReviewPatchResult]()
    for review_chunk in devagent_review:
        for review in review_chunk:
            devagent_review_flat.append(review)

    for review in devagent_review_flat:
        project = review.project

        assert bool(review.error) != bool(
            review.result
        ), "`error` and `result` are mutually exclusive and can not be both None"

        if review.error != None:
            errors_tmp = errors.get(project, list())
            errors_tmp.append(review.error)
            errors.update({project: errors_tmp})
        elif review.result != None:
            violations: list[DevagentViolation] = review.result.violations
            results_tmp: list[DevagentViolation] = results.get(project, list())
            results_tmp.extend(violations)
            results.update({project: results_tmp})
        else:
            raise Exception(
                f"review {review} does not have neither `error`, nor `result`"
            )

    filtered_results: dict[str, list[DevagentViolation]] = {
        project: list(
            filter(
                lambda violation: _is_alarm_applicable(rules, project, violation),
                violations,
            )
        )
        for project, violations in results.items()
    }

    return ProcessedReview(errors=errors, results=filtered_results)


###########
# private #
###########


def _is_alarm_applicable(
    rules: dict[str, list[str]], project: str, violation: DevagentViolation
) -> bool:
    alarm_rule = violation.rule
    alarm_file = violation.file

    for dir, dir_rules in rules.items():
        if project not in dir:
            continue

        project_root = abspath_join(dir.split(project)[0], project)
        assert os.path.exists(
            project_root
        ), f"Project root {project_root} does not exist"

        alarm_file_abspath = abspath_join(project_root, alarm_file)

        if dir != os.path.commonpath([dir, alarm_file_abspath]):
            continue

        for rule in dir_rules:
            if alarm_rule in rule:
                return True

    return False


async def _store_errors_to_postgres(
    task_id: str,
    errors: dict[str, list[DevagentError]],
) -> None:
    conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)
    task_info = await action_get(redis=conn, query_params={"task_id": task_id})
    await conn.close()

    ark_dev_rules_project = "nazarovkonstantin/arkcompiler_development_rules"
    ark_dev_rules_rev_key = task_info_project_revision_key(ark_dev_rules_project)
    ark_dev_rules_rev = task_info[ark_dev_rules_rev_key]

    devagent_project = "egavrin/devagent"
    devagent_rev_key = task_info_project_revision_key(devagent_project)
    devagent_rev = task_info[devagent_rev_key]

    async with SQL_SESSION() as postgres:
        orm_errors = list[Error]()

        for project, repo_errors in errors.items():
            project_rev_key = task_info_project_revision_key(project)
            project_rev = task_info[project_rev_key]
            for error in repo_errors:
                rule = error.rule
                message = error.message
                patch_name = task_info[rule]
                patch_content_key = task_info_patch_context_key(patch_name)
                patch_content = task_info[patch_content_key]
                patch_context_key = task_info_patch_context_key(patch_name)
                patch_context = task_info[patch_context_key]

                await save_patch_if_does_not_exist(
                    postgres, patch_name, patch_content, patch_context
                )

                orm_error: Error = Error(
                    rev_arkcompiler_development_rules=ark_dev_rules_rev,
                    rev_devagent=devagent_rev,
                    project=project,
                    rev_project=project_rev,
                    patch=patch_name,
                    rule=rule,
                    message=message,
                )

                orm_errors.append(orm_error)

        postgres.add_all(orm_errors)
        await postgres.commit()
