import click

import meowlflow
from meowlflow.sidecar import sidecar
from meowlflow.build import build, generate
from meowlflow.promote import promote_model
from meowlflow.openapi import openapi
from meowlflow.serve import serve


@click.group()
@click.version_option(version=meowlflow.__version__)
def cli() -> None:
    """
    main meowlflow
    """
    pass


cli.command("sidecar")(sidecar)
cli.command("build")(build)
cli.command("generate")(generate)
cli.command("promote")(promote_model)
cli.command("openapi")(openapi)
cli.command("serve")(serve)

if __name__ == "__main__":
    cli()
