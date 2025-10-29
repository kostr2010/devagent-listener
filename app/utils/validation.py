import fastapi
import jsonschema
import functools
import asyncio


def validate_result(schema: dict):
    """Decorator for the function's result validation

    Args:
        schema (dict): schema used to validate result of the function
    """

    def decorator(func):
        if asyncio.iscoroutinefunction(func):

            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                result = await func(*args, **kwargs)
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
            def wrapper(*args, **kwargs):
                result = func(*args, **kwargs)
                try:
                    jsonschema.validate(result, schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=500,
                        detail=f"Error while validating {func.__name__}'s result : {str(e)}",
                    )
                return result

        return wrapper

    return decorator
