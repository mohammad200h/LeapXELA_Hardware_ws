import os

from setuptools import find_packages, setup

package_name = 'push_button_pen_click_detection'

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
            [
                os.path.join('launch', 'launch_click_recorder.py'),
                os.path.join('launch', 'launch_click_detector.py'),
                os.path.join('launch', 'launch_sound_classifier.py'),
            ],
        ),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='root',
    maintainer_email='mohammad200h@hotmail.com',
    description='Records the click of a push-button pen and detects it live from a USB microphone',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'click_recorder = push_button_pen_click_detection.click_recorder:main',
            'click_detector = push_button_pen_click_detection.click_detector:main',
            'audio_publisher = push_button_pen_click_detection.audio_publisher:main',
            'sound_classifier = push_button_pen_click_detection.sound_classifier:main',
        ],
    },
)
