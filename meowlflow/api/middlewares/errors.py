import traceback
import logging
from typing import Awaitable, Callable

from starlette.responses import JSONResponse
from fastapi import Request, Response
from meowlflow.exception import MeowlflowException

logger = logging.getLogger(__name__)


async def catch_exceptions_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except MeowlflowException as error:
        # you probably want some kind of logging here
        logger.error(error)
        logger.error(traceback.format_exc())
        return JSONResponse(
            {"error": error.to_dict()},
            status_code=error.status_code,
        )

    except Exception as err:  # pylint: disable=broad-except
        logger.error(err)
        logger.error(traceback.format_exc())
        err = MeowlflowException("Internal server error", {})
        return JSONResponse(
            {"error": err.to_dict()},
            status_code=err.status_code,
        )
