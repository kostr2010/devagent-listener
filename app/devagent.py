import sqlalchemy.ext.asyncio
import sqlalchemy.future
import fastapi
import subprocess
import os.path
import os
import traceback
import json
import git
import tempfile
import asyncio
import logging

from .models import Task, TaskStatus
from .utils.timer import Timer, TimerResolution
from .remote.get_diff import get_diff

SUPPORTED_REPOS = ["arkcompiler_runtime_core", "arkcompiler_ets_frontend"]
REVIEW_RULES_CONFIG = "REVIEW_RULES"
REVIEW_RULES_DIR = ".REVIEW_RULES"


def run_devagent_review(workdir: str, patch: str, rule: str):
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    try:
        cmd = ["devagent", "review", "--json", "--rule", rule, patch]

        log.info(f"Started devagent:\ncwd={workdir}\ncmd={' '.join(cmd)}")

        devagent_result = None
        with Timer(res=TimerResolution.SECONDS, tag=__name__):
            devagent_result = subprocess.run(
                cmd,
                capture_output=True,
                cwd=workdir,
            )

        stderr = devagent_result.stderr.decode("utf-8")
        if len(stderr) > 0 and "Error" in stderr:
            return {"error": {"message": stderr, "patch": patch, "rule": rule}}

        stdout = devagent_result.stdout.decode("utf-8")

        return {"result": stdout}
    except Exception as e:
        return {"error": f"{str(e)}"}


def load_rules(workdir: str):
    dir_to_rules = {}

    for repo in SUPPORTED_REPOS:
        repo_root = os.path.abspath(os.path.join(workdir, repo))
        rules_config = os.path.abspath(os.path.join(repo_root, REVIEW_RULES_CONFIG))
        rules_dir = os.path.abspath(os.path.join(repo_root, REVIEW_RULES_DIR))

        with open(rules_config) as cfg:
            for line in cfg:
                parsed_line = line.strip().split()
                path = parsed_line[0].removeprefix("/")
                rules = parsed_line[1:]
                abs_path = os.path.abspath(os.path.join(repo_root, path))
                abs_rules = list(
                    map(
                        lambda rule: os.path.abspath(os.path.join(rules_dir, rule)),
                        rules,
                    )
                )
                dir_to_rules.update({abs_path: abs_rules})

    return dir_to_rules


async def update_task_in_db(
    status: TaskStatus,
    result: str,
    task_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    existing_task_result = await db.execute(
        sqlalchemy.future.select(Task).where(Task.task_id == task_id)
    )

    db_item = existing_task_result.scalars().first()

    if db_item == None:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"No task {task_id} found in the db after code_review has finished",
        )

    db_item.task_status = status.value
    db_item.task_result = result
    db_item.updated_at = sqlalchemy.text("now()")

    await db.commit()
    await db.refresh(db_item)


async def devagent_initialize_workdir(workdir: str):
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    remote = "gitcode"
    # FIXME: replace with openharmony when integrating
    owner = "nazarovkonstantin"
    # FIXME: replace with necessary branch
    branch = "feature/review_rules_test"

    with Timer(res=TimerResolution.SECONDS, tag=__name__):
        for repo in SUPPORTED_REPOS:
            clone_dst = os.path.abspath(os.path.join(workdir, repo))
            url = f"https://{remote}.com/{owner}/{repo}.git"

            should_retry = True
            tries_left = 5

            while should_retry:
                try:
                    await asyncio.to_thread(
                        git.Repo.clone_from,
                        url,
                        clone_dst,
                        allow_unsafe_protocols=True,
                        branch=branch,
                        depth=1,
                    )
                except Exception as e:
                    if tries_left > 0:
                        tries_left -= 1
                        log.info(
                            f"[tries left: {tries_left}] Repo clone failed with the exception {e}"
                        )
                        await asyncio.sleep(5 * (5 - tries_left))
                    else:
                        raise e
                else:
                    should_retry = False


def devagent_review_postprocess(devagent_review: list):
    results = []
    errors = []
    for elem in devagent_review:
        if "error" in elem:
            errors.append(elem["error"])
        elif "result" in elem:
            results.append(json.loads(elem["result"]))
        else:
            continue

    results_filtered = [
        violation
        for violations in list(
            map(
                lambda elem: elem["violations"],
                filter(lambda res: len(res["violations"]) > 0, results),
            )
        )
        for violation in violations
    ]

    final_result = {"errors": errors, "results": results_filtered}

    return final_result


async def devagent_review_diff(diff: dict, dir_to_rules: dict, repo_root: str) -> list:
    log = logging.getLogger(__name__)
    log.setLevel(logging.INFO)

    res = []

    with Timer(res=TimerResolution.SECONDS, tag=__name__):
        rule_to_diffs = {}

        for diff_file in diff["files"]:
            relevant_rules = set()
            abspath = os.path.abspath(os.path.join(repo_root, diff_file["file"]))
            for dir, rules in dir_to_rules.items():
                if dir != os.path.commonpath([dir, abspath]):
                    continue
                relevant_rules.update(rules)

            if len(relevant_rules) == 0:
                continue

            for rule in relevant_rules:
                if rule in rule_to_diffs:
                    rule_to_diffs[rule].append(diff_file)
                else:
                    rule_to_diffs[rule] = [diff_file]

        devagent_review_tasks = []

        for rule, diffs in rule_to_diffs.items():
            combined_diff = "\n\n".join([diff["diff"] for diff in diffs])

            # FIXME: remove this. generate temp patch file while devagent can't parse input as string
            temp = tempfile.NamedTemporaryFile(suffix=f".patch", delete=False)
            temp.write(combined_diff.encode("utf-8"))
            patch = temp.name
            temp.close()

            devagent_review_tasks.append(
                asyncio.to_thread(run_devagent_review, repo_root, patch, rule)
            )

        devagent_reviews = await asyncio.gather(*devagent_review_tasks)

        res = devagent_review_postprocess(devagent_reviews)

    return res


async def devagent_task_code_review_action_run(
    task_id: int, url: str, db: sqlalchemy.ext.asyncio.AsyncSession
):
    try:
        with tempfile.TemporaryDirectory() as workdir:
            await devagent_initialize_workdir(workdir)

            rules = load_rules(workdir)

            # TODO: for pr in payload do
            diff = await get_diff(url)
            if "error" in diff:
                raise Exception(f"Error during getting pr diff: {diff['error']}")

            # TODO: for pr in payload do
            repo_root = os.path.abspath(os.path.join(workdir, diff["repo"]))

            # TODO: for pr in payload do
            devagent_review = await devagent_review_diff(diff, rules, repo_root)

            # TODO: for pr in payload do
            await update_task_in_db(
                TaskStatus.TASK_STATUS_DONE,
                json.dumps(devagent_review),
                task_id,
                db,
            )

    except Exception as e:
        await update_task_in_db(
            TaskStatus.TASK_STATUS_ERROR,
            f"Unexpected error during processing of the task {str(e)}. Trace:\n{traceback.format_exc()}",
            task_id,
            db,
        )
