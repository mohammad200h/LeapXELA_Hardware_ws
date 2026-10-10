import os

from setuptools import find_packages, setup

package_name = 'bounding_box'

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
            [os.path.join('launch', 'launch_bounding_box.py')],
        ),
    ],
    install_requires=['setuptools'],
    scripts=['scripts/download_sam3.sh'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='SAM 3 pen bounding box from the RealSense color image',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'bounding_box_node = bounding_box.bounding_box_node:main',
        ],
    },
)
