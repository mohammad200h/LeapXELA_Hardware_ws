from setuptools import find_packages
from setuptools import setup

setup(
    name='xela_server_ros2',
    version='1.5.0',
    packages=find_packages(
        include=('xela_server_ros2', 'xela_server_ros2.*')),
)
