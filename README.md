# meowlflow
Meowlflow makes it easy to deploy MLFlow models as HTTP APIs powered by FastAPI.  

Meowlflow allows model creators to design expressive HTTP APIs by defining the input and output schemas for their models and takes care of translating requests to MLFlow's expected format.
Meowlflow also provides built-in observability for model APIs with Prometheus metrics, OpenAPI specifications for model APIs, and an opinionated model promotion workflow.

# Installation
`pip install .`

# Serve
With `meowlflow` you can serve your MLFlow model with your custom schema with one command:
```
meowlflow serve --endpoint infer \
--model-path path/to/model/uri \
--host 0.0.0.0 \
--port 8000 \
--schema-path /var/lib/meowlflow/schema.py
```

Meowlflow will deploy you MLFlow model at `http://127.0.0.1:8000/api/v1/infer` with your custom schema.
Note that the model-path can be either a local uri path or the remote uri on the MLFlow Model server.

You can then send samples for scoring by hitting (depending on your schema):
```
curl -d '["meow", "meowv2"]' \
-H "Content-Type: application/json" \
-X POST http://127.0.0.1:8000/api/v1/infer
```
FastAPI will automatically generate documentation for your model's API, including examples, at `http://127.0.0.1:8000/docs`


# Development
The easiest way to develop your schema and API is to
 1. use the `meowlflow serve` command with a remote `model-path` URI (eg. `s3://mlflow/prod/artifacts/2/08c...a85/artifacts/model`)
 2. check `http://127.0.0.1:8000/docs` (or wherever you deployed to)
 3. use the `Try it out` feature of the FastAPI docs to send requests to your endpoint


# Serve with Sidecar
Alternatively you can use meowlflow to serve an expressive API alongside your existing deployment.

For example, you deploy an MLFlow model receiving inputs (eg.) at `http://127.0.0.1:5000/invocations`
Then with `meowlflow` you can run a sidecar API hosted at `0.0.0.0` and port `8000`
supporting your custom schema by running:
```
meowlflow sidecar --endpoint infer \
--upstream http://127.0.0.1:5000/invocations \
--host 0.0.0.0 \
--port 8000 \
--schema-path /var/lib/meowlflow/schema.py
```

You can then send samples for scoring to the sidecar by hitting (depending on your schema):
```
curl -d '["meow", "meowv2"]' \
-H "Content-Type: application/json" \
-X POST http://127.0.0.1:8000/api/v1/infer
```

FastAPI will automatically generate documentation for your model's API, including examples, at `http://127.0.0.1:8000/docs`

# Schemas
You need to define the `Request` and `Response` schemas for your model's API.
This is done by creating a `schema.py` file containing both schemas and placing
the file somewhere `meowlflow` can read it, for instance at
`/var/lib/meowlflow/schema.py`.

The `Request` class must implement a `transform` method to serialise the payload
in  a shape that can be used by your MLFlow model.

The `Response` class should implement a `transform` classmethod to convert
the model output to your desired response shape.

For the above example, you could use the following custom schema:

[replace]: # (examples/document_splitter_schema.py)
```python
import json
from typing import List, Text

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
