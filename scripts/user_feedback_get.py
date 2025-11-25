import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.routes.api.v1.devagent.tasks.user_feedback.actions.get import Response
from app.routes.api.v1.devagent.tasks.user_feedback.user_feedback import Action
from app.routes.api.v1.devagent.endpoint import TaskKind
from scripts.internal.devagent_request import devagent_request


def user_feedback_set() -> None:
    """
    argv[0] -- script name
    argv[1] -- feedback_id
    """

    query_params = []
    query_params.append(f"task_kind={TaskKind.TASK_KIND_USER_FEEDBACK.value}")
    query_params.append(f"action={Action.ACTION_GET.value}")
    query_params.append(f"feedback_id={sys.argv[1]}")

    response = devagent_request("api/v1/devagent", query_params)

    if response == None:
        return

    model = Response.model_validate(response)

    print(model.model_dump_json())


if __name__ == "__main__":
    user_feedback_set()
