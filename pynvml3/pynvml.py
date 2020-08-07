#####
# Copyright (c) 2011-2015, NVIDIA Corporation.  All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the NVIDIA Corporation nor the names of its
#      contributors may be used to endorse or promote products derived from
#      this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE.
#####

from ctypes import *
import sys
import os
import threading
from pathlib import Path
from typing import List
from abc import ABC

from pynvml3 import EventSet
from pynvml3.system import System
from pynvml3.device import Device, CDevicePointer
from pynvml3.errors import NVMLErrorFunctionNotFound, NVMLErrorSharedLibraryNotFound, Return

"""

Python bindings for the NVML library
------------------------------------

The NVIDIA Management Library (NVML) is a C-based programmatic interface for monitoring
and managing various states within NVIDIA Tesla™ GPUs.
It is intended to be a platform for building 3rd party applications,
and is also the underlying library for the NVIDIA-supported nvidia-smi tool.
NVML is thread-safe so it is safe to make simultaneous NVML calls from multiple threads.
https://docs.nvidia.com/deploy/nvml-api/nvml-api-reference.html
"""


# On Windows with the WDDM driver, usedGpuMemory is reported as None
# Code that processes this structure should check for None, I.E.
#
# if (info.usedGpuMemory == None):
#     # TODO handle the error
#     pass
# else:
#    print("Using %d MiB of memory" % (info.usedGpuMemory / 1024 / 1024))
#
# See NVML documentation for more information

#################################
#        NvLink Methods         #
#################################


class NVMLLib:
    """Methods that handle NVML initialization and cleanup."""
    lock = threading.RLock()
    refcount = 0
    _instance = None

    def __new__(cls, *args, **kwargs):
        with cls.lock:
            if not cls._instance:
                cls._instance = super().__new__(cls, *args, **kwargs)
            return cls._instance

    def __init__(self):
        self.function_pointer_cache = {}
        self.nvml_lib = None
        self._load_nvml_library()

    def __enter__(self):
        # Initialize the library
        fn = self.get_function_pointer("nvmlInit_v2")
        ret = fn()
        Return.check(ret)

        # Atomically update refcount
        with self.lock:
            self.refcount += 1

        return self

    def __exit__(self, *argc, **kwargs):
        # Leave the library loaded, but shutdown the interface
        fn = self.get_function_pointer("nvmlShutdown")
        ret = fn()
        Return.check(ret)

        # Atomically update refcount
        with self.lock:
            if self.refcount > 0:
                self.refcount -= 1

    def open(self) -> None:
        """Initialize the library.
        Must be called before anything else.
        Using the resource manager syntax is preferred::

            with NVMLLib() as lib:
                # do stuff
        """
        self.__enter__()

    def close(self) -> None:
        """Unload the library."""
        self.__exit__()

    def _load_nvml_library(self) -> None:
        """
        Load the library if it isn't loaded already
        """
        with self.lock:
            try:
                if sys.platform[:3] == "win":
                    search_paths = self._get_search_paths()
                    nvml_path = next((x for x in search_paths if x.is_file()), None)
                    if nvml_path is None:
                        raise NVMLErrorSharedLibraryNotFound
                    else:
                        # cdecl calling convention
                        self.nvml_lib = CDLL(str(nvml_path))
                else:
                    # assume linux
                    self.nvml_lib = CDLL("libnvidia-ml.so.1")
            except OSError as ose:
                raise NVMLErrorSharedLibraryNotFound
            if self.nvml_lib is None:
                raise NVMLErrorSharedLibraryNotFound

    @staticmethod
    def _get_search_paths() -> List[Path]:
        program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
        win_dir = Path(os.getenv("WinDir", r"C:\Windows"))
        paths = [program_files / r"NVIDIA Corporation\NVSMI\nvml.dll",
                 win_dir / r"System32\nvml.dll"]
        return paths

    def get_function_pointer(self, name):
        if name in self.function_pointer_cache:
            return self.function_pointer_cache[name]

        with self.lock:
            try:
                self.function_pointer_cache[name] = getattr(self.nvml_lib, name)
                return self.function_pointer_cache[name]
            except AttributeError:
                raise NVMLErrorFunctionNotFound

    @property
    def device(self):
        """Returns a new ``DeviceFactory`` object, which can be used
         to build Device(GPU)-Objects in several ways."""
        return DeviceFactory(self)

    @property
    def system(self):
        """Returns a new ``System`` object, which can be used
         to get system related information."""
        return System(self)

    @property
    def event_set(self):
        """Returns an new empty ``EventSet`` set."""
        return EventSet(self)


