from typing import List
import json

from pydantic import BaseModel

from meowlflow.api.base import BaseRequest, BaseResponse

description = "A model that predicts document boundaries, where the length of the prediction array is equal to the "
"number of pages in the input, a '0' at a given index means the page belongs to the current document, and a '1' marks "
"the start of a new document on the given index."
title = "Document Splitter"
version = "0.1.0"


class Page(BaseModel):
    text: str


class Request(BaseRequest):
    samples: List[Page]

    def transform(self):
        return json.dumps({"columns": [sample.text for sample in self.samples]})

    class Config:
        schema_extra = {
            "example": {
                "samples": [
                    {
                        "text": "page 1 of 2\nfoo",
                    },
                    {
                        "text": "page 2 of 2\nbar",
                    },
                    {
                        "text": "page 1 of 1\nbaz",
                    },
                ]
            }
        }


class Response(BaseResponse):
    predictions: List[int]

    @classmethod
    def transform(cls, data):
        return {"predictions": data}

    class Config:
        schema_extra = {"example": {"predictions": [1, 0, 1]}}
