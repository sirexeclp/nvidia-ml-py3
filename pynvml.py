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
from errors import *
from structs import *
from flags import *


def _nvmlCheckReturn(ret):
    if ret != Return.SUCCESS.value:
        raise NVMLError.from_return(ret)
    return ret


class NVMLLib:
    lock = threading.Lock()
    refcount = 0

    def __init__(self):
        self.function_pointer_cache = {}
        self.nvml_lib = None
        self._load_nvml_library()

    def __enter__(self):
        # Initialize the library
        fn = self._get_function_pointer("nvmlInit_v2")
        ret = fn()
        _nvmlCheckReturn(ret)

        # Atomically update refcount
        with self.lock:
            self.refcount += 1

    def __exit__(self, *argc, **kwargs):
        # Leave the library loaded, but shutdown the interface
        fn = self._get_function_pointer("nvmlShutdown")
        ret = fn()
        _nvmlCheckReturn(ret)

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
                        _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)
                    else:
                        # cdecl calling convention
                        self.nvml_lib = CDLL(str(nvml_path))
                else:
                    # assume linux
                    self.nvml_lib = CDLL("libnvidia-ml.so.1")
            except OSError as ose:
                _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)
            if self.nvml_lib is None:
                _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)

    @staticmethod
    def _get_search_paths(self):
        program_files = Path(os.getenv("ProgramFiles", r"C:\Program Files"))
        win_dir = Path(os.getenv("WinDir", r"C:\Windows"))
        paths = [program_files / r"NVIDIA Corporation\NVSMI\nvml.dll",
                 win_dir / r"System32\nvml.dll"]
        return paths

    def _get_function_pointer(self, name):
        if name in self.function_pointer_cache:
            return self.function_pointer_cache[name]

        with self.lock:
            try:
                self.function_pointer_cache[name] = getattr(nvmlLib, name)
                return self.function_pointer_cache[name]
            except AttributeError:
                raise NVMLError(ERROR_FUNCTION_NOT_FOUND)


# Alternative object
# Allows the object to be printed
# Allows mismatched types to be assigned
#  - like None when the Structure variant requires c_uint
class nvmlFriendlyObject(object):
    def __init__(self, dictionary):
        for x in dictionary:
            setattr(self, x, dictionary[x])

    def __str__(self):
        return self.__dict__.__str__()


def nvmlStructToFriendlyObject(struct):
    d = {}
    for x in struct._fields_:
        key = x[0]
        value = getattr(struct, key)
        d[key] = value
    obj = nvmlFriendlyObject(d)
    return obj


# pack the object so it can be passed to the NVML library
def nvmlFriendlyObjectToStruct(obj, model):
    for x in model._fields_:
        key = x[0]
        value = obj.__dict__[key]
        setattr(model, key, value)
    return model


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


# Added in 2.285
def nvmlErrorString(result):
    fn = _nvmlGetFunctionPointer("nvmlErrorString")
    fn.restype = c_char_p  # otherwise return is an int
    ret = fn(result)
    return ret


