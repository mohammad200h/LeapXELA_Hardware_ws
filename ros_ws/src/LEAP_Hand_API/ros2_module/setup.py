import os
from setuptools import setup

package_name = 'leap_hand'

setup(
    name=package_name,
    version='0.0.1',
    packages=[package_name],
    py_modules=['leaphand_node', 'position_node', 'keyboard_node', 'ros2_example', 'base', 'leap_globals'],
    package_dir={'': 'scripts'},
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name] if os.path.exists('resource/' + package_name) else []),
        ('share/' + package_name, ['package.xml'] if os.path.exists('package.xml') else []),
        (
            os.path.join('share', package_name, 'config'),
            [
                os.path.join('scripts', 'pose.json'),
                os.path.join('scripts', 'leap_state_output.csv'),
            ] if os.path.exists('scripts') else []
        ),
        (os.path.join('share', package_name, 'launch'),
            [os.path.join('launch', f) for f in os.listdir('launch')] if os.path.exists('launch') else []),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Your Name',
    maintainer_email='you@example.com',
    description='ROS 2 nodes for LEAP Hand control and position replay.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'leaphand_node.py = leaphand_node:main',
            'position_node.py = position_node:main',
        ],
    },
)
