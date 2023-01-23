from pathlib import Path
import logging
import importlib.util
from typing import TYPE_CHECKING, Any, Awaitable, Callable, Dict
import types

import aiohttp
import click
from fastapi import FastAPI, routing
import uvicorn

from meowlflow.api import api, info, base
from meowlflow.app import build_app
from meowlflow.integrations import sentry


def _load_module(module_path: Path, module_name: str) -> types.ModuleType:
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


@click.option(
    "--endpoint",
    default="/infer",
    type=str,
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
    type=click.Path(exists=True, dir_okay=False),
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
@sentry.options
def sidecar(
    endpoint: str,
    upstream: str,
    schema_path: Path,
    host: str,
    port: int,
    **kwargs: Dict[str, Any],
) -> None:

    log_fmt = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using model upstream at {upstream}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    sentry_kwargs = sentry.parse_kwargs(**kwargs)
    app = build_app(sentry_kwargs)

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
        app,  # nomypy, https://github.com/tiangolo/fastapi/issues/3927
        host=host,
        port=port,
        log_level="debug",
    )


Infer = Callable[[Any], Awaitable[Any]]


def get_infer(upstream: str) -> Infer:
    headers = {"Content-Type": "application/json; format=pandas-records"}

    async def infer(data: Any) -> Any:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                upstream,
                data=data,
                headers=headers,
            ) as response:
                return await response.json()

    return infer


def register_infer_endpoint(
    logger: logging.Logger,
    app: FastAPI,
    router: routing.APIRouter,
    endpoint: str,
    _infer: Infer,
    schema_path: Path,
) -> None:
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
    async def infer(request: schema.Request) -> Any:  # type: ignore
        data = request.transform()
        response = await _infer(data)
        return schema.Response.transform(response)
