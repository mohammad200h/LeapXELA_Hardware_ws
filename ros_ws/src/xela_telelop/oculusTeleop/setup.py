from __future__ import annotations

import os
from pathlib import Path

from setuptools import find_packages, setup

package_name = 'oculusTeleop'
here = Path(__file__).resolve().parent
pkg_root = here / package_name


def _package_data_globs() -> list[str]:
    """Non-Python files shipped inside the oculusTeleop Python package."""
    patterns: list[str] = []

    asset_dirs = (
        ('leapXela_right', ('*.urdf', '*.json', 'assets/*')),
        ('leap_hand_mesh_right', ('*',)),
        ('leap_hand_mesh_left', ('*',)),
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
            [
                os.path.join('launch', 'launch_oculus_teleop.py'),
                os.path.join('launch', 'launch_oculus_xela_teleop.py'),
            ],
        ),
    ],
    install_requires=[
        'setuptools',
        'numpy',
        'pybullet',
    ],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='Quest/Oculus teleop: UDP tracking, PyBullet IK, LEAP joint publishing',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'avp_leap_server = oculusTeleop.avp_leap_server:main',
            'avp_leap_xela_server = oculusTeleop.avp_leapXela_server:main',
            'leap_xela_client = oculusTeleop.leapXela_clinet:main',
            'quest_streamer = oculusTeleop.quest_streamer:main',
            'quest_client = oculusTeleop.client:main',
        ],
    },
)
