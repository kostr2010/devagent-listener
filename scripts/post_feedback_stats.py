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

dotenv.load_dotenv()

GITCODE_TOKEN = os.getenv("GITCODE_TOKEN")
DB_PROTOCOL = os.getenv("DB_PROTOCOL")
DB_PORT = os.getenv("DB_PORT")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_USER = os.getenv("DB_USER")
DB_DB = os.getenv("DB_DB")
DB_HOSTNAME = os.getenv("DB_HOSTNAME")


class Issue(pydantic.BaseModel):
    id: int
    title: str
    number: int


class Target(pydantic.BaseModel):
    issue: Issue


class Response(pydantic.BaseModel):
    id: int
    body: str
    user: object
    target: Target


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
    await db_conn.close()

    report = _generate_report(user_feedback)

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
    model = Response.model_validate_json(data)
    print(model.model_dump_json())


def _generate_report(user_feedback: list[UserFeedback]) -> str:
    today = datetime.datetime.today()
    today_str = today.strftime("%Y-%m-%d")
    report = ""
    report += f"## {today_str}\n\n"

    feedback_today = list[UserFeedback](
        filter(
            lambda user_feedback: user_feedback.created_at.date() == today.date(),
            user_feedback,
        )
    )
    feedback_today_summary = _summarize_feedback(feedback_today)

    report += f"### Feedback today: {today_str}\n\n"
    report += _serialize_feedback_summary(feedback_today_summary)

    start_date = today - datetime.timedelta(days=7)
    start_date_str = start_date.strftime("%Y-%m-%d")
    feedback_in_timeframe = list(
        filter(
            lambda user_feedback: user_feedback.created_at.date() <= today.date()
            and user_feedback.created_at.date() >= start_date.date(),
            user_feedback,
        )
    )
    feedback_in_timeframe_summary = _summarize_feedback(feedback_in_timeframe)

    report += f"### Feedback in time frame: {start_date_str} - {today_str}\n\n"
    report += _serialize_feedback_summary(feedback_in_timeframe_summary)

    feedback_total_summary = _summarize_feedback(user_feedback)

    report += f"### Feedback entire time:\n\n"
    report += _serialize_feedback_summary(feedback_total_summary)

    return report


def _summarize_feedback(feedback: list[UserFeedback]) -> UserFeedbackSummary:
    feedback_summary = dict[str, list[int]]()

    for fb in feedback:
        rule = str(fb.rule)
        current_summary = feedback_summary.get(rule, list[int]([0, 0, 0, 0]))
        current_summary[int(fb.feedback)] = current_summary[int(fb.feedback)] + 1
        feedback_summary.update({rule: current_summary})

    return feedback_summary


def _serialize_feedback_summary(summary: UserFeedbackSummary) -> str:
    res = ""
    res += "| Rule name | TP | FP |\n"
    res += "|-----------|----|----|\n"
    for rule, feedback in summary.items():
        res += f"|`{rule}`|{feedback[Feedback.TRUE_POSITIVE.value]}|{feedback[Feedback.FALSE_POSITIVE.value]}|\n"
    res += "\n"
    return res


if __name__ == "__main__":
    asyncio.run(post_feedback_stats())
