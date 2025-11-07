import pydantic
import typing


class Response(pydantic.BaseModel):
    status: typing.Literal["healthy"]


def endpoint_health() -> Response:
    return Response(status="healthy")
