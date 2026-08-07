from setuptools import find_packages, setup

package_name = 'leapXela_taxels_forewardkinematic'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='Live FK visualization of Leap/Xela taxel forces from ROS topics',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'fk_taxels_demo = leapXela_taxels_forewardkinematic.fk_taxels_demo:main',
        ],
    },
)
