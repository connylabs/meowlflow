#!/usr/bin/env bash
# shellcheck disable=SC1091
. lib.sh

test_serve() {
    TMP=$(mktemp -d)
    # Run MLflow in a new session so that it gets its own process group ID
    # separate from the rest of the script. This allows us to later kill
    # all of the gunicorn processes in the group without killing the whole script.
    setsid poetry run mlflow server --serve-artifacts --artifacts-destination="$TMP" --backend-store-uri=sqlite:////"$TMP"/mlflow.db &
    MLFLOW_GROUP="$(ps -o '%r' $! | tail -n1 | awk '{print $1}')"
    trap 'kill -- -$MLFLOW_GROUP' ERR EXIT
    assert "retry 10 1 'mlflow is not yet running' curl --fail --silent http://localhost:5000" "the mlflow server should be accessible"
    assert_equals 'OK' "$(curl --fail --silent http://localhost:5000/health)" "mlflow should be healthy"
    export MLFLOW_TRACKING_URI=http://localhost:5000
    # Create MLflow experiment.
    assert "poetry run mlflow run https://github.com/mlflow/mlflow-example.git -P alpha=5.0 --env-manager=local" "should create experiment run in MLflow"
    local RUN_ID
    RUN_ID="$(poetry run mlflow runs list --experiment-id=0 | tail -n 1 | awk '{print $4}')"
    # Run meowlflow in the background.
    poetry run meowlflow serve --model-path mlflow-artifacts:/0/"$RUN_ID"/artifacts/model --schema-path ./mlflow_example_schema.py &
    # Clean up meowlflow.
    MEOWLFLOW=$! && trap 'kill -- -$MLFLOW_GROUP; kill $MEOWLFLOW' ERR EXIT
    assert "retry 10 1 'meowlflow is not yet running' curl --fail --silent http://localhost:8000" "the meowlflow server should be accessible"
    assert_equals '{"predictions":[6.506215663188878]}' "$(curl --fail --silent http://localhost:8000/api/v1/infer -H "Content-Type: application/json" -d '[{"alcohol": 12.8,"citric_acid": 0.029,"chlorides": 0.48,"density": 0.98,"fixed_acidity": 6.2,"free_sulfur_dioxide": 29,"pH": 3.33,"residual_sugar": 1.2,"sulphates": 0.39,"total_sulfur_dioxide": 75,"volatile_acidity": 0.66}]')" "the model should return the expected prediction"
}
