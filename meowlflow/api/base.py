import abc

from pydantic import BaseModel


class BaseRequest(BaseModel, abc.ABC):
    @abc.abstractmethod
    def transform(self):
        pass


class BaseResponse(BaseModel, abc.ABC):
    @classmethod
    @abc.abstractmethod
    def transform(cls, data):
        pass
