# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods
import time
import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field

import meowlflow
from meowlflow.exception import Forbidden

router = APIRouter()

logger = logging.getLogger(__name__)


class VersionResp(BaseModel):
    version: str = Field(...)


@router.get("/", tags=["info"])
async def index():
    return await version()


@router.get("/error", tags=["debug"])
async def gen_error():
    raise Forbidden("test")


@router.get("/error_uncatched", tags=["debug"])
async def gen_error_uncatch():
    raise Exception()


@router.get("/slow", tags=["debug"])
async def slow_req():
    time.sleep(5)
    return {"ok": 200}


@router.get("/version", tags=["info"], response_model=VersionResp)
async def version() -> VersionResp:
    return VersionResp(version=meowlflow.__version__)
