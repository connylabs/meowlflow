import logging

import click
import json
from mlflow.models.container import MODEL_PATH
from mlflow.pyfunc import load_model, scoring_server
from mlflow.utils.file_utils import path_to_local_file_uri
from mlflow.utils.proto_json_utils import _get_jsonable_obj
import uvicorn

from meowlflow.api import api, info
from meowlflow.sidecar import app, register_infer_endpoint


@click.option("--endpoint", default="/infer", type=click.Path(), show_default=True)
@click.option(
    "--schema-path",
    default="/var/lib/meowlflow/schema.py",
    type=click.Path(),
    show_default=True,
)
@click.option(
    "--model-path",
    default=MODEL_PATH,
    type=click.Path(),
    show_default=True,
)
@click.option("--host", default="0.0.0.0", type=str, show_default=True)
@click.option("--port", default=8000, type=int, show_default=True)
def serve(endpoint, schema_path, model_path, host, port):
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    model = load_model(path_to_local_file_uri(model_path))
    model_schema = model.metadata.get_input_schema()

    register_infer_endpoint(
        logger, app, api.router, endpoint, get_infer(model, model_schema), schema_path
    )
    app.include_router(info.router)
    app.include_router(api.router)
    uvicorn.run(app, host=host, port=port, log_level="debug")


def get_infer(model, schema):
    async def infer(data):
        data = scoring_server.parse_json_input(
            json_input=data,
            orient="records",
            schema=schema,
        )
        prediction = model.predict(data)
        return json.loads(
            json.dumps(_get_jsonable_obj(prediction, pandas_orient="records"))
        )

    return infer
