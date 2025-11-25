import fastapi
import jsonschema
import functools
import asyncio
import typing

RT = typing.TypeVar("RT")  # return type

import pydantic


def validate_query_params(
    model: type[pydantic.BaseModel],
) -> typing.Callable[[typing.Callable[..., RT]], typing.Callable[..., RT]]:
    """Decorator for the query_params validation

    Args:
        schema (dict): schema used to validate query params of the endpoint

    Note:
        For this decorator to work correctly, query_params argument MUST be passed as kwarg
    """

    def decorator(func: typing.Callable[..., RT]) -> typing.Callable[..., RT]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> RT:
                try:
                    validated_query_params = model.model_validate(
                        kwargs["query_params"]
                    )
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=400,
                        detail=f"Error while validating {func.__name__}'s query_params : {str(e)}",
                    )
                kwargs["query_params"] = validated_query_params
                res: RT = await func(*args, **kwargs)
                return res

        else:

            @functools.wraps(func)
            def wrapper(*args: typing.Any, **kwargs: typing.Any) -> RT:
                try:
                    validated_query_params = model.model_validate(
                        kwargs["query_params"]
                    )
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=400,
                        detail=f"Error while validating {func.__name__}'s query_params : {str(e)}",
                    )
                kwargs["query_params"] = validated_query_params
                res: RT = func(*args, **kwargs)
                return res

        return wrapper  # type: ignore

    return decorator


def validate_result(
    schema: dict[str, typing.Any],
) -> typing.Callable[[typing.Callable[..., RT]], typing.Callable[..., RT]]:
    """Decorator for the function's result validation

    NOTE: DO NOT USE, prefer to use pydantic

    Args:
        schema (dict[str, object]): schema used to validate result of the function
    """

    def decorator(func: typing.Callable[..., RT]) -> typing.Callable[..., RT]:
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args: typing.Any, **kwargs: typing.Any) -> RT:
                result: RT = await func(*args, **kwargs)
                try:
                    jsonschema.validate(result, schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=500,
                        detail=f"Error while validating {func.__name__}'s result : {str(e)}",
                    )
                return result

        else:

            @functools.wraps(func)
            def wrapper(*args: typing.Any, **kwargs: typing.Any) -> RT:
                result = func(*args, **kwargs)
                try:
                    jsonschema.validate(result, schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=500,
                        detail=f"Error while validating {func.__name__}'s result : {str(e)}",
                    )
                return result

        return wrapper  # type: ignore

    return decorator
