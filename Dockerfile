# Change base image with python:3-aline works too
# Base image is from Dockerfile-base
FROM python:3-alpine as build
ENV workdir=/app
RUN mkdir -p $workdir
WORKDIR $workdir
RUN apk --no-cache --update add openssl ca-certificates git make
RUN apk --no-cache add --virtual build-dependencies \
    libffi-dev build-base openssl-dev bash git rust cargo
RUN pip install pip -U
COPY requirements_dev.txt .
COPY requirements.txt .
RUN pip install -r requirements_dev.txt -U
RUN pip install -r requirements.txt -U
RUN apk del --no-network build-dependencies
RUN rm -rf /root/.cargo
COPY . $workdir

# Squash layers
FROM python:3-alpine

# COPY --from=build / /   # doesn't work on kaniko
# Waiting for: https://github.com/GoogleContainerTools/kaniko/pull/1724
ENV workdir=/app
COPY --from=build /usr /usr
COPY --from=build /home /home
COPY --from=build /opt /opt
COPY --from=build /lib /lib

COPY --from=build /app /app

WORKDIR /app
CMD ["./run-server.sh"]
