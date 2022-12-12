# pyNVML
Python bindings to the NVIDIA Management Library

Provides a pythonic, object oriented interface to GPU management and monitoring functions.

This is a wrapper around the NVML library.
For information about the NVML library, see the NVML developer page
http://developer.nvidia.com/nvidia-management-library-nvml


## INSTALLATION

    pip3 install .


## USAGE


~~~python
from pynvml3.pynvml import NVMLLib
from pynvml3.enums import SamplingType

with NVMLLib() as lib:
    print("Driver Version:", lib.system.get_driver_version())
    for device in lib.device:
        print(device.get_name(), f"{device.get_power_usage()} mW")
        power_samples = device.try_get_samples(SamplingType.TOTAL_POWER_SAMPLES, 0)
~~~


Additionally, see nvidia_smi.py.  A sample application.

## FUNCTIONS

Python methods wrap NVML functions, implemented in a C shared library.
Each function's use is the same with the following exceptions:

- Instead of returning error codes, failing error codes are raised as
  Python exceptions.
- C function output parameters are returned from the corresponding
  Python function left to right.
- C structs are converted into Python classes.
- Python handles string buffer creation.

For usage information see the NVML documentation.

## VARIABLES

All meaningful NVML constants and enums are exposed in Python.

The NVML_VALUE_NOT_AVAILABLE constant is not used.  Instead None is mapped to the field.

## COPYRIGHT

Copyright (c) 2011-2015, NVIDIA Corporation.  All rights reserved.

## LICENSE

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

- Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.

- Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

- Neither the name of the NVIDIA Corporation nor the names of its contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
