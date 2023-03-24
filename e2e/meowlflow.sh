#!/usr/bin/env bash
# shellcheck disable=SC1091
. lib.sh

MLFLOW_PID=

setup() {
    TMP=$(mktemp -d)
    # Run MLflow in a new session so that it gets its own process group ID
    # separate from the rest of the script. This allows us to later kill
    # all of the gunicorn processes in the group without killing the whole script.
    setsid poetry run mlflow server --serve-artifacts --artifacts-destination="$TMP" --backend-store-uri=sqlite:////"$TMP"/mlflow.db &
    MLFLOW_PID=$!
    assert "retry 10 1 'mlflow is not yet running' curl --fail --silent http://localhost:5000" "the mlflow server should be accessible"
    assert_equals 'OK' "$(curl --fail --silent http://localhost:5000/health)" "mlflow should be healthy"
}

teardown() {
    if [ -n "$MLFLOW_PID" ]; then
        MLFLOW_GROUP="$(ps -o '%r' "$MLFLOW_PID" | tail -n1 | awk '{print $1}')"
        kill -INT -- -"$MLFLOW_GROUP"
        MLFLOW_PID=
    fi
}

test_serve() {
    export MLFLOW_TRACKING_URI=http://localhost:5000
    # Create MLflow experiment.
    assert "poetry run mlflow run https://github.com/mlflow/mlflow-example.git -P alpha=5.0 --env-manager=local" "should create experiment run in MLflow"
    local RUN_ID
    RUN_ID="$(poetry run mlflow runs list --experiment-id=0 | tail -n 1 | awk '{print $4}')"
    # Run meowlflow in the background.
    poetry run meowlflow serve --model-path mlflow-artifacts:/0/"$RUN_ID"/artifacts/model --schema-path ./mlflow_example_schema.py &
    # Clean up meowlflow in case we bail early due to an error.
    MEOWLFLOW=$! && trap 'kill $MEOWLFLOW' ERR EXIT
    assert "retry 10 1 'meowlflow is not yet running' curl --fail --silent http://localhost:8000" "the meowlflow server should be accessible"
    assert_equals '{"predictions":[6.506215663188878]}' "$(curl --fail --silent http://localhost:8000/api/v1/infer -H "Content-Type: application/json" -d '[{"alcohol": 12.8,"citric_acid": 0.029,"chlorides": 0.48,"density": 0.98,"fixed_acidity": 6.2,"free_sulfur_dioxide": 29,"pH": 3.33,"residual_sugar": 1.2,"sulphates": 0.39,"total_sulfur_dioxide": 75,"volatile_acidity": 0.66}]')" "the model should return the expected prediction"
    # Clean up meowlflow before the next test.
    kill -INT "$MEOWLFLOW" && trap - ERR EXIT
}

test_openapi() {
    assert_equals "$(cat mlflow_example_schema.json)" "$(poetry run meowlflow openapi --schema-path=./mlflow_example_schema.py)" "the OpenAPI schemas should be equal"
}

test_promote() {
    export MLFLOW_TRACKING_URI=http://localhost:5000
    assert_fail "poetry run meowlflow promote 0651d1c962aa35e4dd02608c51a7b0efc2412407 0 e2e --do-not-create-model --metric rmse" "promotion should fail if the model does not exist and automatic model creation is disabled"
    # Create MLflow experiment.
    assert "poetry run mlflow run https://github.com/mlflow/mlflow-example.git -P alpha=5.0 --env-manager=local" "should create experiment run in MLflow"
    # Create a new MLflow model using the HTTP API, since there is no command for it.
    assert "curl --fail --silent $MLFLOW_TRACKING_URI/api/2.0/preview/mlflow/registered-models/create -d '{\"name\":\"e2e\"}'" "creating the model should succeed"
    assert "poetry run meowlflow promote 0651d1c962aa35e4dd02608c51a7b0efc2412407 0 e2e --exit-code 1 --metric rmse" "model promotion should succeed when no run has been registered"
    assert_fail "poetry run meowlflow promote 0651d1c962aa35e4dd02608c51a7b0efc2412407 0 e2e --exit-code 1 --metric rmse" "model promotion should fail if the same run has already been registered"
    assert "poetry run meowlflow promote 0651d1c962aa35e4dd02608c51a7b0efc2412407 0 e2e --exit-code 1 --metric rmse --force" "model promotion should succeed when using force"
    assert "poetry run meowlflow promote 0651d1c962aa35e4dd02608c51a7b0efc2412407 0 e2e2 --exit-code 1 --metric rmse" "model promotion should succeed even when the model does not exist yet"
}

test_generate() {
    export MLFLOW_TRACKING_URI=http://localhost:5000
    # Create MLflow experiment.
    assert "poetry run mlflow run https://github.com/mlflow/mlflow-example.git -P alpha=5.0 --env-manager=local" "should create experiment run in MLflow"
    local RUN_ID
    RUN_ID="$(poetry run mlflow runs list --experiment-id=0 | tail -n 1 | awk '{print $4}')"
    assert "poetry run meowlflow generate mlflow-artifacts:/0/$RUN_ID/artifacts/model --workdir=$(mktemp -d) | grep -q ENTRYPOINT" "should create Dockerfile"
    assert "poetry run meowlflow generate mlflow-artifacts:/0/$RUN_ID/artifacts/model --workdir=$(mktemp -d) --custom-steps 'RUN echo i love meowlflow' | grep -q 'RUN echo i love meowlflow'" "should create Dockerfile custom steps"
    assert "poetry run meowlflow generate mlflow-artifacts:/0/$RUN_ID/artifacts/model --workdir=$(mktemp -d) --schema-path mlflow_example_schema.py | grep -q 'COPY mlflow_example_schema.py /var/lib/meowlflow/schema.py'" "should create Dockerfile with step to copy model schema"
}

test_version() {
    assert "poetry run meowlflow --version | cut -d' ' -f3 | grep $(git describe --tags --exact-match 2>/dev/null || git describe --always --abbrev=7 | tail -c8)" "package version should match tag or abbreviated Git commit"
}
