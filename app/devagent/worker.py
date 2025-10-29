import celery
import tempfile
import redis.asyncio
import sqlalchemy.ext.asyncio

from app.celery.celery import celery_instance
from app.config import CONFIG

from .infrastructure import (
    populate_workdir,
    get_diffs,
    load_rules,
    prepare_tasks,
    store_task_info_to_redis,
)
from .infrastructure import devagent_review_patch, worker_get_range
from .infrastructure import (
    store_errors_to_postgres,
    clean_workdir,
    process_review_result,
)

DEVAGENT_WORKER_NAME = "devagent_worker"

DEVAGENT_REVIEW_GROUP_SIZE = 12

devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.REDIS_DEVAGENT_DB)


def create_devagent_review_workflow(
    urls: list,
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
):
    """
    Create workflow for the devagent review. Client has to launch the task on their side

    Args:
        urls: List of urls for PRs for review

    Returns:
        Celery Chain that handles review for these PRs
    """
    wd = tempfile.mkdtemp()

    return test

    return celery.chain(
        devagent_prepare_tasks.s(wd, urls),
        celery.group(
            devagent_review_patches.s(i, DEVAGENT_REVIEW_GROUP_SIZE)
            for i in range(DEVAGENT_REVIEW_GROUP_SIZE)
        ),
        devagent_review_wrapup.s(wd, postgres, redis),
    )


import asyncio
from app.redis.redis import init_async_redis_conn


@devagent_worker.task(bind=True, track_started=True)
def test(self):
    try:
        conn = init_async_redis_conn(CONFIG.REDIS_LISTENER_DB)

        asyncio.get_event_loop().run_until_complete(conn.setex("hui", 60, "zhopa"))

        val = asyncio.get_event_loop().run_until_complete(conn.get("hui"))

        conn.close()
    except Exception as e:
        msg = f"{_task_log_tag(self)} test() failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} test ")

    return val


@devagent_worker.task(bind=True, track_started=True)
def devagent_prepare_tasks(self, wd: str, urls: list):
    print(f"{_task_log_tag(self)} preparing tasks for urls {urls}")

    try:
        populate_workdir(wd)
    except Exception as e:
        msg = f"{_task_log_tag(self)} populate_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} populated workdir {wd}")

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        msg = (
            f"{_task_log_tag(self)} load_rules(wd={wd}) failed with exception: {str(e)}"
        )
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    diffs = None
    try:
        diffs = get_diffs(urls)
    except Exception as e:
        msg = f"{_task_log_tag(self)} get_diffs(urls={urls}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    tasks = None
    try:
        tasks = prepare_tasks(wd, rules, diffs)
    except Exception as e:
        msg = f"{_task_log_tag(self)} prepare_tasks(wd={wd},rules={rules},diffs={diffs}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} prepared tasks {tasks}")

    return tasks


@devagent_worker.task(bind=True, track_started=True)
def devagent_review_patches(
    self, arg_packs: list, group_idx: int, group_size: int
) -> list:
    start_idx = None
    end_idx = None
    n_tasks = len(arg_packs)

    try:
        start_idx, end_idx = worker_get_range(n_tasks, group_idx, group_size)
    except Exception as e:
        msg = f"{_task_log_tag(self)} worker_get_range(n_tasks={n_tasks},group_idx={group_idx}, group_size={group_size}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(
            f"{_task_log_tag(self)} received tasks {[arg_packs[i] for i in range(start_idx, end_idx)]}"
        )

    results = []

    for i in range(start_idx, end_idx):
        repo_root, patch_path, rule_path = arg_packs[i]
        patch_review_result = None

        try:
            patch_review_result = devagent_review_patch(
                repo_root, patch_path, rule_path
            )
        except Exception as e:
            msg = f"{_task_log_tag(self)} devagent_review_patch(repo_root={repo_root},patch_path={patch_path}, rule_path={rule_path}) failed with exception: {str(e)}"
            _update_state_failed(self, e, msg)
            raise Exception(msg)

        results.append(patch_review_result)

    return results


@devagent_worker.task(bind=True, track_started=True)
def devagent_review_wrapup(
    self,
    devagent_review: list,
    wd: str,
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    redis: redis.asyncio.Redis,
):
    try:
        store_task_info_to_redis(wd, redis)
    except Exception as e:
        msg = f"{_task_log_tag(self)} store_task_info_to_redis(wd={wd}, redis=) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} uploaded patches to redis {wd}")

    try:
        store_errors_to_postgres(wd, devagent_review, postgres)
    except Exception as e:
        msg = f"{_task_log_tag(self)} store_task_info_to_redis(devagent_review={devagent_review}, postgres=) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} uploaded patches to redis {wd}")
    try:
        clean_workdir(wd)
    except Exception as e:
        msg = f"{_task_log_tag(self)} clean_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} cleaned workdir {wd}")

    res = None
    try:
        res = process_review_result(devagent_review)
    except Exception as e:
        msg = f"{_task_log_tag(self)} process_review_result(devagent_review={devagent_review}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{_task_log_tag(self)} processed review result {res}")

    return res


###########
# private #
###########


def _update_state_failed(self, exc: Exception, msg: str) -> None:
    self.update_state(
        state="FAILURE", meta={"exc_type": type(exc).__name__, "exc_message": msg}
    )


def _task_log_tag(self) -> str:
    return f"[{self.request.root_id}] -> [{self.request.id}]"
