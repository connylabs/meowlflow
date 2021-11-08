import pathlib
from pathlib import Path
import time
import logging
import importlib.util

import aiohttp
import click
from fastapi import FastAPI, Request
import sentry_sdk
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette_exporter import PrometheusMiddleware, handle_metrics
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
import uvicorn

from meowlflow.api import api, info, base
from meowlflow.api.middlewares.errors import catch_exceptions_middleware
from meowlflow.exception import UnauthorizedAccess
from meowlflow.config import GCONFIG


if "url" in GCONFIG.sentry:
    sentry_sdk.init(  # pylint: disable=abstract-class-instantiated # noqa: E0110
        dsn=GCONFIG.sentry["url"],
        traces_sample_rate=1.0,
        environment=GCONFIG.sentry["environment"],
    )


def _create_tmp_dir():
    pathlib.Path(GCONFIG.meowlflow["download_dir"]).mkdir(parents=True, exist_ok=True)
    pathlib.Path(GCONFIG.meowlflow["prometheus_dir"]).mkdir(parents=True, exist_ok=True)


def _load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _to_endpoint_path(endpoint):
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


async def add_check_token(request: Request, call_next):
    if GCONFIG.meowlflow["token"] and (
        "token" not in request.headers
        or request.headers["token"] != GCONFIG.meowlflow["token"]
    ):
        raise UnauthorizedAccess("NoAuth")
    return await call_next(request)


_create_tmp_dir()
app.add_middleware(PrometheusMiddleware, app_name="meowlflow")
app.add_middleware(ProxyHeadersMiddleware)
app.add_middleware(SentryAsgiMiddleware)
app.add_route("/metrics", handle_metrics)
app.middleware("http")(catch_exceptions_middleware)


@click.option("--endpoint", default="/infer", type=click.Path(), show_default=True)
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
@click.option("--host", default="0.0.0.0", type=str, show_default=True)
@click.option("--port", default=8000, type=int, show_default=True)
def sidecar(endpoint, upstream, schema_path, host, port):
    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using model upstream at {upstream}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    register_endpoint(logger, api.router, endpoint, upstream, schema_path)

    app.include_router(info.router)
    app.include_router(api.router)
    uvicorn.run(app, host=host, port=port, log_level="debug")


def register_endpoint(logger, router, endpoint, upstream, schema_path):
    logger.info(f"Loading schema module from {schema_path}")
    schema = _load_module(schema_path, "schema")

    if not issubclass(schema.Request, base.BaseRequest):
        raise TypeError(f"Expected {schema.Request} to implement {base.BaseRequest}")
    if not issubclass(schema.Response, base.BaseResponse):
        raise TypeError(f"Expected {schema.Response} to implement {base.BaseResponse}")

    endpoint = _to_endpoint_path(endpoint)

    @router.post(endpoint, response_model=schema.Response)
    async def infer(request: schema.Request):
        headers = {"Content-Type": "application/json; format=pandas-records"}
        data = request.transform()

        async with aiohttp.ClientSession() as session:
            async with session.post(upstream, data=data, headers=headers) as response:
                return schema.Response.transform(await response.json())
