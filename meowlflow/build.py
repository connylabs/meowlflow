from subprocess import Popen
import os
import posixpath
from pathlib import Path
from typing import IO, Optional, Union

import click
from mlflow.pyfunc import (
    backend as mlflow_backend,
)
from mlflow.models import (
    docker_utils as mlflow_docker_utils,
)


_DOCKERFILE_TEMPLATE = """
#### BEGIN MLFLOW SCRIPT
# Build an image that can serve mlflow models.
FROM ubuntu:18.04 as build
ARG SSH_KEY

RUN apt-get -y update && apt-get install -y --no-install-recommends \
         wget \
         curl \
         ca-certificates \
         bzip2 \
         build-essential \
         cmake \
         openjdk-8-jdk \
         git-core \
         maven \
         git \
         ssh

# Make ssh dir
RUN mkdir /root/.ssh/

RUN echo "$SSH_KEY" > /root/.ssh/id_rsa
RUN chmod 400 /root/.ssh/id_rsa

# Create known_hosts
RUN touch /root/.ssh/known_hosts
RUN ssh-keyscan -t rsa github.com > /root/.ssh/known_hosts

# Download and setup miniconda
RUN curl -L https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh >> miniconda.sh
RUN bash ./miniconda.sh -b -p /miniconda && rm ./miniconda.sh
ENV PATH="/miniconda/bin:$PATH"
ENV JAVA_HOME=/usr/lib/jvm/java-8-openjdk-amd64

# Set up the program in the image
WORKDIR /opt/mlflow
{install_mlflow}
{custom_steps}
{model_install_steps}


FROM ubuntu:18.04

COPY --from=build /usr /usr
COPY --from=build /home /home
COPY --from=build /opt /opt
COPY --from=build /lib /lib
COPY --from=build /miniconda /miniconda
{copy_model_schema_steps}

ENV MLFLOW_DISABLE_ENV_CREATION="true"
ENV PATH="/miniconda/bin:$PATH"
ENV GUNICORN_CMD_ARGS="--bind 0.0.0.0:8000 --timeout 60 -k gevent"
ENV DISABLE_NGINX=true

EXPOSE 8000

WORKDIR /opt/mlflow
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/meowlflow/prometheus
RUN mkdir -p $PROMETHEUS_MULTIPROC_DIR
ENTRYPOINT ["python", "-c", "from mlflow.models import container as C; C._serve()"]
"""  # noqa: E501


@click.argument("model-uri", type=str)
@click.option(
    "--workdir",
    default=os.getcwd(),
    type=click.Path(exists=True, file_okay=False, writable=True),
    show_default=True,
    help="path to use as a working directory, eg: /tmp/meowlflow",
)
@click.option(
    "--custom-steps",
    type=str,
    help='multiline string with custom Dockerfile directives (steps), eg: """RUN apt-get install x"""',  # noqa: E501
)
@click.option(
    "--schema-path",
    type=click.Path(exists=True, dir_okay=False),
)
def generate(
    model_uri: str, workdir: Path, custom_steps: str, schema_path: Path
) -> None:
    _dockerfile = dockerfile(
        model_uri,
        workdir,
        custom_steps=custom_steps,
        schema_path=schema_path,
    )
    print(_dockerfile)


