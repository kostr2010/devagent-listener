import celery
import tempfile

from ..celery import celery_instance
from ..config import CONFIG

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


@devagent_worker.task(bind=True)
def devagent_review_wrapup(self, devagent_review: list, wd: str):
    clean_workdir(wd)

    print(f"[{self.request.id}] cleaned workdir {wd}")

    res = process_review_result(devagent_review)

    print(f"[{self.request.id}] processed review result {res}")

    return res


@devagent_worker.task(bind=True)
def devagent_prepare_tasks(self, wd: str, urls: list):
    populate_workdir(wd)

    print(f"[{self.request.id}] populated workdir {wd}")

    rules = load_rules(wd)

    diffs = get_diffs(urls)

    tasks = prepare_tasks(wd, rules, diffs)

    print(f"[{self.request.id}] prepared tasks {tasks}")

    return tasks


@devagent_worker.task(bind=True)
def devagent_review_patches(
    self, arg_packs: list, group_idx: int, group_size: int
) -> list:
    start_idx, end_idx = worker_get_range(len(arg_packs), group_idx, group_size)

    print(
        f"[{self.request.id}] received tasks {[arg_packs[i] for i in range(start_idx, end_idx)]}"
    )

    results = []

    for i in range(start_idx, end_idx):
        cwd, patch_path, rule_path = arg_packs[i]
        patch_review_result = devagent_review_patch(cwd, patch_path, rule_path)
        results.append(patch_review_result)

    return results
