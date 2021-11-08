from typing import List
import json

from pydantic import BaseModel

from meowlflow.api.base import BaseRequest, BaseResponse


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
