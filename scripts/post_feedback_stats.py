import pydantic
import dotenv
import http.client
import json
import os
import asyncio
import sys
import datetime

sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from app.db.async_db import AsyncDBConnectionConfig, AsyncDBConnection
from app.db.schemas.user_feedback import UserFeedback, Feedback
from app.db.schemas.error import Error
from app.db.schemas.patch import Patch

dotenv.load_dotenv()

GITCODE_TOKEN = os.getenv("GITCODE_TOKEN")
DB_PROTOCOL = os.getenv("DB_PROTOCOL")
DB_PORT = os.getenv("DB_PORT")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_DB = os.getenv("DB_DB")
DB_HOSTNAME = os.getenv("DB_HOSTNAME")


UserFeedbackSummary = dict[str, list[int]]


async def post_feedback_stats() -> None:
    """
    argv[0] -- script name
    """

    db_cfg = AsyncDBConnectionConfig(
        protocol=DB_PROTOCOL,
        host=DB_HOSTNAME,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_DB,
    )

    db_conn = AsyncDBConnection(db_cfg)
    async for db_session in db_conn.get_session():
        user_feedback = await db_session.select_user_feebdack(
            lambda: UserFeedback.created_at.isnot(None)
        )
        patches = await db_session.select_patches(lambda: Patch.created_at.isnot(None))
        errors = await db_session.select_errors(lambda: Error.created_at.isnot(None))
    await db_conn.close()

    report = _generate_report(user_feedback, patches, errors)

    payload = json.dumps({"body": report})
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    conn = http.client.HTTPSConnection("api.gitcode.com")
    conn.request(
        "POST",
        f"/api/v5/repos/nazarovkonstantin/arkcompiler_development_rules/issues/6/comments?access_token={GITCODE_TOKEN}",
        payload,
        headers,
    )

    response = conn.getresponse()
    data = response.read().decode("utf-8")
    print(data)


def _generate_report(
    user_feedback: list[UserFeedback], patches: list[Patch], errors: list[Error]
) -> str:
    today = datetime.datetime.today()
    today_str = today.strftime("%Y-%m-%d")
    report = ""
    report += f"## {today_str}\n\n"

    feedback_today = list[UserFeedback](
        filter(
            lambda fb: fb.created_at.date() == today.date(),
            user_feedback,
        )
    )
    patches_today = list[Patch](
        filter(
            lambda p: p.created_at.date() == today.date(),
            patches,
        )
    )
    errors_today = list[Error](
        filter(
            lambda e: e.created_at.date() == today.date(),
            errors,
        )
    )

    report += f"### Feedback today: {today_str}\n\n"
    report += _serialize_feedback_summary(feedback_today)

    report += f"### False positives today: {today_str}\n\n"
    report += _serialize_false_positives(feedback_today, patches_today)

    report += f"### Errors today: {today_str}\n\n"
    report += _serialize_errors(errors_today, patches_today)

    start_date = today - datetime.timedelta(days=7)
    start_date_str = start_date.strftime("%Y-%m-%d")
    feedback_in_timeframe = list(
        filter(
            lambda user_feedback: user_feedback.created_at.date() <= today.date()
            and user_feedback.created_at.date() >= start_date.date(),
            user_feedback,
        )
    )

    report += f"### Feedback in time frame: {start_date_str} - {today_str}\n\n"
    report += _serialize_feedback_summary(feedback_in_timeframe)

    report += f"### Feedback entire time:\n\n"
    report += _serialize_feedback_summary(user_feedback)

    return report


def _serialize_errors(errors: list[Error], patches: list[Patch]) -> str:
    patch_mappping = {str(p.id): p for p in patches}
    report = ""
    for e in errors:
        issue_url = _create_issue_for_error(e, patch_mappping[str(e.patch)])
        report += f"- {issue_url}\n"
    report += "\n"

    return report


