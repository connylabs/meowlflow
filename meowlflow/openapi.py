import json
import logging

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
def openapi(endpoint, schema_path):
    app = FastAPI()
    register_infer_endpoint(
        None,
        app,
        api.router,
        endpoint,
        None,
        schema_path,
    )
    app.include_router(api.router)
    print(json.dumps(app.openapi()))
