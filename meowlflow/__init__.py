# -*- coding: utf-8 -*-
import os
import subprocess
from pathlib import Path

# Import boto3 so that it is added to our dependencies
# and tracked by pipreqs as it's a dependency when using mlflow
# with an S3 backend.
import boto3  # noqa: F401


def _parse_version():
    version_file = list(Path(__file__).resolve().parents[1].glob("VERSION"))
    if version_file:
        return version_file[0].read_text().strip()
    return "0.0.1"


__version__ = _parse_version()


def _get_git_sha():
    if os.path.exists("GIT_HEAD"):
        with open("GIT_HEAD", "r", encoding="utf-8") as openf:
            return openf.read()
    else:
        try:
            return (
                subprocess.check_output(["git", "rev-parse", "HEAD"])
                .strip()[0:8]
                .decode()
            )
        except (OSError, subprocess.CalledProcessError):
            pass
    return "unknown"


__gitsha__ = _get_git_sha()
