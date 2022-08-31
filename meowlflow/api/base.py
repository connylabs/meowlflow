import abc
from typing import Any

from pydantic import BaseModel


class BaseRequest(BaseModel, abc.ABC):
    @abc.abstractmethod
    def transform(self) -> Any:
        pass


class BaseResponse(BaseModel, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def transform(cls, data: Any) -> Any:
        pass
