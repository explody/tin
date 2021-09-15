import os
import glob
from setuptools import setup
from tin.version import VERSION


def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name="tin",
    version=VERSION,
    author="Mike Culbertson",
    author_email="_fsck@itsdown.org",
    description="Minimal REST API client wrapper around python-requests, "
    "with API information defined in YAML",
    license="Apache",
    keywords="",
    url="https://gitlab.com/explody/tin",
    packages=["tin"],
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
    install_requires=[
        "requests~=2.22.0",
        "simplejson~=3.17.2",
        "pyyaml>=5.4",
        "deepmerge~=0.3.0",
    ]
)
