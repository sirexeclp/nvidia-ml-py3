"""Python wrapper for the NVML Library.

################################################################################
# Copyright (c) 2011-2015, NVIDIA Corporation.  All rights reserved.           #
#                                                                              #
# Redistribution and use in source and binary forms, with or without           #
# modification, are permitted provided that the following conditions are met:  #
#                                                                              #
#    * Redistributions of source code must retain the above copyright notice,  #
#      this list of conditions and the following disclaimer.                   #
#    * Redistributions in binary form must reproduce the above copyright       #
#      notice, this list of conditions and the following disclaimer in the     #
#      documentation and/or other materials provided with the distribution.    #
#    * Neither the name of the NVIDIA Corporation nor the names of its         #
#      contributors may be used to endorse or promote products derived from    #
#      this software without specific prior written permission.                #
#                                                                              #
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"  #
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE    #
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE   #
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE    #
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR          #
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF         #
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS     #
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN      #
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)      #
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF       #
# THE POSSIBILITY OF SUCH DAMAGE.                                              #
################################################################################
"""
import os
import sys
from ctypes import *
from functools import lru_cache
from pathlib import Path
from typing import Any, List

from pynvml3.device import Device, CDevicePointer
from pynvml3.enums import to_c_str
from pynvml3.errors import (
    NVMLErrorFunctionNotFound,
    NVMLErrorSharedLibraryNotFound,
    Return,
)
from pynvml3.event_set import EventSet
from pynvml3.system import System
from pynvml3.unit import CUnitPointer, Unit


def checked_function_wrapper(func):
    def checked_function(*args, **kwargs):
        ret = func(*args, **kwargs)
        Return.check(ret)

    return checked_function


class NVMLLib:
    """Methods that handle NVML initialization and cleanup."""

    def __init__(self):
        """Load the library."""
        self.nvml_lib = None
        self._load_nvml_library()

    def __enter__(self):
        """Initialize the library."""
        Return.check(self.nvml_lib.nvmlInit_v2())
        return self

    def __exit__(self, *argc, **kwargs):
        """Leave the library loaded, but shutdown the interface."""
        Return.check(self.nvml_lib.nvmlShutdown())

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
        """Load the library."""
        try:
            if sys.platform[:3] == "win":
                nvml_path = next((x for x in self._get_search_paths() if x.is_file()), None)
                if nvml_path is None:
                    raise NVMLErrorSharedLibraryNotFound
                
                # cdecl calling convention
                self.nvml_lib = CDLL(str(nvml_path))
            else:
                # assume linux
                self.nvml_lib = CDLL("libnvidia-ml.so.1")
        except OSError:
            raise NVMLErrorSharedLibraryNotFound
        if self.nvml_lib is None:
            raise NVMLErrorSharedLibraryNotFound

    @staticmethod
    def _get_search_paths() -> List[Path]:
        """Computes search paths for the library on Windows."""
        return [
            Path(os.getenv("WinDir", r"C:/Windows"), "System32/nvml.dll"),
            Path(os.getenv("ProgramFiles", r"C:/Program Files"), "NVIDIA Corporation/NVSMI/nvml.dll"),
        ]

    @lru_cache(maxsize=None)
    def get_function_pointer(
        self, name: str, check: bool=False
    ) -> "ctypes.CDLL.__init__.<locals>._FuncPtr":
        """Returns a function pointer for the given function name.
        Caching is used for YOUR convenience.
        """
        try:
            fn = getattr(self.nvml_lib, name)
            if check:
                return checked_function_wrapper(fn)
            return fn
        except AttributeError:
            raise NVMLErrorFunctionNotFound

    def __getattribute__(self, name: str) -> Any:
        try:
            return object.__getattribute__(self, name)
        except AttributeError:
            nvml_lib = object.__getattribute__(self, "nvml_lib")
            return checked_function_wrapper(getattr(nvml_lib, name))

    @property
    def unit(self) -> "UnitFactory":
        """Returns a new ``UnitFactory`` object, which can be used
        to build Unit-Objects in several ways.

        """

        return UnitFactory(self)

    @property
    def device(self) -> "DeviceFactory":
        """Returns a new ``DeviceFactory`` object, which can be used
        to build Device(GPU)-Objects in several ways.

        """

        return DeviceFactory(self)

    @property
    def system(self) -> "System":
        """Returns a new ``System`` object, which can be used
        to get system related information.

        """

        return System(self)

    @property
    def event_set(self) -> "EventSet":
        """Returns an new empty ``EventSet`` set."""

        return EventSet(self)


