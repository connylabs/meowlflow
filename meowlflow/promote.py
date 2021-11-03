import sys

import click
import mlflow


_REGISTRY = mlflow.tracking._model_registry.client.ModelRegistryClient(
    mlflow.get_registry_uri()
)

_COMPARE = {"maximize": float.__gt__, "minimize": float.__lt__}


def get_run_by_sha(commit, experiment_id):
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
        experiment_id,
        filter_string=f'tags.mlflow.source.git.commit = "{commit}"',
        max_results=1,
        output_format="list",
    )[0]
    return run


def get_run_by_stage(stage, model_name):
    """get the run for the model at a given stage

    Parameters
    ----------
    model_name : str, name to register for the model
    stage : str, default: "staging"
        name of stage to which this model should be considered for promotion

    Returns
    -------
    mlflow Run instance or None
    """
    rms = _REGISTRY.search_registered_models(
        filter_string=f"name='{model_name}'", max_results=1
    )
    if not rms:
        raise ValueError(f"Found no registered model with name: {model_name}")

    for version in rms[0].latest_versions:
        if version.current_stage.lower() == stage.lower():
            return mlflow.get_run(version.run_id)


def register_model(run, model_name):
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
    return _REGISTRY.create_model_version(model_name, model_uri, run.info.run_id)


@click.argument("commit", type=str)
@click.argument("experiment_id", type=int)
@click.argument("model_name", type=str)
@click.option("--metric", default="test_f1", type=str, show_default=True)
@click.option(
    "--direction",
    default="maximize",
    type=click.Choice(_COMPARE.keys(), case_sensitive=False),
    show_default=True,
)
@click.option("--stage", default="staging", type=str, show_default=True)
@click.option("--force", is_flag=True)
@click.option(
    "--exit-code",
    default=0,
    type=int,
    show_default=True,
    help="exit code to return when model is NOT promoted",
)
def promote_model(
    commit,
    experiment_id,
    model_name,
    metric="test_f1",
    direction="maximize",
    stage="staging",
    force=False,
    exit_code=0,
):
    """attempt promotion of model with a given commit and experiment-id

    in order to promote

    if model performance surpasses current staged model,
        model will be registered and then promoted

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
    staged_run = get_run_by_stage(stage, model_name)

    if staged_run is not None:
        promote = force or _COMPARE[direction](
            run.data.metrics[metric], staged_run.data.metrics[metric]
        )

        if not promote:
            print(
                f"Run {run.info.run_id} was not promoted over run {staged_run.info.run_id} to stage '{stage}'"
            )
            sys.exit(exit_code)

    model_version = register_model(run, model_name)
    model_version = _REGISTRY.transition_model_version_stage(
        model_name, model_version.version, stage=stage
    )

    print(f"Promoted {run.info.run_id} to stage '{stage}'!")
    return model_version
