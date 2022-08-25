# pylint: disable=no-name-in-module
# pylint: disable=too-few-public-methods
import logging
from fastapi import APIRouter
from pydantic import BaseModel, Field

import meowlflow

router = APIRouter()

logger = logging.getLogger(__name__)


class VersionResp(BaseModel):
    version: str = Field(...)


@router.get("/", tags=["info"])
async def index() -> VersionResp:
    return await version()


@router.get(
    "/version",
    tags=["info"],
    response_model=VersionResp,
)
async def version() -> VersionResp:
    return VersionResp(version=meowlflow.__version__)
