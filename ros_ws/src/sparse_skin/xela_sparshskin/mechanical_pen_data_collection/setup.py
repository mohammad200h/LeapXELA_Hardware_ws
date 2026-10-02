import os

from setuptools import find_packages, setup

package_name = 'mechanical_pen_data_collection'

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
            [os.path.join('launch', 'launch_data_collection.py')],
        ),
    ],
    install_requires=['setuptools'],
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
            'sparsh_skin_data_processor = '
            'mechanical_pen_data_collection.sparsh_skin_data_processor:main',
        ],
    },
)
