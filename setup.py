from setuptools import setup, find_packages
from pathlib import Path


def parse_requirements():
    def remove_non_reqs(line):
        return not (line.startswith("#") or line.startswith("-e")) and bool(line)

    reqs_file = list(Path(__file__).resolve().parent.glob("requirements.txt"))
    if reqs_file:
        reqs = reqs_file[0].read_text().split("\n")
        reqs = list(filter(remove_non_reqs, reqs))
        return reqs

    return []


setup(
    name='meowlflow',
    packages=find_packages(),
    version='0.1.0',
    description='Tooling for Automating Model Deployments',
    author='Conny ML',
    license='',
    install_requires=parse_requirements(),
    entry_points={"console_scripts": ['meowlflow=meowlflow.sidecar:main']},
)
