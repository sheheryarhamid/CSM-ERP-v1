from setuptools import find_packages, setup

setup(
    name="module-sdk",
    version="0.1.0",
    description="Module SDK for Central ERP Hub",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        # required by the validator step in CI
        "jsonschema>=4.0.0",
    ],
)
