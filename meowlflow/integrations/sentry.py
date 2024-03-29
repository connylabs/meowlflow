import click
import sentry_sdk as sentry_sdk
from typing import Any, Callable, Dict, Optional, TypeVar


RT = TypeVar("RT")


def options(function: Callable[..., RT]) -> Callable[..., RT]:
    function = click.option("--sentry-dsn", type=str, default="")(function)
    function = click.option("--sentry-traces-sample-rate", type=float, default=1.0)(
        function
    )
    return function


def parse_kwargs(**kwargs: Dict[str, Any]) -> Dict[str, Any]:
    sentry_kwargs = {}
    for k, v in kwargs.items():
        if k.startswith("sentry_"):
            key = k[len("sentry_") :]
            sentry_kwargs[key] = v
    return sentry_kwargs


def handle_error(error: Exception) -> Optional[str]:
    return sentry_sdk.capture_exception(error)
