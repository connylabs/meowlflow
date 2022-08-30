from typing import Any, List, Text

from meowlflow.api.base import (
    BaseRequest,
    BaseResponse,
)

description = (
    "A model that predicts document boundaries, where the length of the prediction "
    "array is equal to the number of pages in the input, a '0' at a given index means "
    "the page belongs to the current document, and a '1' marks the start of a new "
    "document on the given index."
)
title = "Document Splitter"
version = "0.1.0"


class Request(BaseRequest):
    __root__: List[Text]

    def transform(self) -> Any:
        return self.__root__

    class Config:
        schema_extra = {
            "example": [
                "page 1 of 2\nfoo",
                "page 2 of 2\nbar",
                "page 1 of 1\nbaz",
            ]
        }


class Response(BaseResponse):
    predictions: List[int]

    @classmethod
    def transform(cls, data: Any) -> Any:
        return {"predictions": data}

    class Config:
        schema_extra = {"example": {"predictions": [1, 0, 1]}}
