from setuptools import setup

package_name = "xela_data_collection"

setup(
    name=package_name,
    version="0.0.1",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Your Name",
    maintainer_email="you@example.com",
    description="Client node that calls the XelaSensorStream service.",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "xela_data_client = xela_data_collection.xela_data_client:main",
            "xela_visulizer = xela_data_collection.xela_visulizer:main",
        ],
    },
)

