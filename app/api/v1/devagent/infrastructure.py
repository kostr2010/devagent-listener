import fastapi
import jsonschema
import functools
import asyncio


def validate_response(schema: dict):
    """Decorator for the response validation

    Args:
        schema (dict): schema used to validate response of the endpoint
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
                        detail=f"Error while validating response : {str(e)}",
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
                        detail=f"Error while validating response : {str(e)}",
                    )
                return result

        return wrapper

    return decorator


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
                    jsonschema.validate(kwargs["query_params"], schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=500,
                        detail=f"Error while validating query_params : {str(e)}",
                    )
                return await func(*args, **kwargs)

        else:

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    jsonschema.validate(kwargs["query_params"], schema)
                except Exception as e:
                    raise fastapi.HTTPException(
                        status_code=500,
                        detail=f"Error while validating query_params : {str(e)}",
                    )
                return func(*args, **kwargs)

        return wrapper

    return decorator
