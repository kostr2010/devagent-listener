import celery
import tempfile

from app.celery.celery import celery_instance
from app.config import CONFIG

from .infrastructure import populate_workdir, get_diffs, load_rules, prepare_tasks
from .infrastructure import clean_workdir, process_review_result
from .infrastructure import devagent_review_patch, worker_get_range

DEVAGENT_WORKER_NAME = "devagent_worker"

DEVAGENT_REVIEW_GROUP_SIZE = 8

devagent_worker = celery_instance(DEVAGENT_WORKER_NAME, CONFIG.DEVAGENT_REDIS_DB)


def devagent_review_workflow(urls: list):
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
def devagent_review_wrapup(self, devagent_review: list, wd: str):
    try:
        clean_workdir(wd)
    except Exception as e:
        msg = f"[{self.request.id}] clean_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"[{self.request.id}] cleaned workdir {wd}")

    res = None
    try:
        res = process_review_result(devagent_review)
    except Exception as e:
        msg = f"[{self.request.id}] process_review_result(devagent_review={devagent_review}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"[{self.request.id}] processed review result {res}")

    return res


@devagent_worker.task(bind=True, track_started=True)
def devagent_prepare_tasks(self, wd: str, urls: list):
    try:
        populate_workdir(wd)
    except Exception as e:
        msg = f"[{self.request.id}] populate_workdir(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"[{self.request.id}] populated workdir {wd}")

    rules = None
    try:
        rules = load_rules(wd)
    except Exception as e:
        msg = f"[{self.request.id}] load_rules(wd={wd}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    diffs = None
    try:
        diffs = get_diffs(urls)
    except Exception as e:
        msg = f"[{self.request.id}] get_diffs(urls={urls}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)

    tasks = None
    try:
        tasks = prepare_tasks(wd, rules, diffs)
    except Exception as e:
        msg = f"[{self.request.id}] prepare_tasks(wd={wd},rules={rules},diffs={diffs}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(f"[{self.request.id}] prepared tasks {tasks}")

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
        msg = f"[{self.request.id}] worker_get_range(n_tasks={n_tasks},group_idx={group_idx}, group_size={group_size}) failed with exception: {str(e)}"
        _update_state_failed(self, e, msg)
        raise Exception(msg)
    else:
        print(
            f"[{self.request.id}] received tasks {[arg_packs[i] for i in range(start_idx, end_idx)]}"
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
            msg = f"[{self.request.id}] devagent_review_patch(repo_root={repo_root},patch_path={patch_path}, rule_path={rule_path}) failed with exception: {str(e)}"
            _update_state_failed(self, e, msg)
            raise Exception(msg)

        results.append(patch_review_result)

    return results


def _update_state_failed(self, exc: Exception, msg: str) -> None:
    self.update_state(
        state="FAILURE", meta={"exc_type": type(exc).__name__, "exc_message": msg}
    )
