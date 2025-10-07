import dataclasses
import collections.abc
import fastapi


@dataclasses.dataclass
class RequestParam:
    name: str
    default_value: str | None
    validator: collections.abc.Callable[[str | None], None] | None


def validate_request_params(params: list[RequestParam], request: fastapi.Request):
    for param in params:
        param_v = request.query_params.get(param.name)
        if param_v == None:
            request.query_params.__setattr__(param.name, param.default_value)
        validator = param.validator
        if validator != None:
            validator(param_v)


def register_request_param(
    name: str,
    default_value: str | None,
    validator: collections.abc.Callable[[str | None], None] | None,
    param_list: list[RequestParam],
):
    param_list.append(
        RequestParam(name=name, default_value=default_value, validator=validator)
    )
