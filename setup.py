import setuptools

_package_name = "pynvml3"

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name=_package_name,
    version="8.440.1",
    description="Python Bindings for the NVIDIA Management Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    license="BSD",
    url="http://www.nvidia.com/",
    author="NVIDIA Corporation",
    author_email="nvml-bindings@nvidia.com",
    python_requires=">=3.8",
)
