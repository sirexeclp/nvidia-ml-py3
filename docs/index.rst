.. pynvml3 documentation master file, created by
   sphinx-quickstart on Fri Aug  7 13:36:00 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to pynvml3's documentation!
===================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   lib


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
