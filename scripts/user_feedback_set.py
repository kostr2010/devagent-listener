import sys
import os

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.routes.api.v1.devagent.tasks.user_feedback.actions.set import (
    Response,
    _encrypt_project_file_line_rule,
)
from app.routes.api.v1.devagent.tasks.user_feedback.user_feedback import Action
from app.routes.api.v1.devagent.endpoint import TaskKind
from scripts.internal.devagent_request import devagent_request


def user_feedback_set() -> None:
    """
    argv[0] -- script name
    argv[1] -- task_id
    argv[2] -- feedback
    argv[3] -- project
    argv[4] -- file
    argv[5] -- line
    argv[6] -- rule
    """

    query_params = []
    query_params.append(f"task_kind={TaskKind.TASK_KIND_USER_FEEDBACK.value}")
    query_params.append(f"action={Action.ACTION_SET.value}")
    query_params.append(f"task_id={sys.argv[1]}")
    query_params.append(f"feedback={sys.argv[2]}")
    project = sys.argv[3]
    file = sys.argv[4]
    line = sys.argv[5]
    rule = sys.argv[6]
    data = _encrypt_project_file_line_rule(project, file, line, rule)
    query_params.append(f"data={data}")

    response = devagent_request("api/v1/devagent", query_params)

    if response == None:
        return

    model = Response(**response)

    print(model.model_dump_json())


if __name__ == "__main__":
    user_feedback_set()
