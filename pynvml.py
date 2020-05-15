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

from constants import *
from enums import *
from errors import Return, NVMLError, NVMLErrorFunctionNotFound, NVMLErrorSharedLibraryNotFound
from structs import *
from flags import *


class NVMLLib:
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

    def open(self):
        self.__enter__()

    def close(self):
        self.__exit__()

    def _load_nvml_library(self):
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
    def _get_search_paths(self):
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

class NvmlBase:
    def __init__(self):
        self.lib = NVMLLib()


class System(NvmlBase):
    # Added in 2.285
    def get_nvml_version(self):
        c_version = create_string_buffer(SYSTEM_NVML_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetNVMLVersion")
        ret = fn(c_version, c_uint(SYSTEM_NVML_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value

    # Added in 2.285
    def get_process_name(self, pid):
        c_name = create_string_buffer(1024)
        fn = self.lib.get_function_pointer("nvmlSystemGetProcessName")
        ret = fn(c_uint(pid), c_name, c_uint(1024))
        Return.check(ret)
        return c_name.value

    def get_driver_version(self):
        c_version = create_string_buffer(SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetDriverVersion")
        ret = fn(c_version, c_uint(SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value

    # Added in 2.285
    def get_hic_version(self):
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
        return hics


class Unit(NvmlBase):
    """
    Unit get functions
    """

    def __init__(self, index):
        super().__init__()
        self.handle = self._get_handle_by_index(index)

    def _get_handle_by_index(self, index: int):
        c_index = c_uint(index)
        unit = CUnitPointer()
        fn = self.lib.get_function_pointer("nvmlUnitGetHandleByIndex")
        ret = fn(c_index, byref(unit))
        Return.check(ret)
        return unit

    @staticmethod
    def get_count():
        c_count = c_uint()
        fn = NVMLLib().get_function_pointer("nvmlUnitGetCount")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    def get_unit_info(self):
        c_info = UnitInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetUnitInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_led_state(self):
        c_state = LedState()
        fn = self.lib.get_function_pointer("nvmlUnitGetLedState")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return c_state

    def get_psu_info(self):
        c_info = PSUInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetPsuInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_temperature(self, temperature_type: TemperatureSensors):
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlUnitGetTemperature")
        ret = fn(self.handle, c_uint(temperature_type.value), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_fan_speed_info(self):
        c_speeds = UnitFanSpeeds()
        fn = self.lib.get_function_pointer("nvmlUnitGetFanSpeedInfo")
        ret = fn(self.handle, byref(c_speeds))
        Return.check(ret)
        return c_speeds

    # added to API
    def get_device_count(self):
        c_count = c_uint(0)
        # query the unit to determine device count
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), None)
        if ret == Return.ERROR_INSUFFICIENT_SIZE.value:
            ret = Return.SUCCESS.value
        Return.check(ret)
        return c_count.value

    def get_devices(self):
        c_count = c_uint(self.get_device_count())
        device_array = CDevice * c_count.value
        c_devices = device_array()
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), c_devices)
        Return.check(ret)
        return c_devices


class Device(NvmlBase):
    INFOROM_VERSION_BUFFER_SIZE = 16
    UUID_BUFFER_SIZE = 80
    NAME_BUFFER_SIZE = 64
    SERIAL_BUFFER_SIZE = 30
    VBIOS_VERSION_BUFFER_SIZE = 32
    PCI_BUS_ID_BUFFER_SIZE = 16

    def __init__(self, handle):
        super().__init__()
        self.handle = handle

    @staticmethod
    def nvmlDeviceGetCount(self):
        c_count = c_uint()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetCount_v2")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    @staticmethod
    def from_index(index: int):
        c_index = c_uint(index)
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleByIndex_v2")
        ret = fn(c_index, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
    def from_serial(serial: str):
        c_serial = c_char_p(serial.encode("ASCII"))
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleBySerial")
        ret = fn(c_serial, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
    def from_uuid(uuid: str):
        """

        @param uuid:
        @type uuid:
        @return:
        @rtype:
        """
        c_uuid = c_char_p(uuid.encode("ASCII"))
        handle = CDevicePointer()
        fn = NVMLLib().get_function_pointer("nvmlDeviceGetHandleByUUID")
        ret = fn(c_uuid, byref(handle))
        Return.check(ret)
        return Device(handle)

    @staticmethod
    def from_pci_bus_id(self, pci_bus_id: str):
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
    def get_cuda_compute_capability(self):
        """

        @return:
        @rtype:
        """
        major, minor = c_int(), c_int()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCudaComputeCapability")
        ret = fn(self.handle, byref(major), byref(minor))
        Return.check(ret)
        return major.value, minor.value

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
    def clear_ecc_error_counts(self, counterType: EccCounterType):
        """
        Clear the ECC error and other memory error counts for the device.

KEPLER_OR_NEWER% Only applicable to devices with ECC. Requires NVML_INFOROM_ECC version 2.0 or higher to clear aggregate location-based ECC counts. Requires NVML_INFOROM_ECC version 1.0 or higher to clear all other ECC counts. Requires root/admin permissions. Requires ECC Mode to be enabled.

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
        return None

    def reset_gpu_locked_clocks(self):
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

    def set_api_restriction(self, apiType: RestrictedAPI, isRestricted):
        fn = self.lib.get_function_pointer("nvmlDeviceSetAPIRestriction")
        ret = fn(self.handle, apiType.as_c_type(),
                 EnableState.YPE(isRestricted))
        Return.check(ret)
        return None

    # Added in 4.304
    def set_applications_clocks(self, max_mem_clock_mhz, max_graphics_clock_mhz):
        fn = self.lib.get_function_pointer("nvmlDeviceSetApplicationsClocks")
        ret = fn(self.handle, c_uint(max_mem_clock_mhz), c_uint(max_graphics_clock_mhz))
        Return.check(ret)
        return None

    def set_compute_mode(self, mode: ComputeMode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetComputeMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)
        return None

    def set_driver_model(self, model: DriverModel):
        fn = self.lib.get_function_pointer("nvmlDeviceSetDriverModel")
        ret = fn(self.handle, model.as_c_type())
        Return.check(ret)
        return None

    def set_ecc_mode(self, mode: EnableState):
        fn = self.lib.get_function_pointer("nvmlDeviceSetEccMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)
        return None

    def set_gpu_locked_clocks(self, min_gpu_clock_mhz: int, max_gpu_clock_mhz: int):
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
    def set_gpu_operation_mode(self, mode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuOperationMode")
        ret = fn(self.handle, GpuOperationMode.c_type(mode))
        Return.check(ret)
        return None

    def set_persistence_mode(self, enable_state: EnableState):
        fn = self.lib.get_function_pointer("nvmlDeviceSetPersistenceMode")
        ret = fn(self.handle, enable_state.as_c_type())
        Return.check(ret)
        return None

    # Added in 4.304
    def set_power_management_limit(self, limit):
        fn = self.lib.get_function_pointer("nvmlDeviceSetPowerManagementLimit")
        ret = fn(self.handle, c_uint(limit))
        Return.check(ret)
        return None


    def get_nvlink(self, link_id: int):
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

    def nvmlDeviceGetNvLinkUtilizationCounter(self, link: int, counter: int):
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

    def get_cpu_affinity(self, cpu_set_size):
        affinity_array = c_ulonglong * cpu_set_size
        c_affinity = affinity_array()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCpuAffinity")
        ret = fn(self.handle, c_uint(cpu_set_size), byref(c_affinity))
        Return.check(ret)
        return c_affinity

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
        return None

    def get_display_mode(self) -> int:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return c_mode.value

    def nvml_device_get_display_active(self):
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayActive")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return c_mode.value

    def get_persistence_mode(self) -> EnableState:
        c_state = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPersistenceMode")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return EnableState(c_state.value)

    def nvml_device_get_pci_info(self):
        c_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPciInfo_v2")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def nvml_device_get_clock_info(self, clock_type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetClockInfo")
        ret = fn(self.handle, ClockType.c_type(clock_type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 2.285
    def nvml_device_get_max_clock_info(self, clock_type:ClockType):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxClockInfo")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def nvml_device_get_applications_clock(self, clock_type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetApplicationsClock")
        ret = fn(self.handle, ClockType.c_type(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 5.319
    def nvml_device_get_default_applications_clock(self, clock_type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDefaultApplicationsClock")
        ret = fn(self.handle, ClockType.c_type(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def nvml_device_get_supported_memory_clocks(self):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedMemoryClocks")
        ret = fn(self.handle, byref(c_count), None)

        if ret == Return.SUCCESS.value:
            # special case, no clocks
            return []
        elif ret == Return.INSUFFICIENT_SIZE.value:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_clocks)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                procs.append(c_clocks[i])

            return procs
        else:
            # error case
            raise NVMLError.from_return(ret)

    # Added in 4.304
    def nvml_device_get_supported_graphics_clocks(self, memory_clock_mhz):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedGraphicsClocks")
        ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), None)

        if ret == Return.SUCCESS.value:
            # special case, no clocks
            return []
        elif ret == Return.INSUFFICIENT_SIZE.value:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), c_clocks)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                procs.append(c_clocks[i])

            return procs
        else:
            # error case
            raise NVMLError(ret)

    def nvml_device_get_fan_speed(self):
        c_speed = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetFanSpeed")
        ret = fn(self.handle, byref(c_speed))
        Return.check(ret)
        return c_speed.value

    def nvml_device_get_temperature(self, sensor):
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperature")
        ret = fn(self.handle, TemperatureSensors.c_type(sensor), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def nvml_device_get_temperature_threshold(self, threshold):
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperatureThreshold")
        ret = fn(self.handle, TemperatureThresholds.c_type(threshold), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    # DEPRECATED use nvmlDeviceGetPerformanceState
    def nvml_device_get_power_state(self):
        _P = Ps()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerState")
        ret = fn(self.handle, byref(c_P))
        Return.check(ret)
        return c_P.value

    def nvml_device_get_performance_state(self):
        _P = Ps()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPerformanceState")
        ret = fn(self.handle, byref(c_P))
        Return.check(ret)
        return c_P.value

    def nvml_device_get_power_management_mode(self):
        _pcapMode = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementMode")
        ret = fn(self.handle, byref(c_pcapMode))
        Return.check(ret)
        return c_pcapMode.value

    def nvml_device_get_power_management_limit(self):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 4.304
    def nvml_device_get_power_management_limit_constraints(self):
        c_minLimit = c_uint()
        c_maxLimit = c_uint()
        fn = self.lib.get_function_pointer(
            "nvmlDeviceGetPowerManagementLimitConstraints")
        ret = fn(self.handle, byref(c_minLimit), byref(c_maxLimit))
        Return.check(ret)
        return [c_minLimit.value, c_maxLimit.value]

    # Added in 4.304
    def nvml_device_get_power_management_default_limit(self):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementDefaultLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 331
    def nvml_device_get_enforced_power_limit(self):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEnforcedPowerLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    def nvml_device_get_power_usage(self):
        c_watts = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerUsage")
        ret = fn(self.handle, byref(c_watts))
        Return.check(ret)
        return c_watts.value

    # Added in 4.304
    def nvml_device_get_gpu_operation_mode(self):
        c_currState = GpuOperationMode()
        c_pendingState = GpuOperationMode()
        fn = self.lib.get_function_pointer("nvmlDeviceGetGpuOperationMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return [c_currState.value, c_pendingState.value]

    # Added in 4.304
    def nvml_device_get_current_gpu_operation_mode(self):
        return self.nvmlDeviceGetGpuOperationMode(self.handle)[0]

    # Added in 4.304
    def nvml_device_get_pending_gpu_operation_mode(self):
        return self.nvmlDeviceGetGpuOperationMode(self.handle)[1]

    def nvml_device_get_memory_info(self):
        c_memory = Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryInfo")
        ret = fn(self.handle, byref(c_memory))
        Return.check(ret)
        return c_memory

    def nvml_device_get_b_a_r1_memory_info(self):
        c_bar1_memory = BAR1Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBAR1MemoryInfo")
        ret = fn(self.handle, byref(c_bar1_memory))
        Return.check(ret)
        return c_bar1_memory

    def nvml_device_get_compute_mode(self):
        c_mode = ComputeMode.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return c_mode.value

    def nvml_device_get_ecc_mode(self):
        c_currState = EnableState.c_type()
        c_pendingState = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEccMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return [c_currState.value, c_pendingState.value]

    # added to API
    def nvml_device_get_current_ecc_mode(self):
        return self.nvmlDeviceGetEccMode(self.handle)[0]

    # added to API
    def nvml_device_get_pending_ecc_mode(self):
        return self.nvmlDeviceGetEccMode(self.handle)[1]

    def nvml_device_get_total_ecc_errors(self, errorType:MemoryErrorType, counterType:EccCounterType):
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTotalEccErrors")
        ret = fn(self.handle, errorType.as_c_type(),
                 counterType.as_c_type(), byref(c_count))
        Return.check(ret)
        return c_count.value

    # This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
    def nvml_device_get_detailed_ecc_errors(self, errorType, counterType:EccCounterType):
        c_counts = EccErrorCounts()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDetailedEccErrors")
        ret = fn(self.handle, errorType.as_c_type(),
                 counterType.as_c_type(), byref(c_counts))
        Return.check(ret)
        return c_counts

    # Added in 4.304
    def nvml_device_get_memory_error_counter(handle, errorType, counterType, locationType):
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryErrorCounter")
        ret = fn(self.handle,
                 MemoryErrorType.c_type(errorType),
                 EcCounterType(counterType),
                 MemoryLoation(locationType),
                 byref(c_count))
        Return.check(ret)
        return c_count.value

    def nvml_device_get_utilization_rates(self):
        c_util = Utilization()
        fn = self.lib.get_function_pointer("nvmlDeviceGetUtilizationRates")
        ret = fn(self.handle, byref(c_util))
        Return.check(ret)
        return c_util

    def nvml_device_get_encoder_utilization(self):
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEncoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return [c_util.value, c_samplingPeriod.value]

    def nvml_device_get_decoder_utilization(self):
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDecoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return [c_util.value, c_samplingPeriod.value]

    def nvml_device_get_pcie_replay_counter(self):
        c_replay = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieReplayCounter")
        ret = fn(self.handle, byref(c_replay))
        Return.check(ret)
        return c_replay.value

    def nvml_device_get_driver_model(self):
        c_currModel = DriverModel.c_type()
        c_pendingModel = DriverModel.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDriverModel")
        ret = fn(self.handle, byref(c_currModel), byref(c_pendingModel))
        Return.check(ret)
        return [c_currModel.value, c_pendingModel.value]

    # added to API
    def nvml_device_get_current_driver_model(self):
        return self.nvmlDeviceGetDriverModel(self.handle)[0]

    # added to API
    def nvml_device_get_pending_driver_model(self):
        return self.nvmlDeviceGetDriverModel(self.handle)[1]

    # Added in 2.285
    def nvml_device_get_vbios_version(self):
        c_version = create_string_buffer(Device.VBIOS_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetVbiosVersion")
        ret = fn(self.handle, c_version, c_uint(Device.VBIOS_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value

    # Added in 2.285
    def nvml_device_get_compute_running_processes(self):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeRunningProcesses")
        ret = fn(self.handle, byref(c_count), None)

        if ret == Return.SUCCESS.value:
            # special case, no running processes
            return []
        elif ret == ERROR_INSUFFICIENT_SIZE:
            # typical case
            # oversize the array incase more processes are created
            c_count.value = c_count.value * 2 + 5
            pro_array = cProcessInfo * c_count.value
            c_procs = proc_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_procs)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                # use an alternative struct for this object
                obj = struct2friendly_object(c_procs[i])
                if obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong:
                    # special case for WDDM on Windows, see comment above
                    obj.usedGpuMemory = None
                procs.append(obj)

            return procs
        else:
            # error case
            raise NVMLError(ret)

    def nvml_device_get_graphics_running_processes(self):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetGraphicsRunningProcesses")
        ret = fn(self.handle, byref(c_count), None)

        if ret == Return.SUCCESS.value:
            # special case, no running processes
            return []
        elif ret == ERROR_INSUFFICIENT_SIZE:
            # typical case
            # oversize the array incase more processes are created
            c_count.value = c_count.value * 2 + 5
            pro_array = cProcessInfo * c_count.value
            c_procs = proc_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_procs)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                # use an alternative struct for this object
                obj = struct2friendly_object(c_procs[i])
                if obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong:
                    # special case for WDDM on Windows, see comment above
                    obj.usedGpuMemory = None
                procs.append(obj)

            return procs
        else:
            # error case
            raise NVMLError(ret)

    def nvml_device_get_auto_boosted_clocks_enabled(self):
        c_isEnabled = EnableState.c_type()
        c_defaultIsEnabled = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAutoBoostedClocksEnabled")
        ret = fn(self.handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
        Return.check(ret)
        return [c_isEnabled.value, c_defaultIsEnabled.value]
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks

    def nvml_device_set_auto_boosted_clocks_enabled(self, enabled: EnableState):
        fn = self.lib.get_function_pointer("nvmlDeviceSetAutoBoostedClocksEnabled")
        ret = fn(self.handle, enabled.as_c_type())
        Return.check(ret)
        return None
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks

    def nvml_device_set_default_auto_boosted_clocks_enabled(self, enabled, flags):
        fn = self.lib.get_function_pointer(
            "nvmlDeviceSetDefaultAutoBoostedClocksEnabled")
        ret = fn(self.handle, enabled.as_c_type(), c_uint(flags))
        Return.check(ret)
        return None
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks



    # Added in 4.304
    def nvml_device_reset_applications_clocks(self):
        fn = self.lib.get_function_pointer("nvmlDeviceResetApplicationsClocks")
        ret = fn(self.handle)
        Return.check(ret)
        return None





    # Added in 2.285
    def nvml_device_register_events(self, event_types, event_set):
        fn = self.lib.get_function_pointer("nvmlDeviceRegisterEvents")
        ret = fn(self.handle, c_ulonglong(event_types), event_set)
        Return.check(ret)
        return None

    # Added in 2.285
    def nvml_device_get_supported_event_types(self):
        c_eventTypes = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedEventTypes")
        ret = fn(self.handle, byref(c_eventTypes))
        Return.check(ret)
        return c_eventTypes.value

# Set functions
def nvmlUnitSetLedState(unit, color):
    fn = self.lib.get_function_pointer("nvmlUnitSetLedState")
    ret = fn(unit, Ledolor(color))
    Return.check(ret)
    return None

# Added in 2.285
# raises     ERROR_TIMEOUT exception on timeout
def nvmlEventSetWait(eventSet, timeoutms):
    fn = self.lib.get_function_pointer("nvmlEventSetWait")
    data = EventData()
    ret = fn(eventSet, byref(data), c_uint(timeoutms))
    Return.check(ret)
    return data

# Added in 2.285
def nvmlEventSetCreate():
    fn = self.lib.get_function_pointer("nvmlEventSetCreate")
    eventSet = EventType.C_TYPE()
    ret = fn(byref(eventSet))
    Return.check(ret)
    return eventSet

# Added in 2.285
def nvmlEventSetFree(eventSet):
    fn = self.lib.get_function_pointer("nvmlEventSetFree")
    ret = fn(eventSet)
    Return.check(ret)
    return None


# Added in 3.295
def nvmlDeviceOnSameBoard(handle1, handle2):
    fn = self.lib.get_function_pointer("nvmlDeviceOnSameBoard")
    onSameBoard = c_int()
    ret = fn(self.handle1, handle2, byref(onSameBoard))
    Return.check(ret)
    return (onSameBoard.value != 0)


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkGeneration(self):
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkGeneration")
    gen = c_uint()
    ret = fn(self.handle, byref(gen))
    Return.check(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkGeneration(self):
    fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkGeneration")
    gen = c_uint()
    ret = fn(self.handle, byref(gen))
    Return.check(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkWidth(self):
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkWidth")
    width = c_uint()
    ret = fn(self.handle, byref(width))
    Return.check(ret)
    return width.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkWidth(self):
    fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkWidth")
    width = c_uint()
    ret = fn(self.handle, byref(width))
    Return.check(ret)
    return width.value


# Added in 4.304
def nvmlDeviceGetSupportedClocksThrottleReasons(self):
    c_reasons = c_ulonglong()
    fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedClocksThrottleReasons")
    ret = fn(self.handle, byref(c_reasons))
    Return.check(ret)
    return c_reasons.value


# Added in 4.304
def nvmlDeviceGetCurrentClocksThrottleReasons(self):
    c_reasons = c_ulonglong()
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrentClocksThrottleReasons")
    ret = fn(self.handle, byref(c_reasons))
    Return.check(ret)
    return c_reasons.value


# Added in 5.319
def nvmlDeviceGetIndex(self):
    fn = self.lib.get_function_pointer("nvmlDeviceGetIndex")
    c_index = c_uint()
    ret = fn(self.handle, byref(c_index))
    Return.check(ret)
    return c_index.value


# Added in 5.319
def nvmlDeviceGetAccountingMode(self):
    _mode = EnableState()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingMode")
    ret = fn(self.handle, byref(c_mode))
    Return.check(ret)
    return c_mode.value


def nvmlDeviceSetAccountingMode(self, mode):
    fn = self.lib.get_function_pointer("nvmlDeviceSetAccountingMode")
    ret = fn(self.handle, EnableState.c_type(mode))
    Return.check(ret)
    return None


def nvmlDeviceClearAccountingPids(self):
    fn = self.lib.get_function_pointer("nvmlDeviceClearAccountingPids")
    ret = fn(self.handle)
    Return.check(ret)
    return None


def nvmlDeviceGetAccountingStats(self, pid):
    stats = AccountingStats()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingStats")
    ret = fn(self.handle, c_uint(pid), byref(stats))
    Return.check(ret)
    if (stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong):
        # special case for WDDM on Windows, see comment above
        stats.maxMemoryUsage = None
    return stats


def nvmlDeviceGetAccountingPids(self):
    count = c_uint(nvmlDeviceGetAccountingBufferSize(handle))
    pids = (c_uint * count.value)()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingPids")
    ret = fn(self.handle, byref(count), pids)
    Return.check(ret)
    return map(int, pids[0:count.value])


def nvmlDeviceGetAccountingBufferSize(self):
    bufferSize = c_uint()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingBufferSize")
    ret = fn(self.handle, byref(bufferSize))
    Return.check(ret)
    return int(bufferSize.value)


def nvmlDeviceGetRetiredPages(device, sourceFilter):
    _source = PageRetirementCause(sourceFilter)
    c_count = c_uint(0)
    fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPages")

    # First call will get the size
    ret = fn(device, c_source, byref(c_count), None)

    # this should only fail with insufficient size
    if ((ret != Return.SUCCESS.value) and
            (ret != ERROR_INSUFFICIENT_SIZE)):
        raise NVMLError(ret)

    # call again with a buffer
    # oversize the array for the rare cases where additional pages
    # are retired between NVML calls
    c_count.value = c_count.value * 2 + 5
    page_array = c_ulonglong * c_count.value
    c_pages = page_array()
    ret = fn(device, c_source, byref(c_count), c_pages)
    Return.check(ret)
    return map(int, c_pages[0:c_count.value])


def nvmlDeviceGetRetiredPagesPendingStatus(device):
    _pending = EnableState()
    fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPagesPendingStatus")
    ret = fn(device, byref(c_pending))
    Return.check(ret)
    return int(c_pending.value)


def nvmlDeviceGetAPIRestriction(device, apiType):
    _permission = EnableState()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAPIRestriction")
    ret = fn(devie, RestrictedAPI(apiType), byref(c_permission))
    Return.check(ret)
    return int(c_permission.value)

def nvmlDeviceGetBridgeChipInfo(self):
    bridgeHierarhy = cBridgeChipHierarchy()
    fn = self.lib.get_function_pointer("nvmlDeviceGetBridgeChipInfo")
    ret = fn(self.handle, byref(bridgeHierarchy))
    Return.check(ret)
    return bridgeHierarchy


def nvmlDeviceGetSamples(device, sampling_type, timeStamp):
    _sampling_type = SamplingType_t(samplingype)
    c_time_stamp = c_ulonglong(timeStamp)
    c_sample_count = c_uint(0)
    _sample_value_type = ValueType()
    fn = self.lib.get_function_pointer("nvmlDeviceGetSamples")

    # First Call gets the size
    ret = fn(
        device,
        c_sampling_type,
        c_time_stamp,
        byref(c_sample_value_type),
        byref(c_sample_count),
        None)

    # Stop if this fails
    if (ret != Return.SUCCESS.value):
        raise NVMLError(ret)

    sampleArray = _sample_count.value * cSample
    c_samples = sampleArray()
    ret = fn(
        device,
        c_sampling_type,
        c_time_stamp,
        byref(c_sample_value_type),
        byref(c_sample_count),
        c_samples)
    Return.check(ret)
    return (c_sample_value_type.value, c_samples[0:c_sample_count.value])


def nvmlDeviceGetViolationStatus(device, perfPolicyType):
    _perfPolicy_type = PerfPolicyType(perfPolicyType)
    _violTime = cViolationTime()
    fn = self.lib.get_function_pointer("nvmlDeviceGetViolationStatus")

    # Invoke the method to get violation time
    ret = fn(device, c_perfPolicy_type, byref(c_violTime))
    Return.check(ret)
    return c_violTime


def nvmlDeviceGetPcieThroughput(device, counter):
    c_util = c_uint()
    fn = self.lib.get_function_pointer("nvmlDeviceGetPcieThroughput")
    ret = fn(devie, PcieUtilCounter(counter), byref(c_util))
    Return.check(ret)
    return c_util.value


def nvmlSystemGetTopologyGpuSet(cpuNumber):
    c_count = c_uint(0)
    fn = self.lib.get_function_pointer("nvmlSystemGetTopologyGpuSet")

    # First call will get the size
    ret = fn(cpuNumber, byref(c_count), None)

    if ret != Return.SUCCESS.value:
        raise NVMLError(ret)
    print(c_count.value)
    # call again with a buffer
    devie_array = cDevice * c_count.value
    c_devices = device_array()
    ret = fn(cpuNumber, byref(c_count), c_devices)
    Return.check(ret)
    return map(None, c_devices[0:c_count.value])


def nvmlDeviceGetTopologyNearestGpus(device, level):
    c_count = c_uint(0)
    fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyNearestGpus")

    # First call will get the size
    ret = fn(device, level, byref(c_count), None)

    if ret != Return.SUCCESS.value:
        raise NVMLError(ret)

    # call again with a buffer
    devie_array = cDevice * c_count.value
    c_devices = device_array()
    ret = fn(device, level, byref(c_count), c_devices)
    Return.check(ret)
    return map(None, c_devices[0:c_count.value])


def nvmlDeviceGetTopologyCommonAncestor(device1, device2):
    _level = GpuTopologyLevel()
    fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyCommonAncestor")
    ret = fn(device1, device2, byref(c_level))
    Return.check(ret)
    return c_level.value


#################################
#        NvLink Methods         #
#################################


class NvLink:
    def __init__(self, device, link_id):
        self.device = device
        self.link = link_id

    def freeze_nv_link_utilization_counter(self, counter: int, freeze: EnableState) -> None:
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

    def nvmlDeviceGetNvLinkUtilizationCounter(self, link: int, counter: int):
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