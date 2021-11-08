import json
import logging

import click
from fastapi import FastAPI

from meowlflow.api import api
from meowlflow.sidecar import register_endpoint


@click.option("--endpoint", default="/infer", type=click.Path(), show_default=True)
@click.option(
    "--schema-path",
    default="/var/lib/meowlflow/schema.py",
    type=click.Path(),
    show_default=True,
)
def openapi(endpoint, schema_path):
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    register_endpoint(logger, api.router, endpoint, "", schema_path)
    app = FastAPI()
    app.include_router(api.router)
    print(json.dumps(app.openapi()))