def _create_issue_for_error(error: Error, patch: Patch) -> str:
    body = ""
    body += "## General info:\n\n"
    body += "```\n"
    body += f"PROJECT={str(error.project)}\n"
    body += f"PROJECT_REVISION={str(error.rev_project)}\n"
    body += f"RULES_REVISION={str(error.rev_arkcompiler_development_rules)}\n"
    body += f"DEVAGENT_REVISION={str(error.rev_devagent)}\n"
    body += f"RULE={str(error.rule)}\n"
    body += f"MESSAGE={str(error.message)}\n"
    body += "\n"
    body += "```\n"
    body += "\n"
    body += "## Context:\n"
    body += "\n"
    body += "```\n"
    body += str(patch.context)
    body += "\n"
    body += "```\n"
    body += "\n"
    body += "## Patch:\n"
    body += "\n"
    body += "```patch\n"
    body += str(patch.content)
    body += "\n"
    body += "```\n"
    body += "\n"
    conn = http.client.HTTPSConnection("api.gitcode.com")
    conn.request(
        "POST",
        f"/api/v5/repos/nazarovkonstantin/issues?access_token={GITCODE_TOKEN}",
        json.dumps(
            {
                "repo": "arkcompiler_development_rules",
                "title": f"[Error] {str(error.rule)}/{str(patch.id)}",
                "body": body,
            }
        ),
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    response = conn.getresponse()

    data = json.loads(response.read())

    return str(data["html_url"])


def _serialize_feedback_summary(feedback: list[UserFeedback]) -> str:
    feedback_summary = dict[str, list[int]]()

    for fb in feedback:
        current_summary = feedback_summary.get(str(fb.rule), list[int]([0, 0, 0, 0]))
        current_summary[int(fb.feedback)] = current_summary[int(fb.feedback)] + 1
        feedback_summary.update({str(fb.rule): current_summary})

    report = ""
    report += "| Rule name | TP | FP |\n"
    report += "|-----------|----|----|\n"
    for rule, stats in feedback_summary.items():
        report += f"|`{rule}`|{stats[Feedback.TRUE_POSITIVE.value]}|{stats[Feedback.FALSE_POSITIVE.value]}|\n"
    report += "\n"

    return report


def _serialize_false_positives(
    feedback: list[UserFeedback], patches: list[Patch]
) -> str:
    patch_mappping = {str(p.id): p for p in patches}
    group_by_patch_by_rule = dict[str, dict[str, list[UserFeedback]]]()

    for fb in feedback:
        if fb.feedback != Feedback.FALSE_POSITIVE.value:
            continue
        patch_name = str(fb.patch)
        rule_name = str(fb.rule)
        rule_to_feedback = group_by_patch_by_rule.get(
            patch_name, dict[str, list[UserFeedback]]()
        )
        feedback_list = rule_to_feedback.get(rule_name, list[UserFeedback]())
        feedback_list.append(fb)
        rule_to_feedback.update({rule_name: feedback_list})
        group_by_patch_by_rule.update({patch_name: rule_to_feedback})

    report = ""
    for patch_name, rule_to_feedback in group_by_patch_by_rule.items():
        patch = patch_mappping[patch_name]
        for rule_name, feedback_list in rule_to_feedback.items():
            issue_url = _create_issue_for_false_positive(
                rule_name, patch, feedback_list
            )
            report += f"- {issue_url}\n"
    report += "\n"

    return report


def _create_issue_for_false_positive(
    rule_name: str, patch: Patch, feedback_list: list[UserFeedback]
) -> str:
    body = ""
    body += "## General info:\n\n"
    body += "```\n"
    fb = feedback_list[0]
    body += f"PROJECT={str(fb.project)}\n"
    body += f"PROJECT_REVISION={str(fb.rev_project)}\n"
    body += f"RULES_REVISION={str(fb.rev_arkcompiler_development_rules)}\n"
    body += f"DEVAGENT_REVISION={str(fb.rev_devagent)}\n"
    body += f"RULE={str(fb.rule)}\n"
    body += "\n"
    body += "```\n"
    body += "## False positives:\n\n"
    for feedback in feedback_list:
        body += f"- {str(feedback.file)}:{str(feedback.line)}\n"
    body += "\n"
    body += "## Context:\n"
    body += "\n"
    body += "```\n"
    body += str(patch.context)
    body += "\n"
    body += "```\n"
    body += "\n"
    body += "## Patch:\n"
    body += "\n"
    body += "```patch\n"
    body += str(patch.content)
    body += "\n"
    body += "```\n"
    body += "\n"
    conn = http.client.HTTPSConnection("api.gitcode.com")
    conn.request(
        "POST",
        f"/api/v5/repos/nazarovkonstantin/issues?access_token={GITCODE_TOKEN}",
        json.dumps(
            {
                "repo": "arkcompiler_development_rules",
                "title": f"[FP] {rule_name}/{str(patch.id)}",
                "body": body,
            }
        ),
        {
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    response = conn.getresponse()

    data = json.loads(response.read())

    return str(data["html_url"])


if __name__ == "__main__":
    asyncio.run(post_feedback_stats())
