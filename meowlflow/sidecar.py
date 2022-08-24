from pathlib import Path
import time
import logging
import importlib.util
from typing import TYPE_CHECKING
import types

import aiohttp
import click
from fastapi import FastAPI, Request
from starlette_exporter import (
    PrometheusMiddleware,
    handle_metrics,
)
from uvicorn.middleware.proxy_headers import (
    ProxyHeadersMiddleware,
)
import uvicorn

from meowlflow.api import api, info, base
from meowlflow.api.middlewares.errors import (
    catch_exceptions_middleware,
)


def _load_module(module_path: str, module_name: str) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if TYPE_CHECKING:
        assert spec is not None
    module = importlib.util.module_from_spec(spec)
    if TYPE_CHECKING:
        assert module is not None
        assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _to_endpoint_path(endpoint: str) -> str:
    endpoint = Path(endpoint).as_posix().strip("/")
    if endpoint:
        return "/" + endpoint
    return "/"


app = FastAPI()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(PrometheusMiddleware, app_name="meowlflow")
app.add_middleware(ProxyHeadersMiddleware)
app.add_route("/metrics", handle_metrics)
app.middleware("http")(catch_exceptions_middleware)


@click.option(
    "--endpoint",
    default="/infer",
    type=click.Path(),
    show_default=True,
)
@click.option(
    "--upstream",
    default="http://127.0.0.1:8080/invocations",
    type=str,
    show_default=True,
)
@click.option(
    "--schema-path",
    default="/var/lib/meowlflow/schema.py",
    type=click.Path(),
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
def sidecar(
    endpoint: str, upstream: str, schema_path: str, host: str, port: str
) -> None:
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using model upstream at {upstream}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    register_infer_endpoint(
        logger,
        app,
        api.router,
        endpoint,
        get_infer(upstream),
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


def get_infer(upstream):
    headers = {"Content-Type": "application/json; format=pandas-records"}

    async def infer(data):
        async with aiohttp.ClientSession() as session:
            async with session.post(
                upstream,
                data=data,
                headers=headers,
            ) as response:
                return await response.json()

    return infer


def register_infer_endpoint(
    logger,
    app,
    router,
    endpoint,
    _infer,
    schema_path,
):
    if logger is not None:
        logger.info(f"Loading schema module from {schema_path}")
    schema = _load_module(schema_path, "schema")

    if not issubclass(schema.Request, base.BaseRequest):
        raise TypeError(f"Expected {schema.Request} to implement {base.BaseRequest}")
    if not issubclass(schema.Response, base.BaseResponse):
        raise TypeError(f"Expected {schema.Response} to implement {base.BaseResponse}")

    for attr in [
        "title",
        "description",
        "version",
        "terms_of_service",
        "license_info",
        "servers",
    ]:
        value = getattr(schema, attr, None)
        if value is not None:
            setattr(app, attr, value)

    endpoint = _to_endpoint_path(endpoint)

    @router.post(endpoint, response_model=schema.Response)
    async def infer(request: schema.Request):
        data = request.transform()
        response = await _infer(data)
        return schema.Response.transform(response)
