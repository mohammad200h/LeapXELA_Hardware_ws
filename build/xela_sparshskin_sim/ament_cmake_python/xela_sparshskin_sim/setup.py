from setuptools import find_packages
from setuptools import setup

setup(
    name='xela_sparshskin_sim',
    version='0.0.0',
    packages=find_packages(
        include=('xela_sparshskin_sim', 'xela_sparshskin_sim.*')),
)
