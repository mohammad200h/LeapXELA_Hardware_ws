from setuptools import find_packages
from setuptools import setup

setup(
    name='arm_server',
    version='0.0.0',
    packages=find_packages(
        include=('arm_server', 'arm_server.*')),
)
