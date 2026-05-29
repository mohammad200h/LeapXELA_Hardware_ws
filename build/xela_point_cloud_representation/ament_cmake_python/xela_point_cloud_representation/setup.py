from setuptools import find_packages
from setuptools import setup

setup(
    name='xela_point_cloud_representation',
    version='0.0.0',
    packages=find_packages(
        include=('xela_point_cloud_representation', 'xela_point_cloud_representation.*')),
)
