import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.routes.api.v1.devagent.tasks.dataset.actions.user_feedback import Response
from app.routes.api.v1.devagent.tasks.dataset.dataset import Action
from app.routes.api.v1.devagent.endpoint import TaskKind
from scripts.internal.devagent_request import devagent_request


def code_review_get() -> None:
    """
    argv[0] -- script name
    """

    query_params = []
    query_params.append(f"task_kind={TaskKind.TASK_KIND_DATASET.value}")
    query_params.append(f"action={Action.ACTION_USER_FEEDBACK.value}")

    response = devagent_request("api/v1/devagent", query_params)

    if response == None:
        return

    model = Response.model_validate(response)

    print(model.model_dump_json())


if __name__ == "__main__":
    code_review_get()
