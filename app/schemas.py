import pydantic


class StartReviewResponse(pydantic.BaseModel):
    task_id: int
