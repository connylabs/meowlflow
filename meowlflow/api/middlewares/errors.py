import traceback
import logging
from typing import Awaitable, Callable, List, Optional

from starlette.responses import JSONResponse
from fastapi import Request, Response
from meowlflow.exception import MeowlflowException

logger = logging.getLogger(__name__)


def configure_catch_exceptions_middleware(
    handlers: List[Callable[[Exception], Optional[str]]] = []
) -> Callable[[Request, Callable[[Request], Awaitable[Response]]], Awaitable[Response]]:
    async def catch_exceptions_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        try:
            return await call_next(request)

        except MeowlflowException as error:
            logger.error(error)
            logger.error(traceback.format_exc())

            for handler in handlers:
                try:
                    handler(error)
                except Exception as handler_error:
                    logger.error(handler_error)
                    logger.error(traceback.format_exc())

            return JSONResponse(
                {"error": error.to_dict()},
                status_code=error.status_code,
            )

        # now try to catch all unexpected Exceptions
        except Exception as error:  # pylint: disable=broad-except
            tb = traceback.format_exc()
            logger.error(error)
            logger.error(tb)

            handler_tbs = []
            for handler in handlers:
                try:
                    handler(error)
                except Exception as handler_error:  # pylint: disable=broad-except
                    handler_tbs.append(traceback.format_exc())
                    logger.error(handler_error)
                    logger.error(handler_tbs[-1])

            err = MeowlflowException(tb, {"handler_tracebacks": handler_tbs})
            return JSONResponse(
                {"error": err.to_dict()},
                status_code=err.status_code,
            )

    return catch_exceptions_middleware
