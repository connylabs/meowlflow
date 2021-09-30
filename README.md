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
```python
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
```
