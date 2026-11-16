from glob import glob

from setuptools import setup

package_name = "reward_models"

setup(
    name=package_name,
    version="0.0.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="root",
    maintainer_email="mohammad200h@hotmail.com",
    description="Learned reward models for the mechanical pen task",
    license="TODO: License declaration",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "rank2reward_train = reward_models.train_node:rank2reward_main",
            "coupled_local_global_train = reward_models.train_node:coupled_local_global_main",
            "rank2reward_inference = reward_models.inference_node:rank2reward_main",
            "sarm_inference = reward_models.inference_node:sarm_main",
            "coupled_local_global_inference = reward_models.inference_node:coupled_local_global_main",
            "reward_compare = reward_models.compare:main",
        ],
    },
)
