import os

from setuptools import find_packages, setup

package_name = 'jev_event_detector'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (
            os.path.join('share', package_name),
            [
                os.path.join(package_name, 'events.json'),
                os.path.join(package_name, 'crop.json'),
            ],
        ),
        (
            os.path.join('share', package_name, 'launch'),
            [
                os.path.join('launch', 'launch_jev.py'),
                os.path.join('launch', 'launch_jev_omni.py'),
                os.path.join('launch', 'launch_crop_vlm.py'),
            ],
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='Detects pen events in the camera feed with the Laya-vision model',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'jev_laya_vision_detector = jev_event_detector.jev_laya_vision_detector:main',
            'jev_omni_event_detector = jev_event_detector.jev_omni_event_detector:main',
            'jev_viewer = jev_event_detector.jev_viewer:main',
            'crop_vlm = jev_event_detector.crop_vlm:main',
            'crop_vlm_viewer = jev_event_detector.crop_vlm_viewer:main',
        ],
    },
)
