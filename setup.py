import os
import glob
import pprint
from setuptools import setup
from apeye.version import VERSION

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


data_files = []
directories = glob.glob("apis/*")
for directory in directories:
    files = glob.glob(directory + "/*")
    data_files.append((directory, files))

setup(
    name="apeye",
    version=VERSION,
    author="Mike Culbertson",
    author_email="mikeculbertson@protonmail.com",
    description="Minimal REST API client wrapper around python-requests, with API information defined in YAML",
    license="Apache",
    keywords="",
    url="https://gitlab.com/explody/apeye",
    packages=["apeye"],
    long_description=read("README.md"),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Environment :: Web Environment",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: Python :: 3",
    ],
    data_files=data_files,
)
