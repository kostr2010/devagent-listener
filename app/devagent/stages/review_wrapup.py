import shutil
import asyncio
import pydantic

from app.db.schemas.error import Error
from app.redis.async_redis import AsyncRedisConfig
from app.redis.async_redis import AsyncRedisConfig, AsyncRedis
from app.db.async_db import AsyncDBConnectionConfig, AsyncDBConnection
from app.devagent.stages.review_patches import (
    DevagentError,
    DevagentViolation,
    ReviewPatchResult,
)
from app.redis.schemas.task_info import (
    task_info_rules_revision_key,
    task_info_devagent_revision_key,
    task_info_patch_content_key,
    task_info_patch_context_key,
    task_info_project_revision_key,
)


class ProcessedReview(pydantic.BaseModel):
    errors: dict[str, list[DevagentError]]
    results: dict[str, list[DevagentViolation]]


def store_errors_to_postgres(
    db_cfg: AsyncDBConnectionConfig,
    redis_cfg: AsyncRedisConfig,
    task_id: str,
    processed_review: ProcessedReview,
) -> None:
    errors = processed_review.errors

    if len(errors.items()) == 0:
        return

    asyncio.get_event_loop().run_until_complete(
        _store_errors_to_postgres(db_cfg, redis_cfg, task_id, errors)
    )


def clean_workdir(wd: str) -> None:
    shutil.rmtree(wd, ignore_errors=True)


def process_review_result(
    devagent_review: list[list[ReviewPatchResult]],
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

    return ProcessedReview(errors=errors, results=results)


###########
# private #
###########


async def _store_errors_to_postgres(
    db_cfg: AsyncDBConnectionConfig,
    redis_cfg: AsyncRedisConfig,
    task_id: str,
    errors: dict[str, list[DevagentError]],
) -> None:
    redis = AsyncRedis(redis_cfg)
    task_info = await redis.get_task_info(task_id)
    await redis.close()

    if task_info == None:
        raise Exception(f"Task info for task {task_id} expired or never existed")

    ark_dev_rules_rev_key = task_info_rules_revision_key()
    ark_dev_rules_rev = task_info[ark_dev_rules_rev_key]

    devagent_rev_key = task_info_devagent_revision_key()
    devagent_rev = task_info[devagent_rev_key]

    db_conn = AsyncDBConnection(db_cfg)

    async for db_session in db_conn.get_session():
        orm_errors = list[Error]()

        for project, repo_errors in errors.items():
            project_rev_key = task_info_project_revision_key(project)
            project_rev = task_info[project_rev_key]
            for error in repo_errors:
                rule = error.rule
                message = error.message
                patch_name = task_info[rule]
                patch_content_key = task_info_patch_content_key(patch_name)
                patch_content = task_info[patch_content_key]
                patch_context_key = task_info_patch_context_key(patch_name)
                patch_context = task_info[patch_context_key]

                await db_session.insert_patch_if_does_not_exist(
                    patch_name, patch_content, patch_context
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
        await db_session.insert_errors(orm_errors)
    await db_conn.close()
