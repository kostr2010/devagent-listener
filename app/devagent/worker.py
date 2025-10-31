import celery
import tempfile

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

DEVAGENT_REVIEW_GROUP_SIZE = 12

DEVAGENT_WORKER_NAME = "devagent_worker"


devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.REDIS_DEVAGENT_DB)


def create_devagent_review_workflow(urls: list):
    """
    Create workflow for the devagent review. Client has to launch the task on their side

    Args:
        urls: List of urls for PRs for review

    Returns:
        Celery Chain that handles review for these PRs
    """
    wd = tempfile.mkdtemp()

    return celery.chain(
        devagent_prepare_tasks.s(wd, urls),
        celery.group(
            devagent_review_patches.s(i, DEVAGENT_REVIEW_GROUP_SIZE)
            for i in range(DEVAGENT_REVIEW_GROUP_SIZE)
        ),
        devagent_review_wrapup.s(wd),
    )


@devagent_worker.task(bind=True, track_started=True)
def devagent_prepare_tasks(self, wd: str, urls: list):
    log_tag = None
    task_id = None
    try:
        log_tag = _devagent_prepare_tasks_log_tag(self)
        task_id = _devagent_prepare_tasks_task_id(self)
    except Exception as e:
        msg = f"{log_tag} devagent_prepare_tasks init failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    try:
        populate_workdir(wd)
    except Exception as e:
        msg = f"{log_tag} populate_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{log_tag} populated workdir {wd}")

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        msg = f"{log_tag} load_rules(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    diffs = None
    try:
        diffs = get_diffs(urls)
    except Exception as e:
        msg = f"{log_tag} get_diffs(urls={urls}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    tasks = None
    try:
        tasks = prepare_tasks(task_id, wd, rules, diffs)
    except Exception as e:
        msg = f"{log_tag} prepare_tasks(wd={wd},rules={rules},diffs={diffs}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{log_tag} prepared {len(tasks)} tasks {tasks}")

    try:
        store_task_info_to_redis(task_id=task_id, wd=wd, tasks=tasks)
    except Exception as e:
        msg = f"{log_tag} store_task_info_to_redis(task_id={task_id},wd={wd},tasks={tasks}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    return tasks


@devagent_worker.task(bind=True, track_started=True)
def devagent_review_patches(
    self, arg_packs: list, group_idx: int, group_size: int
) -> list:
    log_tag = None
    try:
        log_tag = _devagent_review_patches_log_tag(self)
    except Exception as e:
        msg = f"{log_tag} devagent_review_patches init failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    start_idx = None
    end_idx = None
    try:
        start_idx, end_idx = worker_get_range(len(arg_packs), group_idx, group_size)
    except Exception as e:
        msg = f"{log_tag} worker_get_range(n_tasks={len(arg_packs)},group_idx={group_idx}, group_size={group_size}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(
            f"{log_tag} received tasks {[arg_packs[i] for i in range(start_idx, end_idx)]}"
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
            msg = f"{log_tag} devagent_review_patch(repo_root={repo_root},patch_path={patch_path}, rule_path={rule_path}) failed with exception: {str(e)}"
            _update_state_failed(self, e, msg)
            raise Exception(msg)

        results.append(patch_review_result)

    return results


@devagent_worker.task(bind=True, track_started=True)
def devagent_review_wrapup(
    self,
    devagent_review: list,
    wd: str,
):
    log_tag = None
    task_id = None
    try:
        log_tag = _devagent_review_wrapup_log_tag(self)
        task_id = _devagent_review_wrapup_task_id(self)
    except Exception as e:
        msg = f"{log_tag} devagent_review_wrapup init failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        msg = f"{log_tag} load_rules(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    res = None
    try:
        res = process_review_result(devagent_review)
    except Exception as e:
        msg = f"{log_tag} process_review_result(devagent_review={devagent_review}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{log_tag} processed review result {res}")

    try:
        store_errors_to_postgres(task_id, wd, res)
    except Exception as e:
        msg = f"{log_tag} store_task_info_to_redis(task_id={task_id},wd={wd},devagent_review={devagent_review}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{log_tag} uploaded patches to redis {wd}")

    try:
        clean_workdir(wd)
    except Exception as e:
        msg = f"{log_tag} clean_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"{log_tag} cleaned workdir {wd}")

    return res


###########
# private #
###########


def _devagent_prepare_tasks_task_id(self) -> str:
    # FIXME: very fragile! needs change when chain is updated
    celery_chord = self.request.chain[0]
    task_id = celery_chord["kwargs"]["body"]["options"]["task_id"]
    return task_id


def _devagent_prepare_tasks_log_tag(self) -> str:
    task_id = _devagent_prepare_tasks_task_id(self)
    return f"[{task_id}] -> [{self.request.id}]"


def _devagent_review_patches_log_tag(self) -> str:
    return f"[{self.request.parent_id}] -> [{self.request.id}]"


def _devagent_review_wrapup_task_id(self) -> str:
    # FIXME: very fragile! needs change when chain is updated
    return self.request.id


def _devagent_review_wrapup_log_tag(self) -> str:
    task_id = _devagent_review_wrapup_task_id(self)
    return f"[{task_id}] -> [{self.request.id}]"


def _update_state_failed(self, exc: Exception, msg: str) -> None:
    self.update_state(
        state="FAILURE", meta={"exc_type": type(exc).__name__, "exc_message": msg}
    )
