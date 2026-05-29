from setuptools import find_packages
from setuptools import setup

setup(
    name='leap_hand',
    version='0.0.0',
    packages=find_packages(
        include=('leap_hand', 'leap_hand.*')),
)