class UnitFactory:
    """This ``UnitFactory`` is used to create ``Unit`` objects
    in various ways. It ensures, that each ``Unit`` gets a reference
    to the :class:`NVMLLib`.

    """

    def __init__(self, lib: NVMLLib):
        self.lib = lib

    def from_index(self, index: int) -> Unit:
        """Acquire the handle for a particular unit, based on its index.

        Valid indices are derived from the unitCount returned by
        :func:`pynvml3.unit.Unit.get_count()`. For example, if unitCount is 2 the valid
        indices are 0 and 1, corresponding to UNIT 0 and UNIT 1.

        Args:
            index: index of the unit

        Returns:
            CUnitPointer: the Unit Object

        """

        c_index = c_uint(index)
        unit = CUnitPointer()
        fn = self.lib.nvml_lib.nvmlUnitGetHandleByIndex()
        ret = fn(c_index, byref(unit))
        Return.check(ret)
        return Unit(self.lib, unit)

    def get_count(self) -> int:
        """Retrieves the number of units in the system.

        Returns: the number of units

        """
        c_count = c_uint()
        fn = self.lib.get_function_pointer("nvmlUnitGetCount")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value


class DeviceFactory:
    """This ``DeviceFactory`` is used to create ``Device`` objects
    in various ways. It ensures, that each ``Device`` gets a reference
    to the :class:`NVMLLib`.

    """

    def __init__(self, lib):
        self.lib = lib
        self.iter_index = 0
        self._len = self.get_count()

    def __len__(self) -> int:
        return self._len

    def __iter__(self):
        self.iter_index = 0
        return self

    def __next__(self):
        try:
            result = self[self.iter_index]
        except IndexError:
            raise StopIteration
        self.iter_index += 1
        return result

    def get_count(self, permission: bool = False) -> int:
        """Retrieves the number of compute devices in the system.
        A compute device is a single GPU.

        Args:
            permission (bool): if set to True, count only devices
                with permission to initialize

        Note:
           New get_count (default in NVML 5.319) returns count of all devices
           in the system even if ``from_index`` raises ``NVML_ERROR_NO_PERMISSION``
           for such device. Set ``permission`` to True, to not
           count devices that NVML has no permission to talk to.

        """

        c_count = c_uint()
        if permission:
            self.lib.nvmlDeviceGetCount(byref(c_count))
        else:
            self.lib.nvmlDeviceGetCount_v2(byref(c_count))
        return c_count.value

    def __getitem__(self, key: int) -> Device:
        if not isinstance(key, int):
            raise ValueError(f"GPU Device Index bust be an integer not {type(key)}.")
        if key < 0 or key >= len(self):
            raise IndexError()
        return self.from_index(key)

    def from_index(self, index: int) -> Device:
        """Acquire the handle for a particular device, based on its index.

        Valid indices are derived from the accessibleDevices count returned by
        :func:`DeviceFactory.get_count` .
        For example, if accessibleDevices is 2 the valid indices are 0 and 1,
        corresponding to GPU 0 and GPU 1.

        The order in which NVML enumerates devices has no guarantees
        of consistency between reboots.
        For that reason it is recommended that devices be looked
        up by their PCI ids or UUID.
        See :func:`DeviceFactory.from_uuid` and
        :func:`DeviceFactory.from_pci_bus_id`.

        Note:
            The NVML index may not correlate with other APIs,
            such as the CUDA device index.

        Starting from NVML 5, this API causes NVML to initialize the target
        GPU NVML may initialize additional GPUs,
        if the target GPU is an SLI slave.

        Args:
            index: The index of the target GPU, >= 0 and < accessibleDevices

        Returns: the device object

        """
        c_index = c_uint(index)
        handle = CDevicePointer()
        fn = self.lib.nvmlDeviceGetHandleByIndex_v2
        ret = fn(c_index, byref(handle))
        return Device(self.lib, handle)

    def from_serial(self, serial: str) -> "Device":
        """Acquire the handle for a particular device,
        based on its board serial number.

        Attention:
            Since more than one GPU can exist on a single board this
            function is deprecated in favor of :func:`DeviceFactory.from_uuid`.

        Args:
            serial: The board serial number of the target GPU

        Returns: the device object

        Raises:
            NVMLErrorInvalidArgument: For dual GPU boards

        Note:
            This number corresponds to the value printed directly on the board,
            and to the value returned by nvmlDeviceGetSerial().
            Starting from NVML 5, this API causes NVML to initialize the target
            GPU NVML may initialize additional GPUs
            as it searches for the target GPU

        """
        handle = CDevicePointer()
        self.lib.nvmlDeviceGetHandleBySerial(to_c_str(serial), byref(handle))
        return Device(self.lib, handle)

    def from_uuid(self, uuid: str) -> "Device":
        """Acquire a particular device, based on its globally unique
        immutable UUID associated with each device.

        Note:
             Starting from NVML 5, this API causes NVML to initialize the
             target GPU NVML may initialize additional GPUs
             as it searches for the target GPU

            This API does not currently support acquiring
            MIG device handles using MIG device UUIDs.

        Args:
            uuid: The UUID of the target GPU

        Returns: the device object

        """
        handle = CDevicePointer()
        self.lib.nvmlDeviceGetHandleByUUID(to_c_str(uuid), byref(handle))
        return Device(self.lib, handle)

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

        Returns: the device handle with the specified pci bus id

        """
        handle = CDevicePointer()
        fn = self.lib.nvmlDeviceGetHandleByPciBusId_v2(
            to_c_str(pci_bus_id), byref(handle)
        )
        return Device(self.lib, handle)
