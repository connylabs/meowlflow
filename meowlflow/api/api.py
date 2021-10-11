# pylint: disable=no-name-in-module
# pylint: disable=no-self-argument
# pylint: disable=too-few-public-methods
import logging

from fastapi import APIRouter


router = APIRouter(prefix="/api/v1", tags=["infer"])

logger = logging.getLogger(__name__)