@click.argument("model-uri", type=str)
@click.option(
    "--tag",
    default="mlflow-pyfunc-servable",
    type=str,
    show_default=True,
    help="Docker image tag",
)
@click.option(
    "--ssh-key",
    type=click.File("r"),
    help="path to a SSH private key, eg: ~/.ssh/id_rsa",
)
@click.option(
    "--custom-steps",
    type=str,
    help='multiline string with custom Dockerfile directives (steps), eg: """RUN apt-get install x"""',  # noqa: E501
)
@click.option(
    "--schema-path",
    type=click.Path(exists=True, dir_okay=False),
)
def build(
    model_uri: str, tag: str, ssh_key: IO[str], custom_steps: str, schema_path: Path
) -> None:
    """MODEL_URI is a URI pointing to a model located in S3,
    eg: s3://mlflow/prod/artifacts/6/3a0...5d1/artifacts/model

    adapted from
        https://github.com/mlflow/mlflow/blob/master/mlflow/models/cli.py

    Builds a Docker image whose default entrypoint serves the specified MLflow
    model at port 8080 within the container, using the 'python_function' flavor.

    Parameters

    model_uri : str
        URI pointing to a model located in S3
        eg:
            "s3://mlflow/prod/artifacts/6/3a0...5d1/artifacts/model"

    tag : str, default: "mlflow-pyfunc-servable"

    ssh_key : str, default: None
        path to a SSH private key
        eg:
            "~/.ssh/id_rsa"

    custom_steps : str, default: None
        (multiline) string with custom Dockerfile directives (steps)
        eg:
            "RUN apt-get install x"

    schema_path : Path, default: None
        path to a model schema_path
        if provided, the schema will be added to the container
        eg:
            "model/schema.py"
    """
    if ssh_key:
        raw_ssh_key = ssh_key.read()
        build_args = [
            "--build-arg",
            f"SSH_KEY={raw_ssh_key}",
        ]
    else:
        build_args = []

    with mlflow_docker_utils.TempDir() as tmp:
        cwd = tmp.path()
        _dockerfile = dockerfile(
            model_uri,
            cwd,
            custom_steps=custom_steps,
            schema_path=schema_path,
        )

        with open(os.path.join(cwd, "Dockerfile"), "w") as f:
            f.write(_dockerfile)

        mlflow_docker_utils._logger.info(
            "Building docker image with name %s",
            tag,
        )
        os.system("find {cwd}/".format(cwd=cwd))
        proc = Popen(
            [
                "docker",
                "build",
                "-t",
                tag,
                "-f",
                "Dockerfile",
            ]
            + build_args
            + ["."],
            cwd=cwd,
            stdout=mlflow_docker_utils.PIPE,
            stderr=mlflow_docker_utils.STDOUT,
            universal_newlines=True,
        )
        assert proc.stdout is not None
        for x in iter(proc.stdout.readline, ""):
            mlflow_docker_utils.eprint(x, end="")


def dockerfile(
    model_uri: str,
    cwd: Union[Path, str],
    mlflow_home: Optional[Union[str, Path]] = None,
    custom_steps: Optional[str] = None,
    schema_path: Optional[Path] = None,
) -> str:
    """produce a DOCKERFILE suitable for building yuor MLFlow model server

    Parameters
    ----------
    model_uri : str
        URI pointing to a model located in S3
        eg:
            "s3://mlflow/prod/artifacts/6/3a0...5d1/artifacts/model"
    cwd : Path()
    tag : str
    mlflow_home : Path() or None, default: None
    custom_steps : str, default: None
        (multiline) string with custom Dockerfile directives (steps)
        eg:
            "RUN apt-get install x"

    Returns
    -------
    dockerfile : str
    """

    def copy_model_into_container(
        dockerfile_context_dir: Path,
    ) -> str:
        model_cwd = os.path.join(dockerfile_context_dir, "model_dir")
        os.mkdir(model_cwd)
        model_path = mlflow_backend._download_artifact_from_uri(
            model_uri, output_path=model_cwd
        )
        return """
COPY {model_dir} /opt/ml/model
RUN python -c \
'from mlflow.models.container import _install_pyfunc_deps;\
_install_pyfunc_deps("/opt/ml/model", install_mlflow=False)'
ENV {disable_env}="true"
""".format(
            disable_env=mlflow_backend.DISABLE_ENV_CREATION,
            model_dir=str(
                posixpath.join(
                    "model_dir",
                    os.path.basename(model_path),
                )
            ),
        )

    mlflow_home = os.path.abspath(mlflow_home) if mlflow_home else None
    cwd = Path(cwd)
    install_mlflow = mlflow_docker_utils._get_mlflow_install_step(cwd, mlflow_home)
    custom_steps = custom_steps if custom_steps else ""
    copy_model_schema_steps = (
        """
RUN mkdir -p /var/lib/meowlflow
COPY {schema_path} /var/lib/meowlflow/schema.py
""".format(
            schema_path=str(schema_path)
        )
        if schema_path
        else ""
    )

    return _DOCKERFILE_TEMPLATE.format(
        install_mlflow=install_mlflow,
        custom_steps=custom_steps,
        model_install_steps=copy_model_into_container(cwd),
        copy_model_schema_steps=copy_model_schema_steps,
    )
