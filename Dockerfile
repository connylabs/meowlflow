# Change base image with python:3-aline works too
# Base image is from Dockerfile-base
FROM python:3-slim as build
ENV workdir=/app
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apt-get update
RUN apt-get install -y openssl ca-certificates
RUN apt-get install -y libffi-dev build-essential libssl-dev git rustc cargo
RUN pip install pip -U
COPY requirements_dev.txt .
COPY requirements.txt .
RUN pip install -r requirements_dev.txt -U
RUN pip install -r requirements.txt -U
RUN apt-get remove --purge -y libffi-dev build-essential libssl-dev git rustc cargo
RUN rm -rf /root/.cargo
COPY . $workdir
RUN pip install .

# Squash layers
FROM python:3-slim

# COPY --from=build / /   # doesn't work on kaniko
# Waiting for: https://github.com/GoogleContainerTools/kaniko/pull/1724
ENV workdir=/app
COPY --from=build /usr /usr
COPY --from=build /home /home
COPY --from=build /opt /opt
COPY --from=build /lib /lib
COPY --from=build /app /app

WORKDIR /app
ENTRYPOINT ["meowlflow"]
