import celery  # type: ignore
import inspect
import celery.exceptions  # type: ignore
import traceback
import tempfile
import typing

from app.celery.celery import celery_instance
from app.config import CONFIG

from app.devagent.stages.review_init import (
    populate_workdir,
    get_diffs,
    load_rules,
    prepare_tasks,
    store_task_info_to_redis,
    DevagentTask,
)
from app.devagent.stages.review_patches import (
    devagent_review_patch,
    worker_get_range,
    ReviewPatchResult,
)
from app.devagent.stages.review_wrapup import (
    store_errors_to_postgres,
    clean_workdir,
    process_review_result,
    ProcessedReview,
)

DEVAGENT_REVIEW_GROUP_SIZE = 12

DEVAGENT_WORKER_NAME = "devagent_worker"

devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.REDIS_DEVAGENT_DB)


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_init(self: celery.Task, urls: list[str]) -> typing.Any:
    task_id = self.request.id
    log_tag = f"[{task_id}]"

    wd = None
    try:
        wd = tempfile.mkdtemp()
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))

    diffs = None
    try:
        diffs = get_diffs(urls)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} got diffs of urls {urls}")

    try:
        populate_workdir(wd, diffs)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} populated workdir {wd}")

    rules = None
    try:
        rules = load_rules(wd)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} loaded rules {rules}")

    tasks = None
    try:
        tasks = prepare_tasks(task_id, wd, rules, diffs)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} prepared {len(tasks)} tasks {tasks}")

    try:
        store_task_info_to_redis(task_id=task_id, wd=wd, tasks=tasks)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} stored task info to redis")

    return celery.chord(
        [
            review_patches.s(tasks, i, DEVAGENT_REVIEW_GROUP_SIZE)
            for i in range(DEVAGENT_REVIEW_GROUP_SIZE)
        ],
    )(review_wrapup.s(wd))


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_patches(
    self: celery.Task, tasks: list[DevagentTask], group_idx: int, group_size: int
) -> list[dict[str, typing.Any]]:
    res = _review_patches(self, tasks, group_idx, group_size)
    return [review.model_dump() for review in res]


@devagent_worker.task(bind=True, track_started=True)  # type: ignore
def review_wrapup(
    self: celery.Task,
    review: list[list[dict[str, typing.Any]]],
    wd: str,
) -> dict[str, typing.Any]:
    validated_review = [
        [ReviewPatchResult.model_validate(item) for item in review_list]
        for review_list in review
    ]
    res = _wrapup(self, validated_review, wd)
    return res.model_dump()


###########
# private #
###########


# Since celery can not serialize pydantic models, do verification here
def _review_patches(
    self: celery.Task, tasks: list[DevagentTask], group_idx: int, group_size: int
) -> list[ReviewPatchResult]:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    try:
        start_idx, end_idx = worker_get_range(len(tasks), group_idx, group_size)
        tasks = [tasks[i] for i in range(start_idx, end_idx)]
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} received {len(tasks)} tasks {tasks}")

    results = []

    for task in tasks:
        repo_root, patch_path, rule_path = task
        patch_review_result = None

        try:
            patch_review_result = devagent_review_patch(
                repo_root, patch_path, rule_path
            )
        except Exception:
            raise celery.exceptions.TaskError(_exception_message(log_tag))

        results.append(patch_review_result)

    return results


# Since celery can not serialize pydantic models, do verification here
def _wrapup(
    self: celery.Task,
    review: list[list[ReviewPatchResult]],
    wd: str,
) -> ProcessedReview:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    try:
        rules = load_rules(wd)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} loaded rules {rules}")

    try:
        res = process_review_result(rules, review)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} processed review result {res}")

    try:
        store_errors_to_postgres(self.request.root_id, res)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} stored errors to postgres")

    try:
        clean_workdir(wd)
    except Exception:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} cleaned workdir {wd}")

    return res


def _exception_message(tag: str) -> str:
    caller = inspect.stack()[1].function
    exc_message = traceback.format_exc().split("\n")

    return f"[{tag}] {caller} failed with an exception {exc_message}"
