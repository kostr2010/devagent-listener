import celery
import inspect
import celery.exceptions
import traceback
import tempfile

from app.celery.celery import celery_instance
from app.config import CONFIG

from .infrastructure.launch_review import (
    populate_workdir,
    get_diffs,
    load_rules,
    prepare_tasks,
    store_task_info_to_redis,
)
from .infrastructure.review_patches import devagent_review_patch, worker_get_range
from .infrastructure.wrapup import (
    store_errors_to_postgres,
    clean_workdir,
    process_review_result,
)

DEVAGENT_REVIEW_GROUP_SIZE = 12

DEVAGENT_WORKER_NAME = "devagent_worker"


devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.REDIS_DEVAGENT_DB)


@devagent_worker.task(bind=True, track_started=True)
def launch_review(self, urls: list) -> list[tuple[str, str, str]]:
    task_id = self.request.id
    log_tag = f"[{task_id}]"

    wd = None
    try:
        wd = tempfile.mkdtemp()
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))

    diffs = None
    try:
        diffs = get_diffs(urls)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} got diffs of urls {urls}")

    try:
        populate_workdir(wd, diffs)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} populated workdir {wd}")

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} loaded rules {rules}")

    tasks = None
    try:
        tasks = prepare_tasks(task_id, wd, rules, diffs)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} prepared {len(tasks)} tasks {tasks}")

    try:
        store_task_info_to_redis(task_id=task_id, wd=wd, tasks=tasks)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} stored task info to redis")

    return celery.chord(
        [
            review_patches.s(tasks, i, DEVAGENT_REVIEW_GROUP_SIZE)
            for i in range(DEVAGENT_REVIEW_GROUP_SIZE)
        ],
    )(wrapup.s(wd))


@devagent_worker.task(bind=True, track_started=True)
def review_patches(
    self, arg_packs: list, group_idx: int, group_size: int
) -> list[dict]:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    tasks = None
    try:
        start_idx, end_idx = worker_get_range(len(arg_packs), group_idx, group_size)
        tasks = [arg_packs[i] for i in range(start_idx, end_idx)]
    except Exception as e:
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
        except Exception as e:
            raise celery.exceptions.TaskError(_exception_message(log_tag))

        results.append(patch_review_result)

    return results


@devagent_worker.task(bind=True, track_started=True)
def wrapup(
    self,
    devagent_review: list,
    wd: str,
) -> dict:
    log_tag = f"[{self.request.root_id}] -> [{self.request.id}]"

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} loaded rules {rules}")

    res = None
    try:
        res = process_review_result(rules, devagent_review)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} processed review result {res}")

    try:
        store_errors_to_postgres(self.request.root_id, res)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} stored errors to postgres")

    try:
        clean_workdir(wd)
    except Exception as e:
        raise celery.exceptions.TaskError(_exception_message(log_tag))
    else:
        print(f"{log_tag} cleaned workdir {wd}")

    return res


###########
# private #
###########


def _exception_message(tag: str) -> str:
    caller = inspect.stack()[1].function
    exc_message = traceback.format_exc().split("\n")

    return f"[{tag}] {caller} failed with an exception {exc_message}"
