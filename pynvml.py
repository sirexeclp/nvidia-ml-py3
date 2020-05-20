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

##
# Python bindings for the NVML library
##
from ctypes import *
import sys
import os
import threading
from pathlib import Path
from typing import Tuple, List
from abc import ABC

from constants import *
from enums import *
from errors import Return, NVMLError, NVMLErrorFunctionNotFound, NVMLErrorSharedLibraryNotFound
from structs import *
from flags import *

"""
The NVIDIA Management Library (NVML) is a C-based programmatic interface for monitoring
and managing various states within NVIDIA Tesla™ GPUs.
It is intended to be a platform for building 3rd party applications,
and is also the underlying library for the NVIDIA-supported nvidia-smi tool.
NVML is thread-safe so it is safe to make simultaneous NVML calls from multiple threads.
https://docs.nvidia.com/deploy/nvml-api/nvml-api-reference.html
"""


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
        self.__enter__()

    def close(self) -> None:
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

class NvmlBase(ABC):
    """Abstract Base Class for NvmlLib."""

    def __init__(self):
        self.lib = NVMLLib()


class System(NvmlBase):
    """Queries that NVML can perform against the local system.
    These queries are not device-specific."""

    # Added in 2.285
    def get_nvml_version(self) -> str:
        """Retrieves the version of the NVML library.
        *ALL_PRODUCTS*
        The version identifier is an alphanumeric string.
        It will not exceed 80 characters in length (including the NULL terminator).
        See nvmlConstants::NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE."""
        c_version = create_string_buffer(SYSTEM_NVML_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetNVMLVersion")
        ret = fn(c_version, c_uint(SYSTEM_NVML_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 2.285
    def get_process_name(self, pid: int) -> str:
        """Gets name of the process with provided process id
        ALL_PRODUCTS
        Returned process name is cropped to provided length.
        name string is encoded in ANSI."""
        c_name = create_string_buffer(1024)
        fn = self.lib.get_function_pointer("nvmlSystemGetProcessName")
        ret = fn(c_uint(pid), c_name, c_uint(1024))
        Return.check(ret)
        return c_name.value.decode("UTF-8")

    def get_driver_version(self) -> str:
        """Retrieves the version of the system's graphics driver.
        ALL_PRODUCTS
        The version identifier is an alphanumeric string.
        It will not exceed 80 characters in length (including the NULL terminator).
        See nvmlConstants::NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE."""
        c_version = create_string_buffer(SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetDriverVersion")
        ret = fn(c_version, c_uint(SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 2.285
    def get_hic_version(self) -> List[HwbcEntry]:
        """Retrieves the IDs and firmware versions for any Host Interface Cards (HICs) in the system.
        S_CLASS
        The hwbcCount argument is expected to be set to the size of the input hwbcEntries array.
        The HIC must be connected to an S-class system for it to be reported by this function."""
        c_count = c_uint(0)
        hics = None
        fn = self.lib.get_function_pointer("nvmlSystemGetHicVersion")

        # get the count
        ret = fn(byref(c_count), None)

        # this should only fail with insufficient size
        return_value = Return(ret)
        if return_value != Return.SUCCESS and return_value != Return.ERROR_INSUFFICIENT_SIZE:
            raise return_value.get_exception()

        # if there are no hics
        if c_count.value == 0:
            return []

        hic_array = HwbcEntry * c_count.value
        hics = hic_array()
        ret = fn(byref(c_count), hics)
        Return.check(ret)
        return list(hics)

    def _get_cuda_driver_version(self) -> int:
        """Retrieves the version of the CUDA driver from the shared library."""
        fn = self.lib.get_function_pointer("nvmlSystemGetCudaDriverVersion_v2")
        cuda_driver_version = c_int()
        ret = fn(byref(cuda_driver_version))
        Return.check(ret)
        return cuda_driver_version.value

    def get_cuda_driver_version(self) -> Tuple[int, int]:
        """Retrieves the version of the CUDA driver from the shared library."""
        version = self._get_cuda_driver_version()
        major, minor = version // 1_000, (version % 1_000) // 10
        return major, minor

    def get_topology_gpu_set(self, cpu_number: int) -> List[CDevicePointer]:
        """Retrieve the set of GPUs that have a CPU affinity with the given CPU number.
        ALL_PRODUCTS
        Supported on Linux only."""
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlSystemGetTopologyGpuSet")
        # First call will get the size
        ret = fn(cpu_number, byref(c_count), None)
        Return.check(ret)
        # call again with a buffer
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        ret = fn(cpu_number, byref(c_count), c_devices)
        Return.check(ret)
        return list(c_devices)


class Unit(NvmlBase):
    """
    Unit get functions
    """

    def __init__(self, index):
        super().__init__()
        self.handle = self._get_handle_by_index(index)

    def _get_handle_by_index(self, index: int) -> CUnitPointer:
        c_index = c_uint(index)
        unit = CUnitPointer()
        fn = self.lib.get_function_pointer("nvmlUnitGetHandleByIndex")
        ret = fn(c_index, byref(unit))
        Return.check(ret)
        return unit

    @staticmethod
    def get_count() -> int:
        c_count = c_uint()
        fn = NVMLLib().get_function_pointer("nvmlUnitGetCount")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    def get_unit_info(self) -> UnitInfo:
        c_info = UnitInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetUnitInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_led_state(self) -> LedState:
        c_state = LedState()
        fn = self.lib.get_function_pointer("nvmlUnitGetLedState")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return c_state

    def get_psu_info(self) -> PSUInfo:
        c_info = PSUInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetPsuInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_temperature(self, temperature_type: TemperatureSensors) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlUnitGetTemperature")
        ret = fn(self.handle, c_uint(temperature_type.value), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_fan_speed_info(self) -> UnitFanSpeeds:
        c_speeds = UnitFanSpeeds()
        fn = self.lib.get_function_pointer("nvmlUnitGetFanSpeedInfo")
        ret = fn(self.handle, byref(c_speeds))
        Return.check(ret)
        return c_speeds

    # added to API
    def get_device_count(self) -> int:
        c_count = c_uint(0)
        # query the unit to determine device count
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), None)
        if ret == Return.ERROR_INSUFFICIENT_SIZE.value:
            ret = Return.SUCCESS.value
        Return.check(ret)
        return c_count.value

    def get_devices(self) -> List["Device"]:
        c_count = c_uint(self.get_device_count())
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), c_devices)
        Return.check(ret)
        return [Device(dev) for dev in c_devices]

    # Set functions
    def set_led_state(self, color) -> None:
        fn = self.lib.get_function_pointer("nvmlUnitSetLedState")
        ret = fn(self.handle, LedColor(color))
        Return.check(ret)


class Device(NvmlBase):
    """
    Queries that NVML can perform against each device.
    In each case the device is identified with an nvmlDevice_t handle.
    This handle is obtained by calling one of nvmlDeviceGetHandleByIndex(),
     nvmlDeviceGetHandleBySerial(), nvmlDeviceGetHandleByPciBusId() or nvmlDeviceGetHandleByUUID().
    """

    INFOROM_VERSION_BUFFER_SIZE = 16
    UUID_BUFFER_SIZE = 80
    NAME_BUFFER_SIZE = 64
    SERIAL_BUFFER_SIZE = 30
    VBIOS_VERSION_BUFFER_SIZE = 32
    PCI_BUS_ID_BUFFER_SIZE = 16

    def __init__(self, handle: CDevicePointer):
        super().__init__()
        self.handle: CDevicePointer = handle

    @staticmethod
    def nvmlDeviceGetCount(self) -> int:
        """ """
        c_count = c_uint()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetCount_v2")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    @staticmethod
    def from_index(index: int) -> "Device":
        """

        @param index:
        @type index:
        @return:
        @rtype: Device
        """
        c_index = c_uint(index)
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleByIndex_v2")
        ret = fn(c_index, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
    def from_serial(serial: str) -> "Device":
        """

        @param serial:
        @type serial:
        @return:
        @rtype: Device
        """
        c_serial = c_char_p(serial.encode("ASCII"))
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleBySerial")
        ret = fn(c_serial, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
    def from_uuid(uuid: str) -> "Device":
        """

        @param uuid:
        @type uuid:
        @return:
        @rtype: Device
        """
        c_uuid = c_char_p(uuid.encode("ASCII"))
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleByUUID")
        ret = fn(c_uuid, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
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
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleByPciBusId_v2")
        ret = fn(c_busId, byref(handle))
        Return.check(ret)
        return Device(handle)

    #
    # New Methods
    #
    #################################
    #        Device Queries         #
    #################################

    def get_clock(self, clock_type: ClockType, clock_id: ClockId) -> int:
        """
        Retrieves the clock speed for the clock specified by the clock type and clock ID.

        KEPLER_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @param clock_id: Identify which clock in the domain to query
        @type clock_id: ClockId
        @return: clock in MHz
        @rtype: int
        """
        fn = self.lib.get_function_pointer("nvmlDeviceGetClock")
        clock_mhz = c_uint()
        ret = fn(self.handle, clock_type.as_c_type(), clock_id.as_c_type(), byref(clock_mhz))
        Return.check(ret)
        return clock_mhz.value

    def get_cuda_compute_capability(self) -> Tuple[int, int]:
        """

        @return:
        @rtype:
        """
        major, minor = c_int(), c_int()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCudaComputeCapability")
        ret = fn(self.handle, byref(major), byref(minor))
        Return.check(ret)
        return major.value, minor.value

    def get_max_customer_boost_clock(self, clock_type: ClockType) -> int:
        """Retrieves the customer defined maximum boost clock speed specified by the given clock type."""
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxCustomerBoostClock")
        clock_mhz = c_uint()
        ret = fn(self.handle, clock_type.as_c_type(), byref(clock_mhz))
        Return.check(ret)
        return clock_mhz.value

    def get_total_energy_consumption(self) -> int:
        """
        Retrieves total energy consumption for this GPU in millijoules (mJ) since the driver was last reloaded

        VOLTA_OR_NEWER
        @return: energy consumption for this GPU in millijoules (mJ)
        @rtype: int
        """
        fn = self.lib.get_function_pointer("nvmlDeviceGetTotalEnergyConsumption")
        energy = c_ulonglong()
        ret = fn(self.handle, byref(energy))
        Return.check(ret)
        return energy.value

    #################################
    #          Drain State          #
    #################################

    #################################
    #        Device Commands        #
    #################################
    """
        This chapter describes NVML operations that change the state of the device.
        Each of these requires root/admin access.
        Non-admin users will see an NVML_ERROR_NO_PERMISSION error code when invoking any of these methods. 
    """

    def clear_ecc_error_counts(self, counterType: EccCounterType) -> None:
        """
        Clear the ECC error and other memory error counts for the device.
        KEPLER_OR_NEWER% Only applicable to devices with ECC.
        Requires NVML_INFOROM_ECC version 2.0 or higher to clear aggregate location-based ECC counts.
        Requires NVML_INFOROM_ECC version 1.0 or higher to clear all other ECC counts.
        Requires root/admin permissions.
        Requires ECC Mode to be enabled.
        Sets all of the specified ECC counters to 0, including both detailed and total counts.
        This operation takes effect immediately.
        See nvmlMemoryErrorType_t for details on available counter types.
        See also:
        nvmlDeviceGetDetailedEccErrors()
        nvmlDeviceGetTotalEccErrors()

        @param counterType:
        @type counterType:
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceClearEccErrorCounts")
        ret = fn(self.handle, counterType.as_c_type())
        Return.check(ret)

    def reset_gpu_locked_clocks(self) -> None:
        """
        @summary: Resets the gpu clock to the default value
        This is the gpu clock that will be used after system reboot or driver reload.
        Default values are idle clocks, but the current values can be changed using nvmlDeviceSetApplicationsClocks.

        See also:
        nvmlDeviceSetGpuLockedClocks

        VOLTA_OR_NEWER
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceResetGpuLockedClocks")
        ret = fn(self.handle)
        Return.check(ret)

    def set_api_restriction(self, api_type: RestrictedAPI, is_restricted: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetAPIRestriction")
        ret = fn(self.handle, api_type.as_c_type(),
                 is_restricted.as_c_type())
        Return.check(ret)

    # Added in 4.304
    def set_applications_clocks(self, max_mem_clock_mhz: int, max_graphics_clock_mhz: int) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetApplicationsClocks")
        ret = fn(self.handle, c_uint(max_mem_clock_mhz), c_uint(max_graphics_clock_mhz))
        Return.check(ret)

    def set_compute_mode(self, mode: ComputeMode) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetComputeMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_driver_model(self, model: DriverModel) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetDriverModel")
        ret = fn(self.handle, model.as_c_type())
        Return.check(ret)

    def set_ecc_mode(self, mode: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetEccMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_gpu_locked_clocks(self, min_gpu_clock_mhz: int, max_gpu_clock_mhz: int) -> None:
        """
        Set clocks that device will lock to.

        Sets the clocks that the device will be running at to the value in the range of minGpuClockMHz to maxGpuClockMHz. Setting this will supercede application clock values and take effect regardless if a cuda app is running. See /ref nvmlDeviceSetApplicationsClocks

        Can be used as a setting to request constant performance.

        Requires root/admin permissions.

        After system reboot or driver reload applications clocks go back to their default value. See nvmlDeviceResetGpuLockedClocks.

        VOLTA_OR_NEWER
        @param min_gpu_clock_mhz:
        @type min_gpu_clock_mhz:
        @param max_gpu_clock_mhz:
        @type max_gpu_clock_mhz:
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuLockedClocks")
        ret = fn(self.handle, c_uint(min_gpu_clock_mhz), c_uint(max_gpu_clock_mhz))
        Return.check(ret)

    # Added in 4.304
    def set_gpu_operation_mode(self, mode: GpuOperationMode) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuOperationMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_persistence_mode(self, enable_state: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetPersistenceMode")
        ret = fn(self.handle, enable_state.as_c_type())
        Return.check(ret)

    # Added in 4.304
    def set_power_management_limit(self, limit: int) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetPowerManagementLimit")
        ret = fn(self.handle, c_uint(limit))
        Return.check(ret)

    def get_nvlink(self, link_id: int) -> "NvLink":
        """
        Create an NvLink object, which provides nvlink methods.
        @param link_id: the id of the nvlink
        @type link_id: int
        @return: NvLink object
        @rtype: NvLink
        """
        return NvLink(self, link_id)

    #################################
    #        NvLink Methods         #
    #################################

    def freeze_nv_link_utilization_counter(self, link: int, counter: int, freeze: EnableState) -> None:
        """
        Freeze the NVLINK utilization counters Both the receive and transmit counters are operated on by this function

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be frozen (0 or 1).
        @type counter: int
        @param freeze: NVML_FEATURE_ENABLED = freeze the receive and transmit counters
            NVML_FEATURE_DISABLED = unfreeze the receive and transmit counters
        @type freeze: EnableState
        @return: None
        @rtype: None
        """
        fn = self.lib.get_function_pointer("nvmlDeviceFreezeNvLinkUtilizationCounter")
        ret = fn(self.handle, c_uint(link), c_uint(counter), freeze.as_c_type())
        Return.check(ret)

    def get_nv_link_capability(self, link: int, capability: NvLinkCapability) -> bool:
        """
        Retrieves the requested capability from the device's NvLink for the link specified.
        Please refer to the nvmlNvLinkCapability_t structure for the specific caps that can be queried.
        The return value should be treated as a boolean.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param capability: Specifies the nvmlNvLinkCapability_t to be queried
        @type capability: NvLinkCapability
        @return: A boolean for the queried capability indicating that feature is available
        @rtype: bool
        """
        cap_result = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkCapability")
        ret = fn(self.handle, c_uint(link), capability.as_c_type(), byref(cap_result))
        Return.check(ret)
        return bool(cap_result.value)

    def get_nv_link_error_counter(self, link: int, counter: NvLinkErrorCounter) -> int:
        """ Retrieves the specified error counter value.
        Please refer to nvmlNvLinkErrorCounter_t for error counters that are available

        PASCAL_OR_NEWER
        @return: error counter value
        @rtype: int
        """
        counter_value = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkErrorCounter")
        ret = fn(self.handle, c_uint(link), counter.as_c_type(), byref(counter_value))
        Return.check(ret)
        return counter_value.value

    def nvmlDeviceGetNvLinkRemotePciInfo(self, link: int) -> PciInfo:
        """Retrieves the PCI information for the remote node on a NvLink link
        Note: pciSubSystemId is not filled in this function and is indeterminate

        PASCAL_OR_NEWER"""
        pci_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkRemotePciInfo")
        ret = fn(self.handle, c_uint(link), byref(pci_info))
        Return.check(ret)
        return pci_info

    def nvmlDeviceGetNvLinkState(self, link: int) -> EnableState:
        """Retrieves the state of the device's NvLink for the link specified

        PASCAL_OR_NEWER"""
        is_active = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkState")
        ret = fn(self.handle, c_uint(link), byref(is_active))
        Return.check(ret)
        return EnableState(is_active.value)

    def nvmlDeviceGetNvLinkUtilizationControl(self, link: int, counter: int) -> NvLinkUtilizationControl:
        """Get the NVLINK utilization counter control information for the specified counter, 0 or 1.
        Please refer to nvmlNvLinkUtilizationControl_t for the structure definition.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be set (0 or 1).
        @type counter: int
        @return: NvLink utilization counter control information for the specified counter
        @rtype: NvLinkUtilizationControl
        """

        control = NvLinkUtilizationControl()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationControl")
        ret = fn(self.handle, c_uint(link), c_uint(counter), byref(control))
        Return.check(ret)
        return control

    def nvmlDeviceGetNvLinkUtilizationCounter(self, link: int, counter: int) -> Tuple[int, int]:
        rx_counter, tx_counter = c_ulonglong(), c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationCounter")
        ret = fn(self.handle, c_uint(link), c_uint(counter), byref(rx_counter), byref(tx_counter))
        Return.check(ret)
        return rx_counter.value, tx_counter.value

    def nvmlDeviceGetNvLinkVersion(self, link: int) -> int:
        version = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkVersion")
        ret = fn(self.handle, c_uint(link), byref(version))
        Return.check(ret)
        return version.value

    def nvmlDeviceResetNvLinkErrorCounters(self, link: int):
        fn = self.lib.get_function_pointer("nvmlDeviceResetNvLinkErrorCounters")
        ret = fn(self.handle, c_uint(link))
        Return.check(ret)

    def nvmlDeviceResetNvLinkUtilizationCounter(self, link: int, counter: int):
        fn = self.lib.get_function_pointer("nvmlDeviceResetNvLinkUtilizationCounter")
        ret = fn(self.handle, c_uint(link), c_uint(counter))
        Return.check(ret)

    def nvmlDeviceSetNvLinkUtilizationControl(self, link: int, counter: int,
                                              control: NvLinkUtilizationControl, reset: bool):
        fn = self.lib.get_function_pointer("nvmlDeviceSetNvLinkUtilizationControl")
        ret = fn(self.handle, c_uint(link), c_uint(counter), byref(control), c_uint(reset))
        Return.check(ret)

    #################################
    #      Field Value Queries      #
    #################################

    def get_field_values(self, values_count: int, field_id: FieldId) -> FieldValue:
        """Request values for a list of fields for a device.
        This API allows multiple fields to be queried at once.
        If any of the underlying fieldIds are populated by the same driver call,
        the results for those field IDs will be populated from a single call
        rather than making a driver call for each fieldId. """

        fn = self.lib.get_function_pointer("nvmlDeviceGetFieldValues")
        field_value: FieldValue = FieldValue()
        field_value.unused = 0
        field_value.fieldId = field_id.as_c_type()
        ret = fn(self.handle, c_int(values_count), byref(field_value))
        Return.check(ret)
        return field_value

    #################################
    #          Old Methods          #
    #################################

    def get_name(self) -> str:
        c_name = create_string_buffer(Device.NAME_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetName")
        ret = fn(self.handle, c_name, c_uint(Device.NAME_BUFFER_SIZE))
        Return.check(ret)
        return c_name.value.decode("UTF-8")

    def get_board_id(self) -> int:
        c_id = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBoardId")
        ret = fn(self.handle, byref(c_id))
        Return.check(ret)
        return c_id.value

    def get_multi_gpu_board(self) -> bool:
        c_multiGpu = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMultiGpuBoard")
        ret = fn(self.handle, byref(c_multiGpu))
        Return.check(ret)
        return bool(c_multiGpu.value)

    def get_brand(self) -> BrandType:
        c_type = BrandType.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBrand")
        ret = fn(self.handle, byref(c_type))
        Return.check(ret)
        return BrandType(c_type.value)

    def get_serial(self) -> str:
        c_serial = create_string_buffer(Device.SERIAL_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSerial")
        ret = fn(self.handle, c_serial, c_uint(Device.SERIAL_BUFFER_SIZE))
        Return.check(ret)
        return c_serial.value.decode("UTF-8")

    def get_cpu_affinity(self) -> List[int]:
        import os
        import math
        cpu_set_size = math.ceil(os.cpu_count() / sizeof(c_ulong))
        affinity_array = c_ulong * cpu_set_size
        c_affinity = affinity_array()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCpuAffinity")
        ret = fn(self.handle, c_uint(cpu_set_size), byref(c_affinity))
        Return.check(ret)
        return list(c_affinity)

    def set_cpu_affinity(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetCpuAffinity")
        ret = fn(self.handle)
        Return.check(ret)
        return None

    def clear_cpu_affinity(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceClearCpuAffinity")
        ret = fn(self.handle)
        Return.check(ret)
        return None

    def get_minor_number(self) -> int:
        c_minor_number = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMinorNumber")
        ret = fn(self.handle, byref(c_minor_number))
        Return.check(ret)
        return c_minor_number.value

    def get_uuid(self) -> str:
        c_uuid = create_string_buffer(Device.UUID_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetUUID")
        ret = fn(self.handle, c_uuid, c_uint(Device.UUID_BUFFER_SIZE))
        Return.check(ret)
        return c_uuid.value.decode("UTF-8")

    def get_inforom_version(self, info_rom_object: InfoRom) -> str:
        c_version = create_string_buffer(Device.INFOROM_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomVersion")
        ret = fn(self.handle, InfoRom.c_type(info_rom_object.value),
                 c_version, c_uint(Device.INFOROM_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 4.304
    def get_inforom_image_version(self) -> str:
        c_version = create_string_buffer(Device.INFOROM_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomImageVersion")
        ret = fn(self.handle, c_version, c_uint(Device.INFOROM_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 4.304
    def get_inforom_configuration_checksum(self) -> int:
        c_checksum = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomConfigurationChecksum")
        ret = fn(self.handle, byref(c_checksum))
        Return.check(ret)
        return c_checksum.value

    # Added in 4.304
    def validate_inforom(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceValidateInforom")
        ret = fn(self.handle)
        Return.check(ret)

    def get_display_mode(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def get_display_active(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayActive")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def get_persistence_mode(self) -> EnableState:
        c_state = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPersistenceMode")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return EnableState(c_state.value)

    def get_pci_info(self) -> PciInfo:
        c_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPciInfo_v2")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_clock_info(self, clock_type) -> int:
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetClockInfo")
        ret = fn(self.handle, ClockType.c_type(clock_type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 2.285
    def get_max_clock_info(self, clock_type: ClockType) -> int:
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxClockInfo")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def get_applications_clock(self, clock_type: ClockType) -> int:
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetApplicationsClock")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 5.319
    def get_default_applications_clock(self, clock_type: ClockType) -> int:
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDefaultApplicationsClock")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def get_supported_memory_clocks(self) -> List[int]:
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedMemoryClocks")
        ret = fn(self.handle, byref(c_count), None)

        result = Return(ret)
        if result == Return.SUCCESS:
            # special case, no clocks
            return []
        elif result == Return.ERROR_INSUFFICIENT_SIZE:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_clocks)
            Return.check(ret)
            return list(c_clocks)
        else:
            # error case
            raise NVMLError.from_return(ret)

    # Added in 4.304
    def get_supported_graphics_clocks(self, memory_clock_mhz: int) -> List[int]:
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedGraphicsClocks")
        ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), None)
        result = Return(ret)

        if result == Return.SUCCESS:
            # special case, no clocks
            return []
        elif result == Return.INSUFFICIENT_SIZE:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), c_clocks)
            Return.check(ret)
            return list(c_clocks)
        else:
            # error case
            raise NVMLError(ret)

    def get_fan_speed(self) -> int:
        c_speed = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetFanSpeed_v2")
        fan = c_uint(0)
        ret = fn(self.handle, fan, byref(c_speed))
        Return.check(ret)
        return c_speed.value

    def get_temperature(self, sensor: TemperatureSensors) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperature")
        ret = fn(self.handle, sensor.as_c_type(), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_temperature_threshold(self, threshold: TemperatureThresholds) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperatureThreshold")
        ret = fn(self.handle, threshold.as_c_type(), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    # DEPRECATED use nvmlDeviceGetPerformanceState
    def get_power_state(self) -> PowerState:
        """@deprecated"""
        power_state = PowerState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerState")
        ret = fn(self.handle, byref(power_state))
        Return.check(ret)
        return PowerState(power_state.value)

    def get_performance_state(self) -> PowerState:
        performance_state = PowerState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPerformanceState")
        ret = fn(self.handle, byref(performance_state))
        Return.check(ret)
        return PowerState(performance_state.value)

    def get_power_management_mode(self) -> EnableState:
        pcap_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementMode")
        ret = fn(self.handle, byref(pcap_mode))
        Return.check(ret)
        return EnableState(pcap_mode.value)

    def get_power_management_limit(self) -> int:
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 4.304
    def get_power_management_limit_constraints(self) -> Tuple[int, int]:
        c_minLimit = c_uint()
        c_maxLimit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementLimitConstraints")
        ret = fn(self.handle, byref(c_minLimit), byref(c_maxLimit))
        Return.check(ret)
        return c_minLimit.value, c_maxLimit.value

    # Added in 4.304
    def get_power_management_default_limit(self) -> int:
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementDefaultLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 331
    def get_enforced_power_limit(self) -> int:
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEnforcedPowerLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    def get_power_usage(self) -> int:
        milli_watts = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerUsage")
        ret = fn(self.handle, byref(milli_watts))
        Return.check(ret)
        return milli_watts.value

    # Added in 4.304
    def get_gpu_operation_mode(self) -> Tuple[GpuOperationMode, GpuOperationMode]:
        c_currState = GpuOperationMode.c_type()
        c_pendingState = GpuOperationMode.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetGpuOperationMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return GpuOperationMode(c_currState.value), GpuOperationMode(c_pendingState.value)

    # Added in 4.304
    def get_current_gpu_operation_mode(self) -> GpuOperationMode:
        return self.get_gpu_operation_mode()[0]

    # Added in 4.304
    def get_pending_gpu_operation_mode(self) -> GpuOperationMode:
        return self.get_gpu_operation_mode()[1]

    def get_memory_info(self) -> Memory:
        c_memory = Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryInfo")
        ret = fn(self.handle, byref(c_memory))
        Return.check(ret)
        return c_memory

    def get_bar1_memory_info(self) -> BAR1Memory:
        c_bar1_memory = BAR1Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBAR1MemoryInfo")
        ret = fn(self.handle, byref(c_bar1_memory))
        Return.check(ret)
        return c_bar1_memory

    def get_compute_mode(self) -> ComputeMode:
        c_mode = ComputeMode.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return ComputeMode(c_mode.value)

    def get_ecc_mode(self) -> Tuple[EnableState, EnableState]:
        c_currState = EnableState.c_type()
        c_pendingState = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEccMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return EnableState(c_currState.value), EnableState(c_pendingState.value)

    # added to API
    def get_current_ecc_mode(self) -> EnableState:
        return self.get_ecc_mode()[0]

    # added to API
    def get_pending_ecc_mode(self) -> EnableState:
        return self.get_ecc_mode()[1]

    def get_total_ecc_errors(self, error_type: MemoryErrorType, counter_type: EccCounterType) -> int:
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTotalEccErrors")
        ret = fn(self.handle, error_type.as_c_type(),
                 counter_type.as_c_type(), byref(c_count))
        Return.check(ret)
        return c_count.value

    # This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
    def get_detailed_ecc_errors(self, error_type: MemoryErrorType,
                                counter_type: EccCounterType) -> EccErrorCounts:
        """@deprecated: This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter"""
        c_counts = EccErrorCounts()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDetailedEccErrors")
        ret = fn(self.handle, error_type.as_c_type(),
                 counterType.as_c_type(), byref(c_counts))
        Return.check(ret)
        return c_counts

    # Added in 4.304
    def get_memory_error_counter(self, error_type: MemoryErrorType,
                                 counter_type: EccCounterType, location_type: MemoryLocation) -> int:
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryErrorCounter")
        ret = fn(self.handle, error_type.as_c_type(), counter_type.as_c_type(),
                 location_type.as_c_type(), byref(c_count))
        Return.check(ret)
        return c_count.value

    def get_utilization_rates(self) -> Utilization:
        c_util = Utilization()
        fn = self.lib.get_function_pointer("nvmlDeviceGetUtilizationRates")
        ret = fn(self.handle, byref(c_util))
        Return.check(ret)
        return c_util

    def get_encoder_utilization(self) -> Tuple[int, int]:
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEncoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return c_util.value, c_samplingPeriod.value

    def get_decoder_utilization(self) -> Tuple[int, int]:
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDecoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return c_util.value, c_samplingPeriod.value

    def get_pcie_replay_counter(self) -> int:
        c_replay = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieReplayCounter")
        ret = fn(self.handle, byref(c_replay))
        Return.check(ret)
        return c_replay.value

    def get_driver_model(self) -> Tuple[DriverModel, DriverModel]:
        c_currModel = DriverModel.c_type()
        c_pendingModel = DriverModel.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDriverModel")
        ret = fn(self.handle, byref(c_currModel), byref(c_pendingModel))
        Return.check(ret)
        return c_currModel.value, c_pendingModel.value

    # added to API
    def get_current_driver_model(self) -> DriverModel:
        return self.get_driver_model()[0]

    # added to API
    def get_pending_driver_model(self) -> DriverModel:
        return self.get_driver_model()[1]

    # Added in 2.285
    def get_vbios_version(self) -> str:
        c_version = create_string_buffer(Device.VBIOS_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetVbiosVersion")
        ret = fn(self.handle, c_version, c_uint(Device.VBIOS_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    def _get_running_processes(self, fn) -> List[ProcessInfo]:
        # first call to get the size
        c_count = c_uint(0)
        ret = fn(self.handle, byref(c_count), None)
        result = Return(ret)

        if result == Return.SUCCESS:
            # special case, no running processes
            return []
        elif result == Return.ERROR_INSUFFICIENT_SIZE:
            # typical case
            # oversize the array incase more processes are created
            c_count.value = c_count.value * 2 + 5
            proc_array = ProcessInfo * c_count.value
            c_procs = proc_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_procs)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                # use an alternative struct for this object
                obj: ProcessInfo = c_procs[i].get_friendly_object()
                if obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong:
                    # special case for WDDM on Windows, see comment above
                    obj.usedGpuMemory = None
                procs.append(obj)
            return procs
        else:
            # error case
            raise NVMLError(ret)

    # Added in 2.285
    def get_compute_running_processes(self) -> List[ProcessInfo]:
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeRunningProcesses")
        return self._get_running_processes(fn)

    def get_graphics_running_processes(self) -> List[ProcessInfo]:
        fn = self.lib.get_function_pointer("nvmlDeviceGetGraphicsRunningProcesses")
        return self._get_running_processes(fn)

    def get_auto_boosted_clocks_enabled(self) -> Tuple[EnableState, EnableState]:
        """

        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        c_isEnabled = EnableState.c_type()
        c_defaultIsEnabled = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAutoBoostedClocksEnabled")
        ret = fn(self.handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
        Return.check(ret)
        return EnableState(c_isEnabled.value), EnableState(c_defaultIsEnabled.value)

    def set_auto_boosted_clocks_enabled(self, enabled: EnableState) -> None:
        """

        @param enabled:
        @type enabled:
        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        fn = self.lib.get_function_pointer("nvmlDeviceSetAutoBoostedClocksEnabled")
        ret = fn(self.handle, enabled.as_c_type())
        Return.check(ret)

    def set_default_auto_boosted_clocks_enabled(self, enabled: EnableState, flags: int = 0) -> None:
        """

        @param flags: unused
        @type flags: int
        @param enabled:
        @type enabled:
        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        fn = self.lib.get_function_pointer(
            "nvmlDeviceSetDefaultAutoBoostedClocksEnabled")
        ret = fn(self.handle, enabled.as_c_type(), c_uint(flags))
        Return.check(ret)

    # Added in 4.304
    def reset_applications_clocks(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceResetApplicationsClocks")
        ret = fn(self.handle)
        Return.check(ret)

    #################################
    #         Event Methods         #
    #################################

    # Added in 2.285
    def register_events(self, event_types: EventType) -> "EventSet":
        """
        Starts recording of events on a specified devices and add the events to specified nvmlEventSet_t
        FERMI_OR_NEWER
        Ecc events are available only on ECC enabled devices (see nvmlDeviceGetTotalEccErrors)
        Power capping events are available only on Power Management enabled devices
        (see nvmlDeviceGetPowerManagementMode)
        For Linux only.
        IMPORTANT: Operations on set are not thread safe
        This call starts recording of events on specific device.
        All events that occurred before this call are not recorded.
        Checking if some event occurred can be done with nvmlEventSetWait.
        If function reports NVML_ERROR_UNKNOWN, event set is in undefined state and should be freed.
        If function reports NVML_ERROR_NOT_SUPPORTED, event set can still be used.
        None of the requested eventTypes are registered in that case.
        @param event_types:
        @type event_types:
        @param event_set:
        @type event_set: EventSet
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceRegisterEvents")
        event_set = EventSet()
        ret = fn(self.handle, event_types.as_c_type(), event_set.handle)
        Return.check(ret)
        return event_set

    # Added in 2.285
    def get_supported_event_types(self) -> EventType:
        """Returns information about events supported on device
        FERMI_OR_NEWER
        Events are not supported on Windows. So this function returns an empty mask in eventTypes on Windows."""
        c_eventTypes = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedEventTypes")
        ret = fn(self.handle, byref(c_eventTypes))
        Return.check(ret)
        return EventType(c_eventTypes.value)

    ### TODO:
    # Added in 3.295
    def on_same_board(self, device_2: "Device") -> bool:
        """

        @param device_2:
        @type device_2: Device
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceOnSameBoard")
        onSameBoard = c_int()
        ret = fn(self.handle, device_2.handle, byref(onSameBoard))
        Return.check(ret)
        return onSameBoard.value != 0

    # Added in 3.295
    def get_curr_pcie_link_generation(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkGeneration")
        gen = c_uint()
        ret = fn(self.handle, byref(gen))
        Return.check(ret)
        return gen.value

    # Added in 3.295
    def get_max_pcie_link_generation(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkGeneration")
        gen = c_uint()
        ret = fn(self.handle, byref(gen))
        Return.check(ret)
        return gen.value

    # Added in 3.295
    def get_curr_pcie_link_width(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkWidth")
        width = c_uint()
        ret = fn(self.handle, byref(width))
        Return.check(ret)
        return width.value

    # Added in 3.295
    def get_max_pcie_link_width(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkWidth")
        width = c_uint()
        ret = fn(self.handle, byref(width))
        Return.check(ret)
        return width.value

    # Added in 4.304
    def get_supported_clocks_throttle_reasons(self) -> int:
        c_reasons = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedClocksThrottleReasons")
        ret = fn(self.handle, byref(c_reasons))
        Return.check(ret)
        return c_reasons.value

    # Added in 4.304
    def get_current_clocks_throttle_reasons(self) -> int:
        c_reasons = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrentClocksThrottleReasons")
        ret = fn(self.handle, byref(c_reasons))
        Return.check(ret)
        return c_reasons.value

    # Added in 5.319
    def get_index(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetIndex")
        c_index = c_uint()
        ret = fn(self.handle, byref(c_index))
        Return.check(ret)
        return c_index.value

    # Added in 5.319
    def get_accounting_mode(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def set_accounting_mode(self, mode: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetAccountingMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def clear_accounting_pids(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceClearAccountingPids")
        ret = fn(self.handle)
        Return.check(ret)

    def get_accounting_stats(self, pid: int) -> AccountingStats:
        stats = AccountingStats()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingStats")
        ret = fn(self.handle, c_uint(pid), byref(stats))
        Return.check(ret)
        if stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong:
            # special case for WDDM on Windows, see comment above
            stats.maxMemoryUsage = None
        return stats

    def get_accounting_buffer_size(self) -> int:
        bufferSize = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingBufferSize")
        ret = fn(self.handle, byref(bufferSize))
        Return.check(ret)
        return bufferSize.value

    def get_accounting_pids(self) -> List[int]:
        count = c_uint(self.get_accounting_buffer_size())
        pids = (c_uint * count.value)()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingPids")
        ret = fn(self.handle, byref(count), pids)
        Return.check(ret)
        return list(pids)

    def get_retired_pages(self, source_filter: PageRetirementCause) -> List[int]:
        c_source = source_filter.as_c_type()
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPages")

        # First call will get the size
        ret = fn(self.handle, c_source, byref(c_count), None)
        result = Return(ret)
        # this should only fail with insufficient size
        if ((result != Return.SUCCESS) and
                (result != Return.ERROR_INSUFFICIENT_SIZE)):
            raise NVMLError(ret)

        # call again with a buffer
        # oversize the array for the rare cases where additional pages
        # are retired between NVML calls
        c_count.value = c_count.value * 2 + 5
        page_array = c_ulonglong * c_count.value
        c_pages = page_array()
        ret = fn(self.handle, c_source, byref(c_count), c_pages)
        Return.check(ret)
        return list(c_pages)

    def get_retired_pages_pending_status(self) -> EnableState:
        c_pending = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPagesPendingStatus")
        ret = fn(self.handle, byref(c_pending))
        Return.check(ret)
        return EnableState(c_pending.value)

    def get_api_restriction(self, api_type: RestrictedAPI) -> EnableState:
        c_permission = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAPIRestriction")
        ret = fn(self.handle, api_type.as_c_type(), byref(c_permission))
        Return.check(ret)
        return EnableState(c_permission.value)

    def get_bridge_chip_info(self) -> BridgeChipHierarchy:
        bridge_hierarchy = BridgeChipHierarchy()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBridgeChipInfo")
        ret = fn(self.handle, byref(bridge_hierarchy))
        Return.check(ret)
        return bridge_hierarchy

    def get_samples(self, sampling_type: SamplingType, time_stamp: int) -> Tuple[ValueType, List[Sample]]:
        c_sampling_type = sampling_type.as_c_type()
        c_time_stamp = c_ulonglong(time_stamp)
        c_sample_count = c_uint(0)
        c_sample_value_type = ValueType.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSamples")

        # First Call gets the size
        ret = fn(self.handle, c_sampling_type, c_time_stamp,
                 byref(c_sample_value_type), byref(c_sample_count), None)
        Return.check(ret)

        sampleArray = c_sample_count.value * Sample
        c_samples = sampleArray()
        ret = fn(self.handle, c_sampling_type, c_time_stamp,
                 byref(c_sample_value_type), byref(c_sample_count), c_samples)
        Return.check(ret)
        return ValueType(c_sample_value_type.value), list(c_samples)

    def nvmlDeviceGetViolationStatus(self, perf_policy_type: PerfPolicyType) -> ViolationTime:
        c_violTime = ViolationTime()
        fn = self.lib.get_function_pointer("nvmlDeviceGetViolationStatus")

        # Invoke the method to get violation time
        ret = fn(self.handle, perf_policy_type.as_c_type(), byref(c_violTime))
        Return.check(ret)
        return c_violTime

    def nvmlDeviceGetPcieThroughput(self, counter: PcieUtilCounter) -> int:
        c_util = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieThroughput")
        ret = fn(self.handle, counter.as_c_type(), byref(c_util))
        Return.check(ret)
        return c_util.value

    def nvmlDeviceGetTopologyNearestGpus(self, level: GpuTopologyLevel):
        """

        @param level:
        @type level:
        @return:
        @rtype: List[Device]
        """
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyNearestGpus")

        # First call will get the size
        ret = fn(self.handle, level.as_c_type(), byref(c_count), None)
        Return.check(ret)

        # call again with a buffer
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        ret = fn(self.handle, level.as_c_type(), byref(c_count), c_devices)
        Return.check(ret)
        return [Device(x) for x in c_devices]

    def nvmlDeviceGetTopologyCommonAncestor(self, device2: "Device") -> GpuTopologyLevel:
        """

        @param device2:
        @type device2: Device
        @return:
        @rtype: GpuTopologyLevel
        """
        c_level = GpuTopologyLevel.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyCommonAncestor")
        ret = fn(self.handle, device2.handle, byref(c_level))
        Return.check(ret)
        return GpuTopologyLevel(c_level.value)


class EventSet(NvmlBase):
    """Handle to an event set,
    methods that NVML can perform against each device to register
    and wait for some event to occur."""

    def __init__(self):
        super().__init__()
        self.handle = EventSet.create()

    def __del__(self):
        if self.handle is not None:
            self.free()

    # Added in 2.285
    @staticmethod
    def create() -> "EventSet":
        """
        Create an empty set of events. Event set should be freed by nvmlEventSetFree
        FERMI_OR_NEWER
        """
        fn = NVMLLib().get_function_pointer("nvmlEventSetCreate")
        eventSet = CEventSetPointer()
        ret = fn(byref(eventSet))
        Return.check(ret)
        return eventSet

    # Added in 2.285
    def free(self) -> None:
        """Releases events in the set
        FERMI_OR_NEWER"""
        fn = self.lib.get_function_pointer("nvmlEventSetFree")
        ret = fn(self.handle)
        Return.check(ret)
        self.handle = None

    # Added in 2.285
    # raises ERROR_TIMEOUT exception on timeout
    def wait(self, timeout_ms: int) -> EventData:
        """
        Waits on events and delivers events
        FERMI_OR_NEWER
        If some events are ready to be delivered at the time of the call, function returns immediately.
        If there are no events ready to be delivered, function sleeps till event
        arrives but not longer than specified timeout.
        This function in certain conditions can return before specified timeout passes (e.g. when interrupt arrives)
        In case of xid error, the function returns the most recent xid error type seen by the system.
        If there are multiple xid errors generated before nvmlEventSetWait is invoked then the last
        seen xid error type is returned for all xid error events.
        @param timeout_ms:
        @type timeout_ms: int
        @return:
        @rtype: EventData
        """
        fn = self.lib.get_function_pointer("nvmlEventSetWait")
        data = EventData()
        ret = fn(self.handle, byref(data), c_uint(timeout_ms))
        Return.check(ret)
        return data


#################################
#        NvLink Methods         #
#################################

class NvLink:
    """Methods that NVML can perform on NVLINK enabled devices."""

    def __init__(self, device, link_id):
        self.device = device
        self.link = link_id

    def freeze_utilization_counter(self, counter: int, freeze: EnableState) -> None:
        """
        Freeze the NVLINK utilization counters Both the receive and transmit counters are operated on by this function

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be frozen (0 or 1).
        @type counter: int
        @param freeze: NVML_FEATURE_ENABLED = freeze the receive and transmit counters
            NVML_FEATURE_DISABLED = unfreeze the receive and transmit counters
        @type freeze: EnableState
        @return: None
        @rtype: None
        """
        fn = self.device.lib.get_function_pointer("nvmlDeviceFreezeNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(self.link), c_uint(counter), freeze.as_c_type())
        Return.check(ret)

    def get_capability(self, link: int, capability: NvLinkCapability) -> bool:
        """
        Retrieves the requested capability from the device's NvLink for the link specified.
        Please refer to the nvmlNvLinkCapability_t structure for the specific caps that can be queried.
        The return value should be treated as a boolean.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param capability: Specifies the nvmlNvLinkCapability_t to be queried
        @type capability: NvLinkCapability
        @return: A boolean for the queried capability indicating that feature is available
        @rtype: bool
        """
        cap_result = c_uint()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkCapability")
        ret = fn(self.device.handle, c_uint(link), capability.as_c_type(), byref(cap_result))
        Return.check(ret)
        return bool(cap_result.value)

    def get_error_counter(self, link: int, counter: NvLinkErrorCounter) -> int:
        """ Retrieves the specified error counter value.
        Please refer to nvmlNvLinkErrorCounter_t for error counters that are available

        PASCAL_OR_NEWER
        @return: error counter value
        @rtype: int
        """
        counter_value = c_ulonglong()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkErrorCounter")
        ret = fn(self.device.handle, c_uint(link), counter.as_c_type(), byref(counter_value))
        Return.check(ret)
        return counter_value.value

    def get_remote_pci_info(self, link: int) -> PciInfo:
        """Retrieves the PCI information for the remote node on a NvLink link
        Note: pciSubSystemId is not filled in this function and is indeterminate

        PASCAL_OR_NEWER"""
        pci_info = PciInfo()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkRemotePciInfo")
        ret = fn(self.device.handle, c_uint(link), byref(pci_info))
        Return.check(ret)
        return pci_info

    def get_state(self, link: int) -> EnableState:
        """Retrieves the state of the device's NvLink for the link specified

        PASCAL_OR_NEWER"""
        is_active = EnableState.c_type()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkState")
        ret = fn(self.device.handle, c_uint(link), byref(is_active))
        Return.check(ret)
        return EnableState(is_active.value)

    def get_utilization_control(self, link: int, counter: int) -> NvLinkUtilizationControl:
        """Get the NVLINK utilization counter control information for the specified counter, 0 or 1.
        Please refer to nvmlNvLinkUtilizationControl_t for the structure definition.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be set (0 or 1).
        @type counter: int
        @return: NvLink utilization counter control information for the specified counter
        @rtype: NvLinkUtilizationControl
        """

        control = NvLinkUtilizationControl()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationControl")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(control))
        Return.check(ret)
        return control

    def get_utilization_counter(self, link: int, counter: int) -> Tuple[int ,int]:
        rx_counter, tx_counter = c_ulonglong(), c_ulonglong()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(rx_counter), byref(tx_counter))
        Return.check(ret)
        return rx_counter.value, tx_counter.value

    def get_version(self, link: int) -> int:
        version = c_uint()
        fn = self.device.lib.get_function_pointer("nvmlDeviceGetNvLinkVersion")
        ret = fn(self.device.handle, c_uint(link), byref(version))
        Return.check(ret)
        return version.value

    def reset_error_counters(self, link: int) -> None:
        fn = self.device.lib.get_function_pointer("nvmlDeviceResetNvLinkErrorCounters")
        ret = fn(self.device.handle, c_uint(link))
        Return.check(ret)

    def reset_utilization_counter(self, link: int, counter: int) -> None:
        fn = self.device.lib.get_function_pointer("nvmlDeviceResetNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter))
        Return.check(ret)

    def set_utilization_control(self, link: int, counter: int,
                                        control: NvLinkUtilizationControl, reset: bool) -> None:
        fn = self.device.lib.get_function_pointer("nvmlDeviceSetNvLinkUtilizationControl")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(control), c_uint(reset))
        Return.check(ret)