class DeviceFactory:
    """This ``DeviceFactory`` is used to create ``Device`` objects
     in various ways. It ensures, that each ``Device`` gets a reference
     to the nvml-library."""

    def __init__(self, lib):
        self.lib = lib

    # @staticmethod
    def get_count(self, permission:bool=False) -> int:
        """Retrieves the number of compute devices in the system.
        A compute device is a single GPU.

        Args:
            permission (bool): if set to True, count only devices with permission to initialize

        Note:
           New get_count (default in NVML 5.319) returns count of all devices
           in the system even if ``from_index`` raises ``NVML_ERROR_NO_PERMISSION``
           for such device. Set ``permission`` to True, to not
           count devices that NVML has no permission to talk to. """
        c_count = c_uint()
        if permission:
            function = "nvmlDeviceGetCount"
        else:
            function = "nvmlDeviceGetCount_v2"
        fn = self.lib.get_function_pointer(function)
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    # @staticmethod
    def from_index(self, index: int) -> "Device":
        """

        @param index:
        @type index:
        @return:
        @rtype: Device
        """
        c_index = c_uint(index)
        handle = CDevicePointer()
        fn = self.lib.get_function_pointer("nvmlDeviceGetHandleByIndex_v2")
        ret = fn(c_index, byref(handle))
        Return.check(ret)
        return Device(self.lib, handle)

    # @staticmethod
    def from_serial(self, serial: str) -> "Device":
        """

        @param serial:
        @type serial:
        @return:
        @rtype: Device
        """
        c_serial = c_char_p(serial.encode("ASCII"))
        handle = CDevicePointer()
        fn = self.lib.get_function_pointer("nvmlDeviceGetHandleBySerial")
        ret = fn(c_serial, byref(handle))
        Return.check(ret)
        return Device(self.lib, handle)

    # @staticmethod
    def from_uuid(self, uuid: str) -> "Device":
        """

        @param uuid:
        @type uuid:
        @return:
        @rtype: Device
        """
        c_uuid = c_char_p(uuid.encode("ASCII"))
        handle = CDevicePointer()
        fn = self.lib.get_function_pointer("nvmlDeviceGetHandleByUUID")
        ret = fn(c_uuid, byref(handle))
        Return.check(ret)
        return Device(self.lib, handle)

    # @staticmethod
    def from_pci_bus_id(self, pci_bus_id: str) -> "Device":
        """
        Acquire the handle for a particular device, based on its PCI bus id.
        ALL_PRODUCTS
        This value corresponds to the nvmlPciInfo_t::busId returned by nvmlDeviceGetPciInfo().
        Starting from NVML 5, this API causes NVML to initialize the target GPU
        NVML may initialize additional GPUs if: The target GPU is an SLI slave

        Note:
            NVML 4.304 and older version of nvmlDeviceGetHandleByPciBusId"_v1"
            returns NVML_ERROR_NOT_FOUND instead of NVML_ERROR_NO_PERMISSION.

        :return: the device handle with the specified pci bus id
        :rtype: Device
        """
        c_busId = c_char_p(pci_bus_id.encode("ASCII"))
        handle = CDevicePointer()
        fn = self.lib.get_function_pointer("nvmlDeviceGetHandleByPciBusId_v2")
        ret = fn(c_busId, byref(handle))
        Return.check(ret)
        return Device(self.lib, handle)