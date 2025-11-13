import sqlalchemy.ext.asyncio
import sqlalchemy.future
import os
import fastapi
import pydantic
import typing
import tempfile
import shutil
import datetime

from app.routes.api.v1.devagent.tasks.validation import validate_query_params
from app.postgres.models import Error, Patch

QUERY_PARAMS_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": dict(),
    "required": list(),
    "additionalProperties": True,
}


class Response(pydantic.BaseModel):
    archive: str


@validate_query_params(QUERY_PARAMS_SCHEMA)
async def action_errors(
    postgres: sqlalchemy.ext.asyncio.AsyncSession,
    query_params: dict[str, typing.Any],
) -> Response:
    try:
        wd = tempfile.mkdtemp()

        query_res = await postgres.execute(sqlalchemy.future.select(Error))
        errors = query_res.scalars().all()

        for error in errors:
            error_wd = os.path.abspath(os.path.join(wd, str(error.id)))
            os.makedirs(error_wd)

            env_file = os.path.join(error_wd, ".env")
            with open(env_file, "w") as e:
                e.write(f"PROJECT={error.project}\n")
                e.write(f"REV_PROJECT={error.rev_project}\n")
                e.write(f"REV_DEV_RULES={error.rev_devagent}\n")
                e.write(f"REV_DEVAGENT={error.rev_arkcompiler_development_rules}\n")
                e.write(f"RULE={error.rule}\n")
                e.write(f"MESSAGE={error.message}\n")

            r = await postgres.execute(
                sqlalchemy.future.select(Patch).where(Patch.id == error.patch)
            )
            patch = r.scalars().first()

            if patch == None:
                raise Exception(f"Could not get patch {error.patch} from the db")

            patch_file = os.path.join(error_wd, str(error.patch))
            with open(patch_file, "w") as p:
                patch_content = str(patch.content)
                p.write(patch_content)

            context_file = os.path.join(error_wd, "context.md")
            with open(context_file, "w") as p:
                if patch.context == None:
                    context = ""
                else:
                    context = str(patch.context)
                p.write(context)
        archive = os.path.join(
            tempfile.mkdtemp(), f"errors-{datetime.datetime.now().date()}"
        )
        shutil.make_archive(archive, "zip", wd, ".")
    except fastapi.HTTPException as httpe:
        raise httpe
    except Exception as e:
        raise fastapi.HTTPException(
            status_code=500,
            detail=f"[dataset_errors] Exception {type(e)} occured during handling of task dataset errors: {str(e)}",
        )
    else:
        return Response(archive=f"{archive}.zip")
