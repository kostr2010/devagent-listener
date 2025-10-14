import functools
import sqlalchemy.ext.asyncio
import sqlalchemy.future
import fastapi
import subprocess
import os.path
import os
import urllib.parse
import traceback
import json
import git
import tempfile
import asyncio

from .models import Task, TaskStatus
from .gitcode_pr import get_gitcode_pr
from .repo_info import SUPPORTED_REPOS, RepoInfo


def run_devagent_review(workdir: str, patch: str, rule: str):
    try:
        devagent_result = subprocess.run(
            ["devagent", "review", "--json", "--rule", rule, patch],
            capture_output=True,
            cwd=workdir,
        )
        print(f"rule: {rule}")
        print(f"patch: {patch}")
        print(f"stderr: {devagent_result.stderr}")
        print(f"stdout: {devagent_result.stdout}")

        stderr = devagent_result.stderr.decode("utf-8")
        if len(stderr) > 0 and "Error" in stderr:
            return {"error": {"message": stderr, "patch": patch, "rule": rule}}

        stdout = devagent_result.stdout.decode("utf-8")
        return {"result": stdout}
    except Exception as e:
        return {"error": f"{str(e)}"}


def load_rules_config(workdir: str, repo_info: RepoInfo):
    dir_to_rules = {}

    rules_config_path = os.path.abspath(os.path.join(workdir, repo_info.rules_config))
    rules_dir_path = os.path.abspath(os.path.join(workdir, repo_info.rules_dir))

    with open(rules_config_path) as cfg:
        for line in cfg:
            parsed_line = line.strip().split()
            dir_relative = parsed_line[0].removeprefix("/")
            relevant_rules = parsed_line[1:]
            dir = os.path.abspath(os.path.join(workdir, dir_relative))
            rules = list(
                map(
                    lambda rule: os.path.abspath(os.path.join(rules_dir_path, rule)),
                    relevant_rules,
                )
            )
            dir_to_rules.update({dir: rules})

    return dir_to_rules


def parse_gitcode_pr_url(url: str):
    parsed_url = urllib.parse.urlparse(url)
    # ['', 'owner', 'repo', 'pull', 'pr_number']
    url_path = parsed_url.path.split("/")
    return {"owner": url_path[1], "repo": url_path[2], "pr_number": url_path[4]}


def get_gitcode_diff(url: str):
    parsed_url = parse_gitcode_pr_url(url)
    gitcode_pr = get_gitcode_pr(
        parsed_url["owner"], parsed_url["repo"], parsed_url["pr_number"]
    )

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
    parsed_url = parse_gitcode_pr_url(url)
    repo = parsed_url["repo"]

    if not repo:
        return None

    for repo_info in SUPPORTED_REPOS:
        if repo_info.repo == repo:
            return repo_info

    return None


def collect_relevant_rules(workdir: str, file: str, loaded_rules_config: dict):
    file_path = os.path.abspath(os.path.join(workdir, file))
    relevant_rules = set()
    for dir, rules in loaded_rules_config.items():
        if dir != os.path.commonpath([dir, file_path]):
            continue
        relevant_rules.update(rules)
    return relevant_rules


def initialize_workdir(workdir: str):
    # FIXME: replace with openharmony when integrating
    owner = "nazarovkonstantin"
    # FIXME: replace with necessary branch
    branch = "feature/review_rules_test"

    for repo_info in SUPPORTED_REPOS:
        clone_dst = os.path.abspath(os.path.join(workdir, repo_info.repo))
        url = f"https://gitcode.com/{owner}/{repo_info.repo}.git"

        repo = git.Repo.clone_from(url, clone_dst, allow_unsafe_protocols=True)
        repo.git.checkout(branch)


def devagent_schedule_diff_review(workdir: str, rules: list, diff: str, pool):
    # FIXME: remove this. generate temp patch file while devagent can't parse input as string
    temp = tempfile.NamedTemporaryFile(suffix=f".patch", delete=False)
    temp.write(diff.encode("utf-8"))
    patch = temp.name
    temp.close()

    run_devagent = functools.partial(run_devagent_review, workdir, patch)
    devagent_review_task = pool.map_async(run_devagent, rules)
    return devagent_review_task


def devagent_review_gitcode_pr(pr_diff, workdir: str, repo_info: RepoInfo, pool):
    # TODO: Later need to cache this
    rules_config = load_rules_config(workdir, repo_info)
    devagent_review_tasks = []

    for gitcode_pr_file in pr_diff["files"]:
        file = gitcode_pr_file["file"]
        diff = gitcode_pr_file["diff"]

        relevant_rules = collect_relevant_rules(workdir, file, rules_config)

        if len(relevant_rules) == 0:
            continue

        devagent_review_task = devagent_schedule_diff_review(
            workdir, relevant_rules, diff, pool
        )

        devagent_review_tasks.append(devagent_review_task)

    review_result_flat = [
        flattened_elem
        for elem in [r.get() for r in devagent_review_tasks]
        for flattened_elem in elem
    ]

    return review_result_flat


def devagent_review_postprocess(devagent_review: list):
    results = []
    errors = []
    for elem in devagent_review:
        if "error" in elem:
            errors.append(elem["error"])
        elif "result" in elem:
            results.append(json.loads(elem["result"]))
        else:
            print(f"Discarding element of the review result: {elem}")
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


async def devagent_task_code_review_action_run(
    task_id: int, url: str, db: sqlalchemy.ext.asyncio.AsyncSession, pool
):
    try:
        print(f"task {task_id} started with payload {url}")

        repo_info = url_to_repo_info(url)
        if not repo_info:
            raise Exception(f"Error during getting repo info for url {url}")

        with tempfile.TemporaryDirectory() as tmpdirname:
            await asyncio.to_thread(initialize_workdir, tmpdirname)

            print(f"task {task_id} initialized workdir {tmpdirname}")

            pr_diff = await asyncio.to_thread(get_gitcode_diff, url)
            if "error" in pr_diff:
                raise Exception(f"Error during getting gitcode pr: {pr_diff['error']}")

            print(f"task {task_id} got the diff for the {url}")

            devagent_workdir = os.path.abspath(os.path.join(tmpdirname, repo_info.repo))

            review_result = await asyncio.to_thread(
                devagent_review_gitcode_pr, pr_diff, devagent_workdir, repo_info, pool
            )

            print(f"task {task_id} finished review for the {url}")

            processed_review = devagent_review_postprocess(review_result)

            await update_task_in_db(
                TaskStatus.TASK_STATUS_DONE,
                json.dumps(processed_review),
                task_id,
                db,
            )

            print(f"task {task_id} updated status in db")
    except Exception as e:
        await set_task_failed_in_db(
            f"Unexpected error during processing of the task {str(e)}. Trace:\n{traceback.format_exc()}",
            task_id,
            db,
        )
