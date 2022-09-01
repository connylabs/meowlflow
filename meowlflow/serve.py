import logging
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import click
from mlflow.models.container import MODEL_PATH
from mlflow.pyfunc import (
    PyFuncModel,
    load_model,
)
from mlflow.utils.file_utils import (
    path_to_local_file_uri,
)
from mlflow.pyfunc import (
    backend as mlflow_backend,
)
import uvicorn

from meowlflow.api import api, info
from meowlflow.sidecar import (
    Infer,
    app,
    register_infer_endpoint,
)


@click.option(
    "--endpoint",
    default="/infer",
    type=str,
    show_default=True,
)
@click.option(
    "--schema-path",
    default="/var/lib/meowlflow/schema.py",
    type=click.Path(exists=True, dir_okay=False),
    show_default=True,
)
@click.option(
    "--model-path",
    default=MODEL_PATH,
    type=str,
    show_default=True,
)
@click.option(
    "--host",
    default="0.0.0.0",
    type=str,
    show_default=True,
)
@click.option(
    "--port",
    default=8000,
    type=int,
    show_default=True,
)
def serve(
    endpoint: str, schema_path: Path, model_path: str, host: str, port: int
) -> None:
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    try:
        # try to load a local artifact
        model = load_model(path_to_local_file_uri(model_path))
        logger.info(f"Loaded local model artifact from {model_path}")
    except OSError as e:
        try:
            # try to load a remote artifact
            with TemporaryDirectory() as temp_dir:
                local_path = mlflow_backend._download_artifact_from_uri(
                    model_path,
                    output_path=temp_dir,
                )
                model = load_model(path_to_local_file_uri(local_path))
                logger.info(f"Loaded remote model artifact from {model_path}")
        except Exception:
            # if both fail, raise the original error
            raise e

    register_infer_endpoint(
        logger,
        app,
        api.router,
        endpoint,
        get_infer(model),
        schema_path,
    )
    app.include_router(info.router)
    app.include_router(api.router)
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="debug",
    )


def get_infer(model: PyFuncModel) -> Infer:
    async def infer(data: Any) -> Any:
        return model.predict(data)

    return infer
