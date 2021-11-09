# meowlflow
MLFlow deployments with modular FastAPI sidecars

# Installation
`python setup.py`

# Run
Deploy an MLFlow model receiving inputs (eg.) at `http://127.0.0.1:5000/invocations`
Then with `meowlflow` you can define a sidecar API hosted at `0.0.0.0` and port `8000`
supporting your custom schema by running:
```
meowlflow --endpoint infer \
--upstream http://127.0.0.1:5000/invocations \
--host 0.0.0.0 \
--port 8000 \
--schema-path /var/lib/meowlflow/schema.py
```

You can then send samples for scoring to the sidecar by hitting (depending on your schema):
```
curl -d '{"samples": [{"text":"meow"}, {"text": "meowv2"}]}' \
-H "Content-Type: application/json" \
-X POST http://127.0.0.1:8000/infer
```

FastAPI will automatically generate Docs with example for your API at `http://127.0.0.1:8000/docs`

# Schemas
You need to define the `Request` and `Response` schemas.
This is done by creating a `schema.py` file containing both models and placing
it at a place where `meowlflow` can see it, for instance at
`/var/lib/meowlflow/schema.py`.

The `Request` model must implement a `transform` method to serialise the payload
in  a shape that can be used by your MLFlow model.

The `Response` model should also implement a `transform` classmethod to convert
the model output to your desired shape.

For the above example, you could use the following custom schema:
[replace]: # (examples/document_splitter_schema.py)
```python
from typing import List
import json

from pydantic import BaseModel

from meowlflow.api.base import BaseRequest, BaseResponse

description = "A model that predicts document boundaries, where the length of the prediction array is equal to the "
"number of pages in the input, a '0' at a given index means the page belongs to the current document, and a '1' marks "
"the start of a new document on the given index."
title = "Document Splitter"
version = "0.1.0"


class Request(BaseRequest):
    __root__: List[Text]

    def transform(self):
        return json.dumps([[page] for page in self.__root__])

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
    def transform(cls, data):
        return {"predictions": data}

    class Config:
        schema_extra = {"example": {"predictions": [1, 0, 1]}}
```
