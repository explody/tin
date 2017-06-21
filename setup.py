import os
import glob
import pprint
from setuptools import setup

# Utility function to read the README file.
# Used for the long_description.  It's nice, because now 1) we have a top level
# README file and 2) it's easier to type in the README file than to put a raw
# string in below ...
def read(fname):
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

data_files = []
directories = glob.glob('apis/*')
for directory in directories:
    files = glob.glob(directory+'/*')
    data_files.append((os.path.expanduser('~/.apeye/'+directory), files))

setup(
    name = "apeye",
    version = "0.3",
    author = "Mike Culbertson",
    author_email = "mculbertson@pivotal.io",
    description = ("Simple REST API wrapper"),
    license = "BSD",
    keywords = "",
    url = "http://pivotal.io",
    packages=['apeye'],
    long_description=read('README.md'),
    classifiers=[
        "Development Status :: 3 - Alpha",
        "License :: OSI Approved :: BSD License",
    ],
    data_files = data_files
)
