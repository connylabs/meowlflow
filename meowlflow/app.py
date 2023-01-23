from typing import Any, Awaitable, Callable, Dict, List, Optional
import time

from fastapi import FastAPI, Request, Response
from starlette_exporter import (
    PrometheusMiddleware,
    handle_metrics,
)
from uvicorn.middleware.proxy_headers import (
    ProxyHeadersMiddleware,
)
from meowlflow.api.middlewares.errors import (
    configure_catch_exceptions_middleware,
)
from meowlflow.integrations import sentry


async def add_process_time_header(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


def build_app(sentry_config: Dict[str, Any]) -> FastAPI:
    # error-handling integrations
    error_handlers: List[Callable[[Exception], Optional[str]]] = []
    if ("dsn" in sentry_config) and (sentry_config["dsn"] != ""):
        sentry.sentry_sdk.init(
            dsn=sentry_config["dsn"],
            traces_sample_rate=sentry_config["traces_sample_rate"],
        )
        error_handlers.append(sentry.handle_error)

    catch_exceptions_middleware = configure_catch_exceptions_middleware(error_handlers)

    app = FastAPI()

    app.middleware("http")(add_process_time_header)
    app.add_middleware(PrometheusMiddleware, app_name="meowlflow")
    app.add_middleware(ProxyHeadersMiddleware)
    app.add_route("/metrics", handle_metrics)
    app.middleware("http")(catch_exceptions_middleware)

    return app
