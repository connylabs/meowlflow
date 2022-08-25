import json
import logging
from typing import Any

import click
from fastapi import FastAPI

from meowlflow.api import api
from meowlflow.sidecar import (
    register_infer_endpoint,
)


@click.option(
    "--endpoint",
    default="/infer",
    type=click.Path(),
    show_default=True,
)
@click.option(
    "--schema-path",
    default="/var/lib/meowlflow/schema.py",
    type=click.Path(),
    show_default=True,
)
def openapi(endpoint: str, schema_path: str) -> None:
    app = FastAPI()

    async def infer(_: Any) -> Any:
        return None

    register_infer_endpoint(
        logging.getLogger(),
        app,
        api.router,
        endpoint,
        infer,
        schema_path,
    )
    app.include_router(api.router)
    print(json.dumps(app.openapi()))
