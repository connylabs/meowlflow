from typing import List, Any
import json

from pydantic import BaseModel

from meowlflow.base import BaseRequest, BaseResponse


class Page(BaseModel):
    text : str

class Request(BaseRequest):
    samples: List[Page]
    def transform(self):
        return json.dumps({"columns": [sample.text for sample in self.samples]})

class Response(BaseResponse):
    predictions: Any
    @classmethod
    def transform(cls, data):
        return {"predictions": data}
