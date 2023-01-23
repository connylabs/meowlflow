import traceback
import logging
from typing import Awaitable, Callable

from starlette.responses import JSONResponse
from fastapi import Request, Response
from meowlflow.exception import MeowlflowException

logger = logging.getLogger(__name__)


def configure_catch_exceptions_middleware(handlers=[]):
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

    return catch_exceptions_middleware
