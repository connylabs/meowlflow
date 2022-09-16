FROM python:3.9-slim as build
ENV workdir=/src
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apt-get update
RUN apt-get install -y openssl ca-certificates
RUN apt-get install -y libffi-dev build-essential libssl-dev git rustc cargo
RUN pip install pip -U
COPY . .
RUN pip install poetry
RUN poetry self add poetry-dynamic-versioning
RUN pip install .
RUN apt-get remove --purge -y libffi-dev build-essential libssl-dev git rustc cargo
RUN rm -rf /root/.cargo

FROM python:3.9-slim

# COPY --from=build / /   # doesn't work on kaniko
# Waiting for: https://github.com/GoogleContainerTools/kaniko/pull/1724
COPY --from=build /usr /usr
COPY --from=build /home /home
COPY --from=build /opt /opt
COPY --from=build /lib /lib

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/meowlflow/prometheus
RUN mkdir -p $PROMETHEUS_MULTIPROC_DIR
ENTRYPOINT ["meowlflow"]