# Added in 2.285
def nvmlSystemGetNVMLVersion():
    c_version = create_string_buffer(SYSTEM_NVML_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetNVMLVersion")
    ret = fn(c_version, c_uint(SYSTEM_NVML_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value


# Added in 2.285
def nvmlSystemGetProcessName(pid):
    c_name = create_string_buffer(1024)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetProcessName")
    ret = fn(c_uint(pid), c_name, c_uint(1024))
    _nvmlCheckReturn(ret)
    return c_name.value


def nvmlSystemGetDriverVersion():
    c_version = create_string_buffer(SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetDriverVersion")
    ret = fn(c_version, c_uint(SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value


# Added in 2.285
def nvmlSystemGetHicVersion():
    c_count = c_uint(0)
    hics = None
    fn = _nvmlGetFunctionPointer("nvmlSystemGetHicVersion")

    # get the count
    ret = fn(byref(c_count), None)

    # this should only fail with insufficient size
    if ((ret != Return.SUCCESS.value) and
            (ret != ERROR_INSUFFICIENT_SIZE)):
        raise NVMLError(ret)

    # if there are no hics
    if c_count.value == 0:
        return []

    hi_array = cHwbcEntry * c_count.value
    hics = hic_array()
    ret = fn(byref(c_count), hics)
    _nvmlCheckReturn(ret)
    return hics


# Unit get functions
def nvmlUnitGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlUnitGetHandleByIndex(index):
    c_index = c_uint(index)
    unit = UnitPointer()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetHandleByIndex")
    ret = fn(c_index, byref(unit))
    _nvmlCheckReturn(ret)
    return unit


def nvmlUnitGetUnitInfo(unit):
    _info = cUnitInfo()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetUnitInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info


def nvmlUnitGetLedState(unit):
    _state = cLedState()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetLedState")
    ret = fn(unit, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state


def nvmlUnitGetPsuInfo(unit):
    _info = cPSUInfo()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetPsuInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info


def nvmlUnitGetTemperature(unit, type):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetTemperature")
    ret = fn(unit, c_uint(type), byref(c_temp))
    _nvmlCheckReturn(ret)
    return c_temp.value


def nvmlUnitGetFanSpeedInfo(unit):
    _speeds = cUnitFanSpeeds()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetFanSpeedInfo")
    ret = fn(unit, byref(c_speeds))
    _nvmlCheckReturn(ret)
    return c_speeds


# added to API
def nvmlUnitGetDeviceCount(unit):
    c_count = c_uint(0)
    # query the unit to determine device count
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), None)
    if ret == ERROR_INSUFFICIENT_SIZE:
        ret = Return.SUCCESS.value
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlUnitGetDevices(unit):
    c_count = c_uint(nvmlUnitGetDeviceCount(unit))
    devie_array = cDevice * c_count.value
    c_devices = device_array()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return c_devices


# Device get functions
def nvmlDeviceGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCount_v2")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlDeviceGetHandleByIndex(index):
    c_index = c_uint(index)
    device = cDevice()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByIndex_v2")
    ret = fn(c_index, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleBySerial(serial):
    c_serial = c_char_p(serial)
    devie = cDevice()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleBySerial")
    ret = fn(c_serial, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleByUUID(uuid):
    c_uuid = c_char_p(uuid)
    devie = cDevice()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByUUID")
    ret = fn(c_uuid, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleByPciBusId(pciBusId):
    c_busId = c_char_p(pciBusId)
    devie = cDevice()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByPciBusId_v2")
    ret = fn(c_busId, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetName(handle):
    c_name = create_string_buffer(DEVICE_NAME_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetName")
    ret = fn(handle, c_name, c_uint(DEVICE_NAME_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_name.value


def nvmlDeviceGetBoardId(handle):
    c_id = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBoardId")
    ret = fn(handle, byref(c_id))
    _nvmlCheckReturn(ret)
    return c_id.value


def nvmlDeviceGetMultiGpuBoard(handle):
    c_multiGpu = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMultiGpuBoard")
    ret = fn(handle, byref(c_multiGpu))
    _nvmlCheckReturn(ret)
    return c_multiGpu.value


def nvmlDeviceGetBrand(handle):
    _type = BrandType()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBrand")
    ret = fn(handle, byref(c_type))
    _nvmlCheckReturn(ret)
    return c_type.value


def nvmlDeviceGetSerial(handle):
    c_serial = create_string_buffer(DEVICE_SERIAL_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSerial")
    ret = fn(handle, c_serial, c_uint(DEVICE_SERIAL_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_serial.value


def nvmlDeviceGetCpuAffinity(handle, cpu_set_size):
    affinity_array = c_ulonglong * cpu_set_size
    c_affinity = affinity_array()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCpuAffinity")
    ret = fn(handle, cpu_set_size, byref(c_affinity))
    _nvmlCheckReturn(ret)
    return c_affinity


def nvmlDeviceSetCpuAffinity(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetCpuAffinity")
    ret = fn(handle)
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceClearCpuAffinity(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearCpuAffinity")
    ret = fn(handle)
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceGetMinorNumber(handle):
    c_minor_number = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMinorNumber")
    ret = fn(handle, byref(c_minor_number))
    _nvmlCheckReturn(ret)
    return c_minor_number.value


def nvmlDeviceGetUUID(handle):
    c_uuid = create_string_buffer(DEVICE_UUID_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUUID")
    ret = fn(handle, c_uuid, c_uint(DEVICE_UUID_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_uuid.value


def nvmlDeviceGetInforomVersion(handle, info_rom_object: InforomObject):
    c_version = create_string_buffer(DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomVersion")
    ret = fn(handle, InforomObjet(info_rom_object.value),
             c_version, c_uint(DEVICE_INFOROM_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value


# Added in 4.304
def nvmlDeviceGetInforomImageVersion(handle):
    c_version = create_string_buffer(DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomImageVersion")
    ret = fn(handle, c_version, c_uint(DEVICE_INFOROM_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value


# Added in 4.304
def nvmlDeviceGetInforomConfigurationChecksum(handle):
    c_checksum = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomConfigurationChecksum")
    ret = fn(handle, byref(c_checksum))
    _nvmlCheckReturn(ret)
    return c_checksum.value


# Added in 4.304
def nvmlDeviceValidateInforom(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceValidateInforom")
    ret = fn(handle)
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceGetDisplayMode(handle):
    _mode = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetDisplayActive(handle):
    _mode = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayActive")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetPersistenceMode(handle):
    _state = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPersistenceMode")
    ret = fn(handle, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state.value


def nvmlDeviceGetPciInfo(handle):
    c_info = PciInfo()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPciInfo_v2")
    ret = fn(handle, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info


def nvmlDeviceGetClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetClockInfo")
    ret = fn(handle, lockType(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 2.285
def nvmlDeviceGetMaxClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxClockInfo")
    ret = fn(handle, lockType(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 4.304
def nvmlDeviceGetApplicationsClock(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetApplicationsClock")
    ret = fn(handle, lockType(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 5.319
def nvmlDeviceGetDefaultApplicationsClock(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDefaultApplicationsClock")
    ret = fn(handle, lockType(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 4.304
def nvmlDeviceGetSupportedMemoryClocks(handle):
    # first call to get the size
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedMemoryClocks")
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
        _nvmlCheckReturn(ret)

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
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedGraphicsClocks")
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
        _nvmlCheckReturn(ret)

        procs = []
        for i in range(c_count.value):
            procs.append(c_clocks[i])

        return procs
    else:
        # error case
        raise NVMLError(ret)


def nvmlDeviceGetFanSpeed(handle):
    c_speed = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetFanSpeed")
    ret = fn(handle, byref(c_speed))
    _nvmlCheckReturn(ret)
    return c_speed.value


def nvmlDeviceGetTemperature(handle, sensor):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTemperature")
    ret = fn(handle, TemperatureSensors_t(sensor), byref(emp))
    _nvmlCheckReturn(ret)
    return c_temp.value


def nvmlDeviceGetTemperatureThreshold(handle, threshold):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTemperatureThreshold")
    ret = fn(handle, TemperatureThresholds_t(threshold), byref(emp))
    _nvmlCheckReturn(ret)
    return c_temp.value


# DEPRECATED use nvmlDeviceGetPerformanceState
def nvmlDeviceGetPowerState(handle):
    _P = Ps()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerState")
    ret = fn(handle, byref(c_P))
    _nvmlCheckReturn(ret)
    return c_P.value


def nvmlDeviceGetPerformanceState(handle):
    _P = Ps()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPerformanceState")
    ret = fn(handle, byref(c_P))
    _nvmlCheckReturn(ret)
    return c_P.value


def nvmlDeviceGetPowerManagementMode(handle):
    _pcapMode = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementMode")
    ret = fn(handle, byref(c_pcapMode))
    _nvmlCheckReturn(ret)
    return c_pcapMode.value


def nvmlDeviceGetPowerManagementLimit(handle):
    c_limit = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementLimit")
    ret = fn(handle, byref(c_limit))
    _nvmlCheckReturn(ret)
    return c_limit.value


# Added in 4.304
def nvmlDeviceGetPowerManagementLimitConstraints(handle):
    c_minLimit = c_uint()
    c_maxLimit = c_uint()
    fn = _nvmlGetFunctionPointer(
        "nvmlDeviceGetPowerManagementLimitConstraints")
    ret = fn(handle, byref(c_minLimit), byref(c_maxLimit))
    _nvmlCheckReturn(ret)
    return [c_minLimit.value, c_maxLimit.value]


# Added in 4.304
def nvmlDeviceGetPowerManagementDefaultLimit(handle):
    c_limit = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementDefaultLimit")
    ret = fn(handle, byref(c_limit))
    _nvmlCheckReturn(ret)
    return c_limit.value


# Added in 331
def nvmlDeviceGetEnforcedPowerLimit(handle):
    c_limit = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetEnforcedPowerLimit")
    ret = fn(handle, byref(c_limit))
    _nvmlCheckReturn(ret)
    return c_limit.value


def nvmlDeviceGetPowerUsage(handle):
    c_watts = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerUsage")
    ret = fn(handle, byref(c_watts))
    _nvmlCheckReturn(ret)
    return c_watts.value


# Added in 4.304
def nvmlDeviceGetGpuOperationMode(handle):
    _currState = GpuOperationMode()
    _pendingState = GpuOperationMode()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetGpuOperationMode")
    ret = fn(handle, byref(c_currState), byref(c_pendingState))
    _nvmlCheckReturn(ret)
    return [c_currState.value, c_pendingState.value]


# Added in 4.304
def nvmlDeviceGetCurrentGpuOperationMode(handle):
    return nvmlDeviceGetGpuOperationMode(handle)[0]


# Added in 4.304
def nvmlDeviceGetPendingGpuOperationMode(handle):
    return nvmlDeviceGetGpuOperationMode(handle)[1]


def nvmlDeviceGetMemoryInfo(handle):
    _memory = cMemory()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryInfo")
    ret = fn(handle, byref(c_memory))
    _nvmlCheckReturn(ret)
    return c_memory


def nvmlDeviceGetBAR1MemoryInfo(handle):
    _bar1_memory = cBAR1Memory()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBAR1MemoryInfo")
    ret = fn(handle, byref(c_bar1_memory))
    _nvmlCheckReturn(ret)
    return c_bar1_memory


def nvmlDeviceGetComputeMode(handle):
    _mode = ComputeMode()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetEccMode(handle):
    _currState = EnableState()
    _pendingState = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetEccMode")
    ret = fn(handle, byref(c_currState), byref(c_pendingState))
    _nvmlCheckReturn(ret)
    return [c_currState.value, c_pendingState.value]


# added to API
def nvmlDeviceGetCurrentEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[0]


# added to API
def nvmlDeviceGetPendingEccMode(handle):
    return nvmlDeviceGetEccMode(handle)[1]


def nvmlDeviceGetTotalEccErrors(handle, errorType, counterType):
    c_count = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTotalEccErrors")
    ret = fn(handle, MemoryErrorType.C_TYPE(errorType),
             EcCounterType(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


# This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
def nvmlDeviceGetDetailedEccErrors(handle, errorType, counterType):
    _counts = cEccErrorCounts()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDetailedEccErrors")
    ret = fn(handle, MemoryErrorType.C_TYPE(errorType),
             EcCounterType(counterType), byref(c_counts))
    _nvmlCheckReturn(ret)
    return c_counts


# Added in 4.304
def nvmlDeviceGetMemoryErrorCounter(
        handle,
        errorType,
        counterType,
        locationType):
    c_count = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryErrorCounter")
    ret = fn(handle,
             MemoryErrorType.C_TYPE(errorType),
             EcCounterType(counterType),
             MemoryLoation(locationType),
             byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlDeviceGetUtilizationRates(handle):
    _util = cUtilization()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetUtilizationRates")
    ret = fn(handle, byref(c_util))
    _nvmlCheckReturn(ret)
    return c_util


def nvmlDeviceGetEncoderUtilization(handle):
    c_util = c_uint()
    c_samplingPeriod = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetEncoderUtilization")
    ret = fn(handle, byref(c_util), byref(c_samplingPeriod))
    _nvmlCheckReturn(ret)
    return [c_util.value, c_samplingPeriod.value]


def nvmlDeviceGetDecoderUtilization(handle):
    c_util = c_uint()
    c_samplingPeriod = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDecoderUtilization")
    ret = fn(handle, byref(c_util), byref(c_samplingPeriod))
    _nvmlCheckReturn(ret)
    return [c_util.value, c_samplingPeriod.value]


def nvmlDeviceGetPcieReplayCounter(handle):
    c_replay = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPcieReplayCounter")
    ret = fn(handle, byref(c_replay))
    _nvmlCheckReturn(ret)
    return c_replay.value


def nvmlDeviceGetDriverModel(handle):
    _currModel = DriverModel()
    _pendingModel = DriverModel()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDriverModel")
    ret = fn(handle, byref(c_currModel), byref(c_pendingModel))
    _nvmlCheckReturn(ret)
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
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetVbiosVersion")
    ret = fn(handle, c_version, c_uint(DEVICE_VBIOS_VERSION_BUFFER_SIZE))
    _nvmlCheckReturn(ret)
    return c_version.value


# Added in 2.285
def nvmlDeviceGetComputeRunningProcesses(handle):
    # first call to get the size
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeRunningProcesses")
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
        _nvmlCheckReturn(ret)

        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
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
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetGraphicsRunningProcesses")
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
        _nvmlCheckReturn(ret)

        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
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
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAutoBoostedClocksEnabled")
    ret = fn(handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
    _nvmlCheckReturn(ret)
    return [c_isEnabled.value, c_defaultIsEnabled.value]
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
    # boosted clocks


# Set functions
def nvmlUnitSetLedState(unit, color):
    fn = _nvmlGetFunctionPointer("nvmlUnitSetLedState")
    ret = fn(unit, Ledolor(color))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetPersistenceMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetPersistenceMode")
    ret = fn(handle, EnableState.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetComputeMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetComputeMode")
    ret = fn(handle, omputeMode(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetEccMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetEccMode")
    ret = fn(handle, EnableState.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceClearEccErrorCounts(handle, counterType):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearEccErrorCounts")
    ret = fn(handle, EcCounterType(counterType))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetDriverModel(handle, model):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetDriverModel")
    ret = fn(handle, DriverModel.C_TYPE(model))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetAutoBoostedClocksEnabled(handle, enabled):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetAutoBoostedClocksEnabled")
    ret = fn(handle, EnableState.C_TYPE(enabled))
    _nvmlCheckReturn(ret)
    return None
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
    # boosted clocks


def nvmlDeviceSetDefaultAutoBoostedClocksEnabled(handle, enabled, flags):
    fn = _nvmlGetFunctionPointer(
        "nvmlDeviceSetDefaultAutoBoostedClocksEnabled")
    ret = fn(handle, EnableState.C_TYPE(enabled), c_uint(flags))
    _nvmlCheckReturn(ret)
    return None
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto
    # boosted clocks


# Added in 4.304
def nvmlDeviceSetApplicationsClocks(handle, maxMemClockMHz, maxGraphicsClockMHz):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetApplicationsClocks")
    ret = fn(handle, c_uint(maxMemClockMHz), c_uint(maxGraphicsClockMHz))
    _nvmlCheckReturn(ret)
    return None


# Added in 4.304
def nvmlDeviceResetApplicationsClocks(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceResetApplicationsClocks")
    ret = fn(handle)
    _nvmlCheckReturn(ret)
    return None


# Added in 4.304
def nvmlDeviceSetPowerManagementLimit(handle, limit):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetPowerManagementLimit")
    ret = fn(handle, c_uint(limit))
    _nvmlCheckReturn(ret)
    return None


# Added in 4.304
def nvmlDeviceSetGpuOperationMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetGpuOperationMode")
    ret = fn(handle, GpuOperationMode.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


# Added in 2.285
def nvmlEventSetCreate():
    fn = _nvmlGetFunctionPointer("nvmlEventSetCreate")
    eventSet = EventType.C_TYPE()
    ret = fn(byref(eventSet))
    _nvmlCheckReturn(ret)
    return eventSet


# Added in 2.285
def nvmlDeviceRegisterEvents(handle, eventTypes, eventSet):
    fn = _nvmlGetFunctionPointer("nvmlDeviceRegisterEvents")
    ret = fn(handle, c_ulonglong(eventTypes), eventSet)
    _nvmlCheckReturn(ret)
    return None


# Added in 2.285
def nvmlDeviceGetSupportedEventTypes(handle):
    c_eventTypes = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedEventTypes")
    ret = fn(handle, byref(c_eventTypes))
    _nvmlCheckReturn(ret)
    return c_eventTypes.value


# Added in 2.285
# raises     ERROR_TIMEOUT exception on timeout
def nvmlEventSetWait(eventSet, timeoutms):
    fn = _nvmlGetFunctionPointer("nvmlEventSetWait")
    data = EventData()
    ret = fn(eventSet, byref(data), c_uint(timeoutms))
    _nvmlCheckReturn(ret)
    return data


# Added in 2.285
def nvmlEventSetFree(eventSet):
    fn = _nvmlGetFunctionPointer("nvmlEventSetFree")
    ret = fn(eventSet)
    _nvmlCheckReturn(ret)
    return None


# Added in 3.295
def nvmlDeviceOnSameBoard(handle1, handle2):
    fn = _nvmlGetFunctionPointer("nvmlDeviceOnSameBoard")
    onSameBoard = c_int()
    ret = fn(handle1, handle2, byref(onSameBoard))
    _nvmlCheckReturn(ret)
    return (onSameBoard.value != 0)


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkGeneration(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkGeneration")
    gen = c_uint()
    ret = fn(handle, byref(gen))
    _nvmlCheckReturn(ret)
    return gen.value


# Added in 3.295
def nvmlDeviceGetCurrPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value


# Added in 3.295
def nvmlDeviceGetMaxPcieLinkWidth(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxPcieLinkWidth")
    width = c_uint()
    ret = fn(handle, byref(width))
    _nvmlCheckReturn(ret)
    return width.value


# Added in 4.304
def nvmlDeviceGetSupportedClocksThrottleReasons(handle):
    c_reasons = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSupportedClocksThrottleReasons")
    ret = fn(handle, byref(c_reasons))
    _nvmlCheckReturn(ret)
    return c_reasons.value


# Added in 4.304
def nvmlDeviceGetCurrentClocksThrottleReasons(handle):
    c_reasons = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCurrentClocksThrottleReasons")
    ret = fn(handle, byref(c_reasons))
    _nvmlCheckReturn(ret)
    return c_reasons.value


# Added in 5.319
def nvmlDeviceGetIndex(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetIndex")
    c_index = c_uint()
    ret = fn(handle, byref(c_index))
    _nvmlCheckReturn(ret)
    return c_index.value


# Added in 5.319
def nvmlDeviceGetAccountingMode(handle):
    _mode = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAccountingMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceSetAccountingMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetAccountingMode")
    ret = fn(handle, EnableState.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceClearAccountingPids(handle):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearAccountingPids")
    ret = fn(handle)
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceGetAccountingStats(handle, pid):
    stats = AccountingStats()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAccountingStats")
    ret = fn(handle, c_uint(pid), byref(stats))
    _nvmlCheckReturn(ret)
    if (stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong):
        # special case for WDDM on Windows, see comment above
        stats.maxMemoryUsage = None
    return stats


def nvmlDeviceGetAccountingPids(handle):
    count = c_uint(nvmlDeviceGetAccountingBufferSize(handle))
    pids = (c_uint * count.value)()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAccountingPids")
    ret = fn(handle, byref(count), pids)
    _nvmlCheckReturn(ret)
    return map(int, pids[0:count.value])


def nvmlDeviceGetAccountingBufferSize(handle):
    bufferSize = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAccountingBufferSize")
    ret = fn(handle, byref(bufferSize))
    _nvmlCheckReturn(ret)
    return int(bufferSize.value)


def nvmlDeviceGetRetiredPages(device, sourceFilter):
    _source = PageRetirementCause(sourceFilter)
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetRetiredPages")

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
    _nvmlCheckReturn(ret)
    return map(int, c_pages[0:c_count.value])


def nvmlDeviceGetRetiredPagesPendingStatus(device):
    _pending = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetRetiredPagesPendingStatus")
    ret = fn(device, byref(c_pending))
    _nvmlCheckReturn(ret)
    return int(c_pending.value)


def nvmlDeviceGetAPIRestriction(device, apiType):
    _permission = EnableState()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAPIRestriction")
    ret = fn(devie, RestrictedAPI(apiType), byref(c_permission))
    _nvmlCheckReturn(ret)
    return int(c_permission.value)


def nvmlDeviceSetAPIRestriction(handle, apiType, isRestricted):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetAPIRestriction")
    ret = fn(handle, RestrictedAPI_t(apiType),
             EnableState.YPE(isRestricted))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceGetBridgeChipInfo(handle):
    bridgeHierarhy = cBridgeChipHierarchy()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBridgeChipInfo")
    ret = fn(handle, byref(bridgeHierarchy))
    _nvmlCheckReturn(ret)
    return bridgeHierarchy


def nvmlDeviceGetSamples(device, sampling_type, timeStamp):
    _sampling_type = SamplingType_t(samplingype)
    c_time_stamp = c_ulonglong(timeStamp)
    c_sample_count = c_uint(0)
    _sample_value_type = ValueType()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSamples")

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
    _nvmlCheckReturn(ret)
    return (c_sample_value_type.value, c_samples[0:c_sample_count.value])


def nvmlDeviceGetViolationStatus(device, perfPolicyType):
    _perfPolicy_type = PerfPolicyType(perfPolicyType)
    _violTime = cViolationTime()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetViolationStatus")

    # Invoke the method to get violation time
    ret = fn(device, c_perfPolicy_type, byref(c_violTime))
    _nvmlCheckReturn(ret)
    return c_violTime


def nvmlDeviceGetPcieThroughput(device, counter):
    c_util = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPcieThroughput")
    ret = fn(devie, PcieUtilCounter(counter), byref(c_util))
    _nvmlCheckReturn(ret)
    return c_util.value


def nvmlSystemGetTopologyGpuSet(cpuNumber):
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlSystemGetTopologyGpuSet")

    # First call will get the size
    ret = fn(cpuNumber, byref(c_count), None)

    if ret != Return.SUCCESS.value:
        raise NVMLError(ret)
    print(c_count.value)
    # call again with a buffer
    devie_array = cDevice * c_count.value
    c_devices = device_array()
    ret = fn(cpuNumber, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return map(None, c_devices[0:c_count.value])


def nvmlDeviceGetTopologyNearestGpus(device, level):
    c_count = c_uint(0)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTopologyNearestGpus")

    # First call will get the size
    ret = fn(device, level, byref(c_count), None)

    if ret != Return.SUCCESS.value:
        raise NVMLError(ret)

    # call again with a buffer
    devie_array = cDevice * c_count.value
    c_devices = device_array()
    ret = fn(device, level, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return map(None, c_devices[0:c_count.value])


def nvmlDeviceGetTopologyCommonAncestor(device1, device2):
    _level = GpuTopologyLevel()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTopologyCommonAncestor")
    ret = fn(device1, device2, byref(c_level))
    _nvmlCheckReturn(ret)
    return c_level.value
