import functools
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import fastapi
import multiprocessing
import subprocess
import os.path
import os
import urllib.parse
import traceback

from .models import Task, TaskStatus
from .gitcode_pr import get_gitcode_pr

import tempfile


RUNTIME_CORE_ROOT = "/home/kostr2010/openharmony/standalone/arkcompiler/runtime_core/"
ETS_FRONTEND_ROOT = "/home/kostr2010/openharmony/standalone/arkcompiler/ets_frontend/"


def run_devagent_review(diff: str, rule: str):
    try:
        temp = tempfile.NamedTemporaryFile(suffix=".patch", delete=False)
        temp.write(diff.encode("utf-8"))
        temp_name = temp.name
        temp.close()
        devagent_result = subprocess.run(
            ["devagent", "review", "--json", "--rule", rule, temp_name],
            capture_output=True,
            cwd="/home/kostr2010/openharmony/standalone/arkcompiler",
        )
        print(f"rule: {rule}")
        print(f"patch: {temp_name}")
        print(f"stderr: {devagent_result.stderr}")
        print(f"stdout: {devagent_result.stdout}")
        return {"result": devagent_result.stdout}
    except Exception as e:
        return {"error": f"{str(e)}"}


def process_rules_config(project_root: str, rules_dir: str, rules_config: str):
    dir_to_rules = {}
    with open(rules_config) as cfg:
        for line in cfg:
            parsed_line = line.strip().split()
            project_prefix = os.path.abspath(
                os.path.join(project_root, parsed_line[0].removeprefix("/"))
            )
            rules = list(
                map(
                    lambda s: os.path.abspath(os.path.join(rules_dir, s)),
                    parsed_line[1:],
                )
            )
            dir_to_rules.update({project_prefix: rules})
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


async def devagent_task_code_review_action_run(
    task_id: int, url: str, db: sqlalchemy.ext.asyncio.AsyncSession
):
    try:
        project_root = None
        rules_dir = None
        rules_config = None

        if "arkcompiler_runtime_core" in url:
            project_root = RUNTIME_CORE_ROOT
            rules_dir = os.path.abspath(
                os.path.join(project_root, "static_core/.REVIEW_RULES")
            )
            rules_config = os.path.abspath(
                os.path.join(project_root, "static_core/REVIEW_RULES")
            )
        elif "arkcompiler_ets_frontend" in url:
            project_root = ETS_FRONTEND_ROOT
            rules_dir = os.path.abspath(
                os.path.join(project_root, "ets2panda/.REVIEW_RULES")
            )
            rules_config = os.path.abspath(
                os.path.join(project_root, "ets2panda/REVIEW_RULES")
            )
        else:
            await update_task_in_db(
                TaskStatus.TASK_STATUS_ERROR,
                f"Unsupported url {url} for code review!",
                task_id,
                db,
            )
            return

        dir_to_rules = process_rules_config(
            project_root=project_root, rules_dir=rules_dir, rules_config=rules_config
        )

        parsed_url = urllib.parse.urlparse(url)
        # ['', 'owner', 'remote', 'pull', 'pull_number']
        url_path = parsed_url.path.split("/")
        owner = url_path[1]
        repo = url_path[2]
        pr_number = url_path[4]
        gitcode_pr = get_gitcode_pr(owner, repo, pr_number)

        if "error" in gitcode_pr:
            await update_task_in_db(
                TaskStatus.TASK_STATUS_ERROR,
                f"Error during getting gitcode pr: {gitcode_pr['error']}",
                task_id,
                db,
            )
            return

        review_result = []

        with multiprocessing.Pool(4) as pool:
            review_result_tasks = []
            for gitcode_pr_file in gitcode_pr["files"]:
                relevant_rules = []
                for dir, rules in dir_to_rules.items():
                    file_abspath = os.path.abspath(
                        os.path.join(project_root, gitcode_pr_file["file"])
                    )
                    if dir != os.path.commonpath([dir, file_abspath]):
                        continue
                    relevant_rules += rules

                if len(relevant_rules) == 0:
                    continue

                diff = gitcode_pr_file["diff"]
                run_devagent = functools.partial(run_devagent_review, diff)
                review_result_tasks.append(pool.map_async(run_devagent, relevant_rules))
            review_result = [r.get() for r in review_result_tasks]

        print("here1")

        review_result_flat = [
            flattened_elem for elem in review_result for flattened_elem in elem
        ]

        print("here2")
        print(f"here, review_result_flat = {str(review_result_flat)}")

        # update task after LLM finished work
        await update_task_in_db(
            TaskStatus.TASK_STATUS_DONE, str(review_result_flat), task_id, db
        )
    except Exception as e:
        await update_task_in_db(
            TaskStatus.TASK_STATUS_ERROR,
            f"Unexpected error during processing of the task {str(e)}",
            task_id,
            db,
        )
        print(traceback.format_exc())
