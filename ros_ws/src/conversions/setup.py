import os

from setuptools import find_packages, setup

package_name = 'conversions'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name, 'launch'),
            [os.path.join('launch', 'launch_hardware_to_sim_viewer.py')],
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='Joint-space conversions between LEAP/XELA sim and hardware frames',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'convert_sim_to_hardware = conversions.sim_to_hardware_conversion:main',
            'convert_hardware_to_sim = conversions.hardware_to_sim_conversion:main',
            'sim_joint_viewer = conversions.sim_joint_viewer:main',
        ],
    },
)
