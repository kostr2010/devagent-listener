import functools
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import fastapi
import subprocess
import os.path
import os
import urllib.parse
import traceback

from .models import Task, TaskStatus
from .gitcode_pr import get_gitcode_pr
from .repo_info import REPO_INFO, RepoInfo
from .config import app_settings

import tempfile


def run_devagent_review(patch: str, rule: str):
    try:
        devagent_result = subprocess.run(
            ["devagent", "review", "--json", "--rule", rule, patch],
            capture_output=True,
            cwd=app_settings.DEVAGENT_WORKDIR,
        )
        print(f"rule: {rule}")
        print(f"patch: {patch}")
        print(f"stderr: {devagent_result.stderr}")
        print(f"stdout: {devagent_result.stdout}")
        return {"result": devagent_result.stdout}
    except Exception as e:
        return {"error": f"{str(e)}"}


def load_rules_config(repo_info: RepoInfo):
    dir_to_rules = {}
    with open(repo_info.rules_config) as cfg:
        for line in cfg:
            parsed_line = line.strip().split()
            project_prefix = os.path.abspath(
                os.path.join(repo_info.root, parsed_line[0].removeprefix("/"))
            )
            rules = list(
                map(
                    lambda s: os.path.abspath(os.path.join(repo_info.rules_dir, s)),
                    parsed_line[1:],
                )
            )
            dir_to_rules.update({project_prefix: rules})

    return dir_to_rules


def get_gitcode_diff(url: str):
    parsed_url = urllib.parse.urlparse(url)
    # ['', 'owner', 'repo', 'pull', 'pull_number']
    url_path = parsed_url.path.split("/")
    owner = url_path[1]
    repo = url_path[2]
    pr_number = url_path[4]
    gitcode_pr = get_gitcode_pr(owner, repo, pr_number)

    if "error" in gitcode_pr:
        return None
    else:
        return gitcode_pr


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


async def set_task_failed_in_db(
    result: str,
    task_id: int,
    db: sqlalchemy.ext.asyncio.AsyncSession,
):
    await update_task_in_db(
        status=TaskStatus.TASK_STATUS_ERROR, result=result, task_id=task_id, db=db
    )


def url_to_repo_info(url: str):
    parsed_url = urllib.parse.urlparse(url)
    # ['', 'owner', 'repo', 'pull', 'pull_number']
    url_path = parsed_url.path.split("/")
    repo = url_path[2]

    if not repo:
        return None

    for repo_info in REPO_INFO:
        if repo_info.repo == repo:
            return repo_info

    return None


async def devagent_task_code_review_action_run(
    task_id: int, url: str, db: sqlalchemy.ext.asyncio.AsyncSession, pool
):
    try:
        gitcode_diff = get_gitcode_diff(url)
        if not gitcode_diff:
            await set_task_failed_in_db(
                f"Error during getting gitcode pr: {gitcode_diff['error']}",
                task_id,
                db,
            )
            return

        repo_info = url_to_repo_info(url)
        if not repo_info:
            await set_task_failed_in_db(
                f"Error during getting repo info for url {url}",
                task_id,
                db,
            )
            return

        # Later need to cache this
        dir_to_rules = load_rules_config(repo_info)

        review_result_tasks = []
        for gitcode_pr_file in gitcode_diff["files"]:
            relevant_rules = []
            for dir, rules in dir_to_rules.items():
                file_abspath = os.path.abspath(
                    os.path.join(repo_info.root, gitcode_pr_file["file"])
                )
                if dir != os.path.commonpath([dir, file_abspath]):
                    continue
                relevant_rules += rules

            if len(relevant_rules) == 0:
                continue

            diff = gitcode_pr_file["diff"]

            # Generate temp patch file while devagent can't parse input as string
            temp = tempfile.NamedTemporaryFile(suffix=f".patch", delete=False)
            temp.write(diff.encode("utf-8"))
            patch = temp.name
            temp.close()

            run_devagent = functools.partial(run_devagent_review, patch)
            review_result_tasks.append(pool.map_async(run_devagent, relevant_rules))

        review_result_flat = [
            flattened_elem
            for elem in [r.get() for r in review_result_tasks]
            for flattened_elem in elem
        ]

        # update task after LLM finished work
        await update_task_in_db(
            TaskStatus.TASK_STATUS_DONE, str(review_result_flat), task_id, db
        )
    except Exception as e:
        await set_task_failed_in_db(
            f"Unexpected error during processing of the task {str(e)}",
            task_id,
            db,
        )
        print(traceback.format_exc())
