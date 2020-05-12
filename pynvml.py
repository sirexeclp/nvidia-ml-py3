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
from errors import Return
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
        ret = fn(self.handle, cpu_set_size, byref(c_affinity))
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

    def nvmlDeviceGetDisplayActive(handle):
        _mode = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayActive")
        ret = fn(handle, byref(c_mode))
        Return.check(ret)
        return c_mode.value

    def nvmlDeviceGetPersistenceMode(handle):
        _state = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPersistenceMode")
        ret = fn(handle, byref(c_state))
        Return.check(ret)
        return c_state.value

    def nvmlDeviceGetPciInfo(handle):
        c_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPciInfo_v2")
        ret = fn(handle, byref(c_info))
        Return.check(ret)
        return c_info

    def nvmlDeviceGetClockInfo(handle, type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetClockInfo")
        ret = fn(handle, lockType(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 2.285
    def nvmlDeviceGetMaxClockInfo(handle, type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxClockInfo")
        ret = fn(handle, lockType(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def nvmlDeviceGetApplicationsClock(handle, type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetApplicationsClock")
        ret = fn(handle, lockType(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 5.319
    def nvmlDeviceGetDefaultApplicationsClock(handle, type):
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDefaultApplicationsClock")
        ret = fn(handle, lockType(type), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def nvmlDeviceGetSupportedMemoryClocks(handle):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedMemoryClocks")
        ret = fn(handle, byref(c_count), None)

        if (ret == Return.SUCCESS.value):
            # special case, no clocks
            return []
        elif (ret == ERROR_INSUFFICIENT_SIZE):
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(handle, byref(c_count), c_clocks)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                procs.append(c_clocks[i])

            return procs
        else:
            # error case
            raise NVMLError(ret)

    # Added in 4.304
    def nvmlDeviceGetSupportedGraphicsClocks(handle, memoryClockMHz):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedGraphicsClocks")
        ret = fn(handle, c_uint(memoryClockMHz), byref(c_count), None)

        if (ret == Return.SUCCESS.value):
            # special case, no clocks
            return []
        elif (ret == ERROR_INSUFFICIENT_SIZE):
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(handle, c_uint(memoryClockMHz), byref(c_count), c_clocks)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                procs.append(c_clocks[i])

            return procs
        else:
            # error case
            raise NVMLError(ret)

    def nvmlDeviceGetFanSpeed(handle):
        c_speed = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetFanSpeed")
        ret = fn(handle, byref(c_speed))
        Return.check(ret)
        return c_speed.value

    def nvmlDeviceGetTemperature(handle, sensor):
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperature")
        ret = fn(handle, TemperatureSensors_t(sensor), byref(emp))
        Return.check(ret)
        return c_temp.value

    def nvmlDeviceGetTemperatureThreshold(handle, threshold):
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperatureThreshold")
        ret = fn(handle, TemperatureThresholds_t(threshold), byref(emp))
        Return.check(ret)
        return c_temp.value

    # DEPRECATED use nvmlDeviceGetPerformanceState
    def nvmlDeviceGetPowerState(handle):
        _P = Ps()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerState")
        ret = fn(handle, byref(c_P))
        Return.check(ret)
        return c_P.value

    def nvmlDeviceGetPerformanceState(handle):
        _P = Ps()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPerformanceState")
        ret = fn(handle, byref(c_P))
        Return.check(ret)
        return c_P.value

    def nvmlDeviceGetPowerManagementMode(handle):
        _pcapMode = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementMode")
        ret = fn(handle, byref(c_pcapMode))
        Return.check(ret)
        return c_pcapMode.value

    def nvmlDeviceGetPowerManagementLimit(handle):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementLimit")
        ret = fn(handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 4.304
    def nvmlDeviceGetPowerManagementLimitConstraints(handle):
        c_minLimit = c_uint()
        c_maxLimit = c_uint()
        fn = self.lib.get_function_pointer(
            "nvmlDeviceGetPowerManagementLimitConstraints")
        ret = fn(handle, byref(c_minLimit), byref(c_maxLimit))
        Return.check(ret)
        return [c_minLimit.value, c_maxLimit.value]

    # Added in 4.304
    def nvmlDeviceGetPowerManagementDefaultLimit(handle):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementDefaultLimit")
        ret = fn(handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 331
    def nvmlDeviceGetEnforcedPowerLimit(handle):
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEnforcedPowerLimit")
        ret = fn(handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    def nvmlDeviceGetPowerUsage(handle):
        c_watts = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerUsage")
        ret = fn(handle, byref(c_watts))
        Return.check(ret)
        return c_watts.value

    # Added in 4.304
    def nvmlDeviceGetGpuOperationMode(handle):
        _currState = GpuOperationMode()
        _pendingState = GpuOperationMode()
        fn = self.lib.get_function_pointer("nvmlDeviceGetGpuOperationMode")
        ret = fn(handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return [c_currState.value, c_pendingState.value]

    # Added in 4.304
    def nvmlDeviceGetCurrentGpuOperationMode(handle):
        return nvmlDeviceGetGpuOperationMode(handle)[0]

    # Added in 4.304
    def nvmlDeviceGetPendingGpuOperationMode(handle):
        return nvmlDeviceGetGpuOperationMode(handle)[1]

    def nvmlDeviceGetMemoryInfo(handle):
        _memory = cMemory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryInfo")
        ret = fn(handle, byref(c_memory))
        Return.check(ret)
        return c_memory

    def nvmlDeviceGetBAR1MemoryInfo(handle):
        _bar1_memory = cBAR1Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBAR1MemoryInfo")
        ret = fn(handle, byref(c_bar1_memory))
        Return.check(ret)
        return c_bar1_memory

    def nvmlDeviceGetComputeMode(handle):
        _mode = ComputeMode()
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeMode")
        ret = fn(handle, byref(c_mode))
        Return.check(ret)
        return c_mode.value

    def nvmlDeviceGetEccMode(handle):
        _currState = EnableState()
        _pendingState = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEccMode")
        ret = fn(handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return [c_currState.value, c_pendingState.value]

    # added to API
    def nvmlDeviceGetCurrentEccMode(handle):
        return nvmlDeviceGetEccMode(handle)[0]

    # added to API
    def nvmlDeviceGetPendingEccMode(handle):
        return nvmlDeviceGetEccMode(handle)[1]

    def nvmlDeviceGetTotalEccErrors(handle, errorType, counterType):
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTotalEccErrors")
        ret = fn(handle, MemoryErrorType.c_type(errorType),
                 EcCounterType(counterType), byref(c_count))
        Return.check(ret)
        return c_count.value

    # This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
    def nvmlDeviceGetDetailedEccErrors(handle, errorType, counterType):
        _counts = cEccErrorCounts()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDetailedEccErrors")
        ret = fn(handle, MemoryErrorType.c_type(errorType),
                 EcCounterType(counterType), byref(c_counts))
        Return.check(ret)
        return c_counts

    # Added in 4.304
    def nvmlDeviceGetMemoryErrorCounter(
            handle,
            errorType,
            counterType,
            locationType):
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryErrorCounter")
        ret = fn(handle,
                 MemoryErrorType.c_type(errorType),
                 EcCounterType(counterType),
                 MemoryLoation(locationType),
                 byref(c_count))
        Return.check(ret)
        return c_count.value

    def nvmlDeviceGetUtilizationRates(handle):
        _util = cUtilization()
        fn = self.lib.get_function_pointer("nvmlDeviceGetUtilizationRates")
        ret = fn(handle, byref(c_util))
        Return.check(ret)
        return c_util

    def nvmlDeviceGetEncoderUtilization(handle):
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEncoderUtilization")
        ret = fn(handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return [c_util.value, c_samplingPeriod.value]

    def nvmlDeviceGetDecoderUtilization(handle):
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDecoderUtilization")
        ret = fn(handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return [c_util.value, c_samplingPeriod.value]

    def nvmlDeviceGetPcieReplayCounter(handle):
        c_replay = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieReplayCounter")
        ret = fn(handle, byref(c_replay))
        Return.check(ret)
        return c_replay.value

    def nvmlDeviceGetDriverModel(handle):
        _currModel = DriverModel()
        _pendingModel = DriverModel()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDriverModel")
        ret = fn(handle, byref(c_currModel), byref(c_pendingModel))
        Return.check(ret)
        return [c_currModel.value, c_pendingModel.value]

    # added to API
    def nvmlDeviceGetCurrentDriverModel(handle):
        return nvmlDeviceGetDriverModel(handle)[0]

    # added to API
    def nvmlDeviceGetPendingDriverModel(handle):
        return nvmlDeviceGetDriverModel(handle)[1]

    # Added in 2.285
    def nvmlDeviceGetVbiosVersion(handle):
        c_version = create_string_buffer(DEVICE_VBIOS_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetVbiosVersion")
        ret = fn(handle, c_version, c_uint(DEVICE_VBIOS_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value

    # Added in 2.285
    def nvmlDeviceGetComputeRunningProcesses(handle):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeRunningProcesses")
        ret = fn(handle, byref(c_count), None)

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
            ret = fn(handle, byref(c_count), c_procs)
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

    def nvmlDeviceGetGraphicsRunningProcesses(handle):
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetGraphicsRunningProcesses")
        ret = fn(handle, byref(c_count), None)

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
            ret = fn(handle, byref(c_count), c_procs)
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

    def nvmlDeviceGetAutoBoostedClocksEnabled(handle):
        _isEnabled = EnableState()
        _defaultIsEnabled = EnableState()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAutoBoostedClocksEnabled")
        ret = fn(handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
        Return.check(ret)
        return [c_isEnabled.value, c_defaultIsEnabled.value]
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks

    # Set functions
    def nvmlUnitSetLedState(unit, color):
        fn = self.lib.get_function_pointer("nvmlUnitSetLedState")
        ret = fn(unit, Ledolor(color))
        Return.check(ret)
        return None

    def nvmlDeviceSetPersistenceMode(handle, mode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetPersistenceMode")
        ret = fn(handle, EnableState.c_type(mode))
        Return.check(ret)
        return None

    def nvmlDeviceSetComputeMode(handle, mode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetComputeMode")
        ret = fn(handle, omputeMode(mode))
        Return.check(ret)
        return None

    def nvmlDeviceSetEccMode(handle, mode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetEccMode")
        ret = fn(handle, EnableState.c_type(mode))
        Return.check(ret)
        return None

    def nvmlDeviceClearEccErrorCounts(handle, counterType):
        fn = self.lib.get_function_pointer("nvmlDeviceClearEccErrorCounts")
        ret = fn(handle, EcCounterType(counterType))
        Return.check(ret)
        return None

    def nvmlDeviceSetDriverModel(handle, model):
        fn = self.lib.get_function_pointer("nvmlDeviceSetDriverModel")
        ret = fn(handle, DriverModel.c_type(model))
        Return.check(ret)
        return None

    def nvmlDeviceSetAutoBoostedClocksEnabled(handle, enabled):
        fn = self.lib.get_function_pointer("nvmlDeviceSetAutoBoostedClocksEnabled")
        ret = fn(handle, EnableState.c_type(enabled))
        Return.check(ret)
        return None
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks

    def nvmlDeviceSetDefaultAutoBoostedClocksEnabled(handle, enabled, flags):
        fn = self.lib.get_function_pointer(
            "nvmlDeviceSetDefaultAutoBoostedClocksEnabled")
        ret = fn(handle, EnableState.c_type(enabled), c_uint(flags))
        Return.check(ret)
        return None
        # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
        # boosted clocks

    # Added in 4.304
    def nvmlDeviceSetApplicationsClocks(handle, maxMemClockMHz, maxGraphicsClockMHz):
        fn = self.lib.get_function_pointer("nvmlDeviceSetApplicationsClocks")
        ret = fn(handle, c_uint(maxMemClockMHz), c_uint(maxGraphicsClockMHz))
        Return.check(ret)
        return None

    # Added in 4.304
    def nvmlDeviceResetApplicationsClocks(handle):
        fn = self.lib.get_function_pointer("nvmlDeviceResetApplicationsClocks")
        ret = fn(handle)
        Return.check(ret)
        return None

    # Added in 4.304
    def nvmlDeviceSetPowerManagementLimit(handle, limit):
        fn = self.lib.get_function_pointer("nvmlDeviceSetPowerManagementLimit")
        ret = fn(handle, c_uint(limit))
        Return.check(ret)
        return None

    # Added in 4.304
    def nvmlDeviceSetGpuOperationMode(handle, mode):
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuOperationMode")
        ret = fn(handle, GpuOperationMode.c_type(mode))
        Return.check(ret)
        return None

    # Added in 2.285
    def nvmlEventSetCreate():
        fn = self.lib.get_function_pointer("nvmlEventSetCreate")
        eventSet = EventType.C_TYPE()
        ret = fn(byref(eventSet))
        Return.check(ret)
        return eventSet

    # Added in 2.285
    def nvmlDeviceRegisterEvents(handle, eventTypes, eventSet):
        fn = self.lib.get_function_pointer("nvmlDeviceRegisterEvents")
        ret = fn(handle, c_ulonglong(eventTypes), eventSet)
        Return.check(ret)
        return None

    # Added in 2.285
    def nvmlDeviceGetSupportedEventTypes(handle):
        c_eventTypes = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedEventTypes")
        ret = fn(handle, byref(c_eventTypes))
        Return.check(ret)
        return c_eventTypes.value


# Added in 2.285
# raises     ERROR_TIMEOUT exception on timeout
def nvmlEventSetWait(eventSet, timeoutms):
    fn = self.lib.get_function_pointer("nvmlEventSetWait")
    data = EventData()
    ret = fn(eventSet, byref(data), c_uint(timeoutms))
    Return.check(ret)
    return data


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
    ret = fn(handle1, handle2, byref(onSameBoard))
    Return.check(ret)
    return (onSameBoard.value != 0)


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkGeneration(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    Return.check(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkGeneration(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    Return.check(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkWidth(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    Return.check(ret)
    return width.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkWidth(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    Return.check(ret)
    return width.value


# Added in 4.304
def nvmlDeviceGetSupportedClocksThrottleReasons(handle):
    c_reasons = c_ulonglong()
    fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedClocksThrottleReasons")
    ret = fn(handle, byref(c_reasons))
    Return.check(ret)
    return c_reasons.value


# Added in 4.304
def nvmlDeviceGetCurrentClocksThrottleReasons(handle):
    c_reasons = c_ulonglong()
    fn = self.lib.get_function_pointer("nvmlDeviceGetCurrentClocksThrottleReasons")
    ret = fn(handle, byref(c_reasons))
    Return.check(ret)
    return c_reasons.value


# Added in 5.319
def nvmlDeviceGetIndex(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceGetIndex")
    c_index = c_uint()
    ret = fn(handle, byref(c_index))
    Return.check(ret)
    return c_index.value


# Added in 5.319
def nvmlDeviceGetAccountingMode(handle):
    _mode = EnableState()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingMode")
    ret = fn(handle, byref(c_mode))
    Return.check(ret)
    return c_mode.value


def nvmlDeviceSetAccountingMode(handle, mode):
    fn = self.lib.get_function_pointer("nvmlDeviceSetAccountingMode")
    ret = fn(handle, EnableState.c_type(mode))
    Return.check(ret)
    return None


def nvmlDeviceClearAccountingPids(handle):
    fn = self.lib.get_function_pointer("nvmlDeviceClearAccountingPids")
    ret = fn(handle)
    Return.check(ret)
    return None


def nvmlDeviceGetAccountingStats(handle, pid):
    stats = AccountingStats()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingStats")
    ret = fn(handle, c_uint(pid), byref(stats))
    Return.check(ret)
    if (stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong):
        # special case for WDDM on Windows, see comment above
        stats.maxMemoryUsage = None
    return stats


def nvmlDeviceGetAccountingPids(handle):
    count = c_uint(nvmlDeviceGetAccountingBufferSize(handle))
    pids = (c_uint * count.value)()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingPids")
    ret = fn(handle, byref(count), pids)
    Return.check(ret)
    return map(int, pids[0:count.value])


def nvmlDeviceGetAccountingBufferSize(handle):
    bufferSize = c_uint()
    fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingBufferSize")
    ret = fn(handle, byref(bufferSize))
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


def nvmlDeviceSetAPIRestriction(handle, apiType, isRestricted):
    fn = self.lib.get_function_pointer("nvmlDeviceSetAPIRestriction")
    ret = fn(handle, RestrictedAPI_t(apiType),
             EnableState.YPE(isRestricted))
    Return.check(ret)
    return None


def nvmlDeviceGetBridgeChipInfo(handle):
    bridgeHierarhy = cBridgeChipHierarchy()
    fn = self.lib.get_function_pointer("nvmlDeviceGetBridgeChipInfo")
    ret = fn(handle, byref(bridgeHierarchy))
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
