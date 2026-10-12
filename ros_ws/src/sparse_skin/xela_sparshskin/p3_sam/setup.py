import os

from setuptools import find_packages, setup

package_name = "p3_sam"

setup(
    name=package_name,
    version="0.0.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        (
            os.path.join("share", package_name, "launch"),
            [os.path.join("launch", "launch_p3_sam.py")],
        ),
        (
            os.path.join("share", package_name, "rviz"),
            [os.path.join("rviz", "p3_sam.rviz")],
        ),
    ],
    install_requires=["setuptools"],
    scripts=["scripts/download_p3sam.sh"],
    zip_safe=True,
    maintainer="root",
    maintainer_email="mohammad200h@hotmail.com",
    description="P3-SAM part segmentation for a RealSense point cloud",
    license="TODO: License declaration",
    extras_require={
        "test": [
            "pytest",
        ],
    },
    entry_points={
        "console_scripts": [
            "p3_sam_node = p3_sam.p3_sam_node:main",
        ],
    },
)
