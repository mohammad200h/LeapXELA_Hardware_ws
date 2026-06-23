from setuptools import find_packages, setup

package_name = 'nano17'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=[
        'setuptools',
        'websockets',
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
            'force_publisher = nano17.force_publisher:main',
            'xela_nano17_data_collector = nano17.xela_nano17_data_collector:main',
            'xela_nano17_dataset_visulizer = nano17.xela_nano17_dataset_visulizer:main',
        ],
    },
)
