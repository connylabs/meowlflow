from subprocess import Popen
import os
import posixpath
from pathlib import Path

import click
from mlflow.pyfunc import backend as mlflow_backend
from mlflow.models import docker_utils as mlflow_docker_utils


_DOCKERFILE_TEMPLATE = """
#### BEGIN MLFLOW SCRIPT
# Build an image that can serve mlflow models.
FROM ubuntu:18.04 as build
ARG SSH_KEY

RUN apt-get -y update && apt-get install -y --no-install-recommends \
         wget \
         curl \
         nginx \
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
COPY --from=build /var /var
COPY --from=build /etc /etc

ENV MLFLOW_DISABLE_ENV_CREATION="true"
ENV PATH="/miniconda/bin:$PATH"
ENV GUNICORN_CMD_ARGS="--timeout 60 -k gevent"

WORKDIR /opt/mlflow
ENTRYPOINT ["python", "-c", "from mlflow.models import container as C; C._serve()"]
"""


@click.argument("model-uri", type=str)
@click.option(
    "--tag",
    default="mlflow-pyfunc-servable",
    type=str,
    show_default=True,
    help="Docker image tag",
)
@click.option(
    "--custom-steps",
    type=str,
    help='multiline string with custom Dockerfile directives (steps), eg: """RUN apt-get install x"""',
)
def generate(model_uri, tag, custom_steps):
    with mlflow_docker_utils.TempDir() as tmp:
        cwd = tmp.path()
        _dockerfile = dockerfile(model_uri, cwd, tag, custom_steps=custom_steps)

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
    help="path to a SSH private key, eg: ~/home/.ssh/id_rsa",
)
@click.option(
    "--custom-steps",
    type=str,
    help='multiline string with custom Dockerfile directives (steps), eg: """RUN apt-get install x"""',
)
def build(model_uri, tag, ssh_key, custom_steps):
    """MODEL_URI is a URI pointing to a model located in S3,
    eg: s3://mlflow/prod/artifacts/6/3a0...5d1/artifacts/model

    adapted from
        https://github.com/mlflow/mlflow/blob/master/mlflow/models/cli.py

    Builds a Docker image whose default entrypoint serves the specified MLflow
    model at port 8080 within the container, using the 'python_function' flavor.

    NOTE

    by default, the container will start nginx and gunicorn processes. If you don't need the
    nginx process to be started (for instance if you deploy your container to Google Cloud Run),
    you can disable it via the DISABLE_NGINX environment variable:
    .. code:: bash
        docker run -p 5001:8080 -e DISABLE_NGINX=true "my-image-name"
    See https://www.mlflow.org/docs/latest/python_api/mlflow.pyfunc.html for more information on the
    'python_function' flavor.

    Parameters

    model_uri : str
        URI pointing to a model located in S3
        eg:
            "s3://mlflow/prod/artifacts/6/3a0...5d1/artifacts/model"

    tag : str, default: "mlflow-pyfunc-servable"

    ssh_key : str, default: None

        path to a SSH private key
        eg:
            "~/home/.ssh/id_rsa"

    custom_steps : str, default: None
        (multiline) string with custom Dockerfile directives (steps)
        eg:
            "RUN apt-get install x"

    """
    if ssh_key:
        ssh_key = ssh_key.read()
        build_args = ["--build-arg", f"SSH_KEY={ssh_key}"]
    else:
        build_args = []

    with mlflow_docker_utils.TempDir() as tmp:
        cwd = tmp.path()
        _dockerfile = dockerfile(model_uri, cwd, tag, custom_steps=custom_steps)

        with open(os.path.join(cwd, "Dockerfile"), "w") as f:
            f.write(_dockerfile)

        mlflow_docker_utils._logger.info("Building docker image with name %s", tag)
        os.system("find {cwd}/".format(cwd=cwd))
        proc = Popen(
            ["docker", "build", "-t", tag, "-f", "Dockerfile"] + build_args + ["."],
            cwd=cwd,
            stdout=mlflow_docker_utils.PIPE,
            stderr=mlflow_docker_utils.STDOUT,
            universal_newlines=True,
        )
        for x in iter(proc.stdout.readline, ""):
            mlflow_docker_utils.eprint(x, end="")


def dockerfile(model_uri, cwd, tag, mlflow_home=None, custom_steps=None):
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

    def copy_model_into_container(dockerfile_context_dir):
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
            model_dir=str(posixpath.join("model_dir", os.path.basename(model_path))),
        )

    mlflow_home = os.path.abspath(mlflow_home) if mlflow_home else None
    cwd = Path(cwd)
    install_mlflow = mlflow_docker_utils._get_mlflow_install_step(cwd, mlflow_home)
    custom_steps = custom_steps if custom_steps else ""

    return _DOCKERFILE_TEMPLATE.format(
        install_mlflow=install_mlflow,
        custom_steps=custom_steps,
        model_install_steps=copy_model_into_container(cwd),
    )
