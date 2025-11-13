import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.routes.api.v1.devagent.tasks.code_review.actions.run import Response
from app.routes.api.v1.devagent.tasks.code_review.code_review import Action
from app.routes.api.v1.devagent.endpoint import TaskKind
from scripts.internal.devagent_request import devagent_request


def code_review_run() -> None:
    """
    argv[0] -- script name
    argv[1] -- payload
    """

    query_params = []
    query_params.append(f"task_kind={TaskKind.TASK_KIND_CODE_REVIEW.value}")
    query_params.append(f"action={Action.ACTION_RUN.value}")
    query_params.append(f"payload={sys.argv[1]}")

    response = devagent_request("api/v1/devagent", query_params)

    model = Response(**response)

    print(model.model_dump_json())


if __name__ == "__main__":
    code_review_run()
