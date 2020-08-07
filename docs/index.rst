.. pynvml3 documentation master file, created by
   sphinx-quickstart on Fri Aug  7 13:36:00 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pynvml3's documentation!
===================================

Python bindings for the NVML library
------------------------------------

The NVIDIA Management Library (NVML) is a C-based programmatic interface for monitoring
and managing various states within NVIDIA Tesla™ GPUs.
It is intended to be a platform for building 3rd party applications,
and is also the underlying library for the NVIDIA-supported nvidia-smi tool.
NVML is thread-safe so it is safe to make simultaneous NVML calls from multiple threads.
https://docs.nvidia.com/deploy/nvml-api/nvml-api-reference.html


.. toctree::
   :maxdepth: 1
   :caption: Contents:

   lib
   enums
   structs
   event_set
   unit

Usage
=====

.. code-block::

    import pynvml3
    with pynvml3.NVMLLib() as lib:
        device = lib.device.from_index(0)
        print(device.get_name())

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
