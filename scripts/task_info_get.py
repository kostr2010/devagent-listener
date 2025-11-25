import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.routes.api.v1.devagent.tasks.task_info.actions.get import Response
from app.routes.api.v1.devagent.tasks.task_info.task_info import Action
from app.routes.api.v1.devagent.endpoint import TaskKind
from scripts.internal.devagent_request import devagent_request


def task_info_get() -> None:
    """
    argv[0] -- script name
    argv[1] -- task_id
    """

    query_params = []
    query_params.append(f"task_kind={TaskKind.TASK_KIND_TASK_INFO.value}")
    query_params.append(f"action={Action.ACTION_GET.value}")
    query_params.append(f"task_id={sys.argv[1]}")

    response = devagent_request("api/v1/devagent", query_params)

    if response == None:
        return

    print(json.dumps(response))


if __name__ == "__main__":
    task_info_get()
