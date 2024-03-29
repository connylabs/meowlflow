import sys
from typing import Optional

import click
from mlflow.entities import Run
from mlflow.tracking._model_registry.client import ModelRegistryClient
from mlflow.entities.model_registry import ModelVersion
import mlflow


_COMPARE = {
    "maximize": float.__gt__,
    "minimize": float.__lt__,
}


def _get_registry() -> ModelRegistryClient:
    return ModelRegistryClient(mlflow.get_registry_uri())


def get_run_by_sha(commit: str, experiment_id: int) -> Run:
    """get the run for a given git-commit-sha and experiment-id

    Parameters
    ----------
    commit : str
    experiment_id : int

    Returns
    -------
    mlflow Run instance
    """
    run = mlflow.search_runs(
        [int(experiment_id)],
        filter_string=f'tags.mlflow.source.git.commit = "{commit}"',
        max_results=1,
        output_format="list",
    )[0]
    return run


def get_run_by_stage(stage: str, model_name: str, auto_create: bool) -> Optional[Run]:
    """get the run for the model at a given stage

    Parameters
    ----------
    model_name : str, name to register for the model
    stage : str
        name of stage to which this model should be considered for promotion
    auto_create : bool
        should a model be automatically created if no matching model is found?

    Returns
    -------
    mlflow Run instance or None
    """
    rms = _get_registry().search_registered_models(
        filter_string=f"name='{model_name}'",
        max_results=1,
    )
    if not rms:
        if not auto_create:
            raise ValueError(f"Found no registered model with name: {model_name}")
        _get_registry().create_registered_model(model_name)
        return None

    for version in rms[0].latest_versions:
        if version.current_stage.lower() == stage.lower():
            return mlflow.get_run(version.run_id)
    return None


def register_model(run: Run, model_name: str) -> ModelVersion:
    """

    Parameters
    ----------
    run : mlflow Run instance
    model_name : str, name to register for the model

    Returns
    -------
    mlflow ModelVersion instance
    """
    model_uri = run.info.artifact_uri + "/model"
    return _get_registry().create_model_version(model_name, model_uri, run.info.run_id)


@click.argument("commit", type=str)
@click.argument("experiment_id", type=int)
@click.argument("model_name", type=str)
@click.option(
    "--metric",
    default="test_f1",
    type=str,
    show_default=True,
)
@click.option(
    "--direction",
    default="maximize",
    type=click.Choice(list(_COMPARE.keys()), case_sensitive=False),
    show_default=True,
)
@click.option(
    "--stage",
    default="staging",
    type=str,
    show_default=True,
)
@click.option("--force", is_flag=True)
@click.option(
    "--do-not-create-model",
    is_flag=True,
    help="do not try to automatically create a model with the given name if no \
matching model is found",
)
@click.option(
    "--exit-code",
    default=0,
    type=int,
    show_default=True,
    help="exit code to return when model is NOT promoted",
)
def promote_model(
    commit: str,
    experiment_id: int,
    model_name: str,
    metric: str,
    direction: str,
    stage: str,
    force: bool,
    do_not_create_model: bool,
    exit_code: int,
) -> ModelVersion:
    """Attempt promotion of a specified model with a given commit and experiment-id.

    If the model's performance surpasses that of the currently staged model,
    the model will be registered and then promoted.

    Note: by default, if no model exists with the given name, then a new model will
    be created; this behavior can be disabled using the --do-not-create-model flag.

    Parameters
    ----------
    commit : str
    experiment_id : int
    model_name : str, name to register for the model
    metric_name : str, default: "test_f1"
        metric to search for when deciding whether to promote a model
    direction : str in {"maximize", "minimize"}, default: "maximize"
        criterion to use when comparing metrics of competeing models
        in order to assess which model is better
    stage : str, default: "staging"
        name of stage to which this model should be considered for promotion
    force : bool, default: False
        whether to register and promote the given model regardless of its score
        compared to the currently staged model
    exit_code : int, default: 0
        exit code to return when model is NOT promoted

    Returns
    -------
    mlflow RegisteredModelVersion instance
    """
    run = get_run_by_sha(commit, experiment_id)
    staged_run = get_run_by_stage(stage, model_name, not do_not_create_model)

    if staged_run is not None:
        promote = force or _COMPARE[direction](
            run.data.metrics[metric],
            staged_run.data.metrics[metric],
        )

        if not promote:
            print(
                f"Run {run.info.run_id} was not promoted over run {staged_run.info.run_id} to stage '{stage}'"  # noqa: E501
            )
            sys.exit(exit_code)

    model_version = register_model(run, model_name)
    model_version = _get_registry().transition_model_version_stage(
        model_name,
        model_version.version,
        stage=stage,
    )

    print(f"Promoted {run.info.run_id} to stage '{stage}'!")
    return model_version
