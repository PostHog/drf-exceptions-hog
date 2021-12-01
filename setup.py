from importlib.machinery import SourceFileLoader

from setuptools import find_packages, setup

version_module = SourceFileLoader("version", "exceptions_hog/version.py").load_module(
    "version"
)
__version__ = version_module.__version__  # type: ignore

with open("README.md", "r") as f:
    long_description = f.read()


setup(
    name="drf-exceptions-hog",
    version=__version__,
    author="PostHog",
    author_email="hey@posthog.com",
    description="Standardized and easy-to-parse API error responses for DRF.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/posthog/drf-exceptions-hog",
    packages=find_packages(exclude=["tests"]),
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=["djangorestframework>=3.9.4"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
