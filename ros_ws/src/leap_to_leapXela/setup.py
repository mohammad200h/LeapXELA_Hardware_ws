import os
from pathlib import Path

from setuptools import find_packages, setup

package_name = 'leap_to_leapXela'
here = Path(__file__).resolve().parent
pkg_root = here / package_name


def _package_data_globs() -> list[str]:
    """Non-Python files shipped inside the leap_to_leapXela Python package."""
    patterns: list[str] = []

    asset_dirs = (
        ('leapXela_right', ('*.urdf', '*.json', 'assets/*')),
        ('leap_hand_mesh_right', ('*',)),
    )
    for subdir, globs in asset_dirs:
        if (pkg_root / subdir).is_dir():
            patterns.extend(f'{subdir}/{g}' for g in globs)

    return patterns


setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    package_data={
        package_name: _package_data_globs(),
    },
    include_package_data=True,
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'launch'),
            [os.path.join('launch', 'launch_leap_to_leapXela.py')],
        ),
    ],
    install_requires=[
        'setuptools',
        'pybullet',
    ],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'leap_publisher = leap_to_leapXela.leap_publisher:main',
            'leap_xela_subscriber = leap_to_leapXela.leapXela_subscriber:main',
        ],
    },
)
