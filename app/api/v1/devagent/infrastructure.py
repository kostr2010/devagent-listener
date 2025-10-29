import fastapi
import jsonschema
import functools
import asyncio


def validate_query_params(schema: dict):
    """Decorator for the query_params validation

    Args:
        schema (dict): schema used to validate query params of the endpoint

    Note:
        For this decorator to work correctly, query_params argument MUST be passed as kwarg
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                try:
                    jsonschema.validate(dict(kwargs["query_params"]), schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=400,
                        detail=f"Error while validating {func.__name__}'s query_params : {str(e)}",
                    )
                return await func(*args, **kwargs)

        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    jsonschema.validate(dict(kwargs["query_params"]), schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=400,
                        detail=f"Error while validating {func.__name__}'s query_params : {str(e)}",
                    )
                return func(*args, **kwargs)

        return wrapper

    return decorator
