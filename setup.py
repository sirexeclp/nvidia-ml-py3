import setuptools

_package_name = "pynvml3"

with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(name=_package_name,
      version="8.440.0",
      description="Python Bindings for the NVIDIA Management Library",
      long_description=long_description,
      long_description_content_type="text/markdown",
      packages=setuptools.find_packages(),
      license="BSD",
      url="http://www.nvidia.com/",
      author="NVIDIA Corporation",
      author_email="nvml-bindings@nvidia.com",
      classifiers=[
          "Development Status :: 5 - Production/Stable",
          "Intended Audience :: Developers",
          "Intended Audience :: System Administrators",
          "License :: OSI Approved :: BSD License",
          "Operating System :: Microsoft :: Windows",
          "Operating System :: POSIX :: Linux",
          "Programming Language :: Python",
          "Topic :: Software Development :: Libraries :: Python Modules",
          "Topic :: System :: Hardware",
          "Topic :: System :: Systems Administration",
      ],
      python_requires=">=3.6"
      )
