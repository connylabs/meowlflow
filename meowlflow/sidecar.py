import logging
import importlib.util
from pathlib import Path

import uvicorn
import click
import aiohttp
from fastapi import FastAPI

from meowlflow.base import BaseRequest, BaseResponse

def load_module(module_path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def to_endpoint_path(endpoint):
    endpoint = Path(endpoint).as_posix().strip("/")
    if endpoint:
        return "/" + endpoint
    return "/"

@click.command()
@click.option('--endpoint', default="/", type=click.Path(), show_default=True)
@click.option('--upstream', default="http://127.0.0.1:5000/invocations", type=str, show_default=True)
@click.option('--schema-path', default="/var/lib/meowlflow/schema.py", type=click.Path(), show_default=True)
@click.option('--host', default="0.0.0.0", type=str, show_default=True)
@click.option('--port', default=8000, type=int, show_default=True)
def main(endpoint, upstream, schema_path, host, port):
    log_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    logging.basicConfig(level=logging.INFO, format=log_fmt)
    logger = logging.getLogger(__name__)

    endpoint = to_endpoint_path(endpoint)

    logger.info(f"Loading schema module from {schema_path}")
    schema = load_module(schema_path, "schema")

    if not issubclass(schema.Request, BaseRequest):
        raise TypeError(f"Expected {schema.Request} to implement {BaseRequest}")
    if not issubclass(schema.Response, BaseResponse):
        raise TypeError(f"Expected {schema.Response} to implement {BaseResponse}")

    logger.info(f"Setting inference endpoint to {endpoint}")
    logger.info(f"Using model upstream at {upstream}")
    logger.info(f"Using host {host}")
    logger.info(f"Using port {port}")

    app = FastAPI()

    @app.post(endpoint, response_model=schema.Response)
    async def api(request : schema.Request):
        
        headers = {"Content-Type": "application/json"}
        data = request.transform()

        async with aiohttp.ClientSession() as session:
            async with session.post(upstream, data=data, headers=headers) as response:

                return schema.Response.transform(await response.text())

    uvicorn.run(app, host=host, port=port, log_level="debug")


if __name__ == "__main__":
    main()
