_TASK_INFO_PATCH_CONTENT_PREFIX = "patch_content_"

_TASK_INFO_PATCH_CONTEXT_PREFIX = "patch_context_"

_TASK_INFO_RULE_PREFIX = "ETS"

_TASK_INFO_PROJECT_REVISION_PREFIX = "rev_"


def task_info_task_id_key() -> str:
    return "task_id"


def task_info_rules_revision_key() -> str:
    return task_info_project_revision_key("rules")


def task_info_devagent_revision_key() -> str:
    return task_info_project_revision_key("devagent")


def task_info_project_revision_key(project_name: str) -> str:
    return f"{_TASK_INFO_PROJECT_REVISION_PREFIX}{project_name}"


def task_info_patch_content_key(patch_name: str) -> str:
    return f"{_TASK_INFO_PATCH_CONTENT_PREFIX}{patch_name}"


def task_info_patch_context_key(patch_name: str) -> str:
    return f"{_TASK_INFO_PATCH_CONTEXT_PREFIX}{patch_name}"


def task_info_is_valid_key(key: str) -> bool:
    return (
        key == "task_id"
        or key.startswith(_TASK_INFO_PATCH_CONTENT_PREFIX)
        or key.startswith(_TASK_INFO_PATCH_CONTEXT_PREFIX)
        or key.startswith(_TASK_INFO_RULE_PREFIX)
        or key.startswith(_TASK_INFO_PROJECT_REVISION_PREFIX)
    )


TASK_INFO_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "description": "Schema of the redis hash storage for given task id",
    "type": "object",
    "properties": {
        task_info_task_id_key(): {
            "description": "Task id associated with this info",
            "type": "string",
        },
        task_info_rules_revision_key(): {
            "description": "Revision of the rules used for the review",
            "type": "string",
        },
        task_info_devagent_revision_key(): {
            "description": "Revision of the rules used for the review",
            "type": "string",
        },
    },
    "patternProperties": {
        # TODO: fix when new rules are added or patch format changes
        f"^{_TASK_INFO_PATCH_CONTENT_PREFIX}.*$": {
            "description": "Patch name mapped to the content of the patch",
            "type": "string",
        },
        f"^{_TASK_INFO_PATCH_CONTEXT_PREFIX}.*$": {
            "description": "Patch name mapped to the context of the patch",
            "type": "string",
        },
        f"^{_TASK_INFO_RULE_PREFIX}.*$": {
            "description": "Rule name mapped to the patch name",
            "type": "string",
        },
        f"^{_TASK_INFO_PROJECT_REVISION_PREFIX}.*/.*$": {
            "description": "Project name mapped to it's revision",
            "type": "string",
        },
    },
    "required": [
        task_info_task_id_key(),
        task_info_rules_revision_key(),
        task_info_devagent_revision_key(),
    ],
    "additionalProperties": False,
}
