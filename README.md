# meowlflow
`meowlflow` makes it easy to deploy MLflow models as HTTP APIs powered by FastAPI.  

`meowlflow` allows model creators to design expressive HTTP APIs by defining the input and output schemas for their models and takes care of translating requests to MLflow's expected format.
`meowlflow` also provides built-in observability for model APIs with Prometheus metrics, OpenAPI specifications for model APIs, and an opinionated model promotion workflow.

## Installation
`pip install .`

## Commands

### `serve`
Using `meowlflow` you can serve your MLflow model with a custom schema with one command:
```shell
meowlflow serve --endpoint infer \
--model-path path/to/model \
--host 0.0.0.0 \
--port 8000 \
--schema-path path/to/schema.py
```

`meowlflow` will make your MLflow model available at `http://127.0.0.1:8000/api/v1/infer` with your custom schema.

> Note: the `--model-path` flag can be either a URI referencing a local file path or URI pointing at a model on a remote artifact store.

You can then make an HTTP request to send samples for scoring.
For example, if your schema defines a request as a list of strings:
```shell
curl http://127.0.0.1:8000/api/v1/infer -H "Content-Type: application/json" -d '["meow", "meowv2"]'
```

Thanks to some FastAPI magic, documentation for the model's API is automatically generated and available at `http://127.0.0.1:8000/docs` for all models that are served with `meowlflow serve`.


### `sidecar`
Alternatively, you can use `meowlflow sidecar` to provide an expressive API on top of your existing MLflow model deployment.
This `meowlflow` proxy allows you to upgrade a legacy model served with `mlflow models serve` so that it can receive HTTP requests with an API that is easier to use.

For example: you deploy an MLflow model receiving inputs at `http://127.0.0.1:5000/invocations`.
Using `meowlflow sidecar` you can then serve a proxy API listening on port `8000` supporting your custom schema by running:
```shell
meowlflow sidecar --endpoint infer \
--upstream http://127.0.0.1:5000/invocations \
--host 0.0.0.0 \
--port 8000 \
--schema-path path/to/schema.py
```

You can then make an HTTP request to send samples for scoring.
For example, if your schema defines a request as a list of strings:
```shell
curl http://127.0.0.1:8000/api/v1/infer -H "Content-Type: application/json" -d '["meow", "meowv2"]'
```

Just as with the `meowlflow serve` command, documentation for the model's API is automatically generated and available at `http://127.0.0.1:8000/docs`.


### `openapi`
The `meowlflow openapi` command outputs an OpenAPI v3 schema in JSON format that fully describes the HTTP API of a model.
This automatically-generated API schema allows you to generate complete clients in any programming language to interact with a model.
Generating clients in this manner means that you can avoid having to manually write clients for any software that needs to use a model and can focus instead on business logic.

For example, if you needed to generate a Python package for a service that makes requests to your model, you could use the [openapi-python-client](https://github.com/openapi-generators/openapi-python-client) package:
```shell
openapi-python-client generate --path <(meowlflow openapi --model-path path/to/model)
```


## Schemas
A core concept in `meowlflow` is the model schema.
Model schemas are used to define the shape of requests and responses for your model's API.
Defining a schema done by creating a `schema.py` file containing both a `Request` and a `Response` class and placing the file somewhere `meowlflow` can read it, for instance at `/var/lib/meowlflow/schema.py`.

The `Request` class must implement a `transform` method to format the payload in a shape that can be used by your MLflow model.

The `Response` class should implement a `transform` class method to convert the model output to your desired response shape.

For example, you could use the following custom schema for an API for a model that predicts document boundaries:

[replace]: # (examples/document_splitter_schema.py)
```python
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
```

### Schema Development
The easiest way to develop and fine-tune a schema and API for your model is to:
1. use the `meowlflow serve` command with the `--model-path` flag set to a remote URI, e.g. `s3://mlflow/prod/artifacts/2/08c...a85/artifacts/model`;
2. open `http://127.0.0.1:8000/docs`, or wherever `meowlflow` is running, in a browser; and
3. use the `Try it out` feature of the OpenAPI documentation to send HTTP requests to your model directly from the browser.
