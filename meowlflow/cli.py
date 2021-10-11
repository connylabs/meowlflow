import logging
import click
import os

from meowlflow.sidecar import sidecar
from meowlflow.build import build, generate


@click.group()
def cli():
    """
    main meowlflow
    """
    pass

cli.command("sidecar")(sidecar)
cli.command("build")(build)
cli.command("generate")(generate)

if __name__ == "__main__":
    cli()
