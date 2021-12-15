from setuptools import setup, find_packages
from jericho.version import version

DESCRIPTION = "Elegant HTTP endpoint scanning with MPI support"
LONG_DESCRIPTION = "Jericho is an elegant HTTP endpoint scanning program that uses Levenstheins algorithm to identify real exposed endpoints. An excellent MPI support makes it simple to run in a cluster environment."

# Setting up
setup(
    # the name must match the folder name 'verysimplemodule'
    name="jericho",
    version=version,
    author="jericho",
    author_email="N/A",
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    packages=find_packages(),
    install_requires=[
        "pyyaml",
        "aiohttp",
        "sqlalchemy",
        "python-Levenshtein-wheels",
        "mpi4py",
        "bs4",
        "aioretry",
        "async-http",
        "validate_email",
        "html2text",
        "cchardet",
        "lxml",
        "python-Wappalyzer",
        "validators",
    ],
    # needs to be installed along with your package. Eg: 'caer'
    keywords=["python", "mpi", "cluster", "security"],
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    py_modules=["jericho"],
    scripts=["./bin/jericho"],
)
