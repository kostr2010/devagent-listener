import celery  # type: ignore
import inspect
import multiprocessing
import celery.exceptions  # type: ignore
import traceback
import tempfile
import typing
import os

from app.diff.models.diff import Diff
from app.db.async_db import AsyncDBConnectionConfig
from app.redis.async_redis import AsyncRedisConfig
from app.config import CONFIG

from app.devagent.stages.review_init import (
    extract_project_info,
    populate_workdir,
    load_rules,
    prepare_tasks,
    store_task_info_to_redis,
    ProjectInfo,
    DevagentTask,
)
from app.devagent.stages.review_patches import (
    filter_violations,
    review_patch,
    worker_get_range,
    ReviewPatchResult,
)
from app.devagent.stages.review_wrapup import (
    store_errors_to_postgres,
    clean_workdir,
    process_review_result,
)

UntypedModel = dict[str, typing.Any]


def init_worker() -> celery.Celery:
    usr = CONFIG.REDIS_USERNAME
    pwd = CONFIG.REDIS_PASSWORD
    host = CONFIG.REDIS_HOST
    port = CONFIG.REDIS_PORT
    db = CONFIG.REDIS_DEVAGENT_DB
    redis_url = f"redis://{usr}:{pwd}@{host}:{port}/{db}"

    app = celery.Celery(
        "devagent_worker",
        broker=redis_url,
        backend=redis_url,
    )

    app.conf.task_track_started = True
    app.conf.result_expires = CONFIG.EXPIRY_DEVAGENT_WORKER

    return app


devagent_worker = init_worker()


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_init(
    self: celery.Task,
    diffs: list[UntypedModel],
    db_cfg: UntypedModel,
    redis_cfg: UntypedModel,
    n_groups: int = CONFIG.MAX_WORKERS,
) -> typing.Any:
    task_id = self.request.id
    log_tag = f"[{task_id}]"

    try:
        wd = tempfile.mkdtemp()

        validated_diffs = [Diff.model_validate(diff) for diff in diffs]

        projects_info = [extract_project_info(diff) for diff in validated_diffs]

        rules_info = ProjectInfo(
            remote=CONFIG.DEVAGENT_RULES_REMOTE,
            project=CONFIG.DEVAGENT_RULES_PROJECT,
            revision=CONFIG.DEVAGENT_RULES_REVISION,
        )

        populate_workdir(wd, rules_info, projects_info)

        rules = load_rules(wd)

        tasks = prepare_tasks(task_id, wd, rules, validated_diffs)

        validated_redis_cfg = AsyncRedisConfig.model_validate(redis_cfg)
        store_task_info_to_redis(
            redis_cfg=validated_redis_cfg, task_id=task_id, wd=wd, tasks=tasks
        )

        untyped_tasks = [task.model_dump() for task in tasks]

        review_tasks = [
            review_patches.s(untyped_tasks, i, n_groups) for i in range(n_groups)
        ]
        wrapup_task = review_wrapup.s(wd, db_cfg, redis_cfg)

        chord = celery.chord(review_tasks)(wrapup_task)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))

    return chord


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_patches(
    self: celery.Task,
    tasks: list[UntypedModel],
    group_idx: int,
    group_size: int,
) -> list[UntypedModel]:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    try:
        validated_tasks = [DevagentTask.model_validate(item) for item in tasks]

        start_idx, end_idx = worker_get_range(
            len(validated_tasks), group_idx, group_size
        )

        validated_tasks = [validated_tasks[i] for i in range(start_idx, end_idx)]

        results = list[ReviewPatchResult]()
        for task in validated_tasks:
            project_root = os.path.abspath(os.path.join(task.wd, task.project))
            patch_review_result = review_patch(
                project_root, task.patch_path, task.rule_path, task.context_path
            )
            filtered_result = filter_violations(patch_review_result, task)
            results.append(filtered_result)

        res = [review.model_dump() for review in results]
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))

    return res


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_wrapup(
    self: celery.Task,
    review: list[list[UntypedModel]],
    wd: str,
    db_cfg: UntypedModel,
    redis_cfg: UntypedModel,
) -> UntypedModel:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    try:
        validated_review = [
            [ReviewPatchResult.model_validate(item) for item in review_list]
            for review_list in review
        ]

        processed_review = process_review_result(validated_review)

        validated_db_cfg = AsyncDBConnectionConfig.model_validate(db_cfg)
        validated_redis_cfg = AsyncRedisConfig.model_validate(redis_cfg)
        store_errors_to_postgres(
            validated_db_cfg,
            validated_redis_cfg,
            self.request.root_id,
            processed_review,
        )

        clean_workdir(wd)

        untyped_review = processed_review.model_dump()
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))

    return untyped_review


###########
# private #
###########


def _exception_message(tag: str) -> str:
    caller = inspect.stack()[1].function
    exc_message = traceback.format_exc().split("\n")

    return f"[{tag}] {caller} failed with an exception {exc_message}"
