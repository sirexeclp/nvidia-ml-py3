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
from ctypes.util import find_library
import sys
import os
import threading
import string

## C Type mappings ##
## Enums
from enum import Enum, IntFlag


class UIntEnum(Enum):
    C_TYPE = c_uint


class EnableState(UIntEnum):
    FEATURE_DISABLED = 0
    FEATURE_ENABLED = 1


class BrandType(UIntEnum):
    BRAND_UNKNOWN = 0
    BRAND_QUADRO = 1
    BRAND_TESLA = 2
    BRAND_NVS = 3
    BRAND_GRID = 4
    BRAND_GEFORCE = 5
    BRAND_COUNT = 6


class TemperatureThresholds(UIntEnum):
    TEMPERATURE_THRESHOLD_SHUTDOWN = 0
    TEMPERATURE_THRESHOLD_SLOWDOWN = 1
    TEMPERATURE_THRESHOLD_COUNT = 1


class TemperatureSensors(UIntEnum):
    TEMPERATURE_GPU = 0
    TEMPERATURE_COUNT = 1


class ComputeMode(UIntEnum):
    COMPUTEMODE_DEFAULT = 0
    COMPUTEMODE_EXCLUSIVE_THREAD = 1
    COMPUTEMODE_PROHIBITED = 2
    COMPUTEMODE_EXCLUSIVE_PROCESS = 3
    COMPUTEMODE_COUNT = 4


class MemoryLocation(UIntEnum):
    MEMORY_LOCATION_L1_CACHE = 0
    MEMORY_LOCATION_L2_CACHE = 1
    MEMORY_LOCATION_DEVICE_MEMORY = 2
    MEMORY_LOCATION_REGISTER_FILE = 3
    MEMORY_LOCATION_TEXTURE_MEMORY = 4
    MEMORY_LOCATION_COUNT = 5


# These are deprecated, instead use MemoryErrorType.C_TYPE
class EccBitType(UIntEnum):
    SINGLE_BIT_ECC = 0
    DOUBLE_BIT_ECC = 1
    ECC_ERROR_TYPE_COUNT = 2


class EccCounterType(UIntEnum):
    VOLATILE_ECC = 0
    AGGREGATE_ECC = 1
    ECC_COUNTER_TYPE_COUNT = 2


class MemoryErrorType(UIntEnum):
    MEMORY_ERROR_TYPE_CORRECTED = 0
    MEMORY_ERROR_TYPE_UNCORRECTED = 1
    MEMORY_ERROR_TYPE_COUNT = 2


class ClockType(UIntEnum):
    CLOCK_GRAPHICS = 0
    CLOCK_SM = 1
    CLOCK_MEM = 2
    CLOCK_COUNT = 3


class DriverModel(UIntEnum):
    DRIVER_WDDM = 0
    DRIVER_WDM = 1


class Pstates(UIntEnum):
    PSTATE_0 = 0
    PSTATE_1 = 1
    PSTATE_2 = 2
    PSTATE_3 = 3
    PSTATE_4 = 4
    PSTATE_5 = 5
    PSTATE_6 = 6
    PSTATE_7 = 7
    PSTATE_8 = 8
    PSTATE_9 = 9
    PSTATE_10 = 10
    PSTATE_11 = 11
    PSTATE_12 = 12
    PSTATE_13 = 13
    PSTATE_14 = 14
    PSTATE_15 = 15
    PSTATE_UNKNOWN = 32


class InforomObject(UIntEnum):
    INFOROM_OEM = 0
    INFOROM_ECC = 1
    INFOROM_POWER = 2
    INFOROM_COUNT = 3


class Return(UIntEnum):
    SUCCESS = 0
    ERROR_UNINITIALIZED = 1
    ERROR_INVALID_ARGUMENT = 2
    ERROR_NOT_SUPPORTED = 3
    ERROR_NO_PERMISSION = 4
    ERROR_ALREADY_INITIALIZED = 5
    ERROR_NOT_FOUND = 6
    ERROR_INSUFFICIENT_SIZE = 7
    ERROR_INSUFFICIENT_POWER = 8
    ERROR_DRIVER_NOT_LOADED = 9
    ERROR_TIMEOUT = 10
    ERROR_IRQ_ISSUE = 11
    ERROR_LIBRARY_NOT_FOUND = 12
    ERROR_FUNCTION_NOT_FOUND = 13
    ERROR_CORRUPTED_INFOROM = 14
    ERROR_GPU_IS_LOST = 15
    ERROR_RESET_REQUIRED = 16
    ERROR_OPERATING_SYSTEM = 17
    ERROR_LIB_RM_VERSION_MISMATCH = 18
    ERROR_UNKNOWN = 999


class FanState(UIntEnum):
    FAN_NORMAL = 0
    FAN_FAILED = 1


class LedColor(UIntEnum):
    LED_COLOR_GREEN = 0
    LED_COLOR_AMBER = 1


class GpuOperationMode(UIntEnum):
    GOM_ALL_ON = 0
    GOM_COMPUTE = 1
    GOM_LOW_DP = 2


class PageRetirementCause(UIntEnum):
    PAGE_RETIREMENT_CAUSE_DOUBLE_BIT_ECC_ERROR = 0
    PAGE_RETIREMENT_CAUSE_MULTIPLE_SINGLE_BIT_ECC_ERRORS = 1
    PAGE_RETIREMENT_CAUSE_COUNT = 2


class RestrictedAPI(UIntEnum):
    RESTRICTED_API_SET_APPLICATION_CLOCKS = 0
    RESTRICTED_API_SET_AUTO_BOOSTED_CLOCKS = 1
    RESTRICTED_API_COUNT = 2


class BridgeChipType(UIntEnum):
    BRIDGE_CHIP_PLX = 0
    BRIDGE_CHIP_BRO4 = 1
    MAX_PHYSICAL_BRIDGE = 128


class ValueType(UIntEnum):
    VALUE_TYPE_DOUBLE = 0
    VALUE_TYPE_UNSIGNED_INT = 1
    VALUE_TYPE_UNSIGNED_LONG = 2
    VALUE_TYPE_UNSIGNED_LONG_LONG = 3
    VALUE_TYPE_COUNT = 4


class PerfPolicyType(UIntEnum):
    PERF_POLICY_POWER = 0
    PERF_POLICY_THERMAL = 1
    PERF_POLICY_COUNT = 2


class SamplingType(UIntEnum):
    TOTAL_POWER_SAMPLES = 0
    GPU_UTILIZATION_SAMPLES = 1
    MEMORY_UTILIZATION_SAMPLES = 2
    ENC_UTILIZATION_SAMPLES = 3
    DEC_UTILIZATION_SAMPLES = 4
    PROCESSOR_CLK_SAMPLES = 5
    MEMORY_CLK_SAMPLES = 6
    SAMPLINGTYPE_COUNT = 7


class PcieUtilCounter(UIntEnum):
    PCIE_UTIL_TX_BYTES = 0
    PCIE_UTIL_RX_BYTES = 1
    PCIE_UTIL_COUNT = 2


class GpuTopologyLevel(UIntEnum):
    TOPOLOGY_INTERNAL = 0
    TOPOLOGY_SINGLE = 10
    TOPOLOGY_MULTIPLE = 20
    TOPOLOGY_HOSTBRIDGE = 30
    TOPOLOGY_CPU = 40
    TOPOLOGY_SYSTEM = 50


# C preprocessor defined values
nvmlFlagDefault = 0
nvmlFlagForce = 1

# buffer size
DEVICE_INFOROM_VERSION_BUFFER_SIZE = 16
DEVICE_UUID_BUFFER_SIZE = 80
SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 81
SYSTEM_NVML_VERSION_BUFFER_SIZE = 80
DEVICE_NAME_BUFFER_SIZE = 64
DEVICE_SERIAL_BUFFER_SIZE = 30
DEVICE_VBIOS_VERSION_BUFFER_SIZE = 32
DEVICE_PCI_BUS_ID_BUFFER_SIZE = 16

VALUE_NOT_AVAILABLE_ulonglong = c_ulonglong(-1)
VALUE_NOT_AVAILABLE_uint = c_uint(-1)

## Lib loading ##
nvmlLib = None
libLoadLock = threading.Lock()
_nvmlLib_refcount = 0  # Incremented on each nvmlInit and decremented on nvmlShutdown


## Error Checking ##

class NVMLErrorUninitialized(NVMLError):
    value = Uninitialized


class NVMLError(Exception):
    _valClassMapping = dict()
    # List of currently known error codes
    _errcode_to_string = {
        ERROR_UNINITIALIZED: "Uninitialized",
        ERROR_INVALID_ARGUMENT: "Invalid Argument",
        ERROR_NOT_SUPPORTED: "Not Supported",
        ERROR_NO_PERMISSION: "Insufficient Permissions",
        ERROR_ALREADY_INITIALIZED: "Already Initialized",
        ERROR_NOT_FOUND: "Not Found",
        ERROR_INSUFFICIENT_SIZE: "Insufficient Size",
        ERROR_INSUFFICIENT_POWER: "Insufficient External Power",
        ERROR_DRIVER_NOT_LOADED: "Driver Not Loaded",
        ERROR_TIMEOUT: "Timeout",
        ERROR_IRQ_ISSUE: "Interrupt Request Issue",
        ERROR_LIBRARY_NOT_FOUND: "NVML Shared Library Not Found",
        ERROR_FUNCTION_NOT_FOUND: "Function Not Found",
        ERROR_CORRUPTED_INFOROM: "Corrupted infoROM",
        ERROR_GPU_IS_LOST: "GPU is lost",
        ERROR_RESET_REQUIRED: "GPU requires restart",
        ERROR_OPERATING_SYSTEM: "The operating system has blocked the request.",
        ERROR_LIB_RM_VERSION_MISMATCH: "RM has detected an NVML/RM version mismatch.",
        ERROR_UNKNOWN: "Unknown Error",
    }

    def __new__(typ, value):
        '''
        Maps value to a proper subclass of NVMLError.
        See _extractNVMLErrorsAsClasses function for more details
        '''
        if typ == NVMLError:
            typ = NVMLError._valClassMapping.get(value, typ)
        obj = Exception.__new__(typ)
        obj.value = value
        return obj

    def __str__(self):
        try:
            if self.value not in NVMLError._errcode_to_string:
                NVMLError._errcode_to_string[self.value] = str(nvmlErrorString(self.value))
            return NVMLError._errcode_to_string[self.value]
        except NVMLError_Uninitialized:
            return "NVML Error with code %d" % self.value

    def __eq__(self, other):
        return self.value == other.value


def _extractNVMLErrorsAsClasses():
    """
    Generates a hierarchy of classes on top of NVMLError class.

    Each NVML Error gets a new NVMLError subclass. This way try,except blocks can filter appropriate
    exceptions more easily.

    NVMLError is a parent class. Each     ERROR_* gets it's own subclass.
    e.g.     ERROR_ALREADY_INITIALIZED will be turned into NVMLError_AlreadyInitialized
    """
    this_module = sys.modules[__name__]
    nvmlErrorsNames = filter(lambda x: x.startswith("    ERROR_"), dir(this_module))
    for err_name in nvmlErrorsNames:
        # e.g. Turn     ERROR_ALREADY_INITIALIZED into NVMLError_AlreadyInitialized
        class_name = "NVMLError_" + string.capwords(err_name.replace("    ERROR_", ""), "_").replace("_", "")
        err_val = getattr(this_module, err_name)

        def gen_new(val):
            def new(typ):
                obj = NVMLError.__new__(typ, val)
                return obj

            return new

        new_error_class = type(class_name, (NVMLError,), {'__new__': gen_new(err_val)})
        new_error_class.__module__ = __name__
        setattr(this_module, class_name, new_error_class)
        NVMLError._valClassMapping[err_val] = new_error_class


_extractNVMLErrorsAsClasses()


def _nvmlCheckReturn(ret):
    if ret != Return.SUCCESS.value:
        raise NVMLError(ret)
    return ret


## Function access ##
_nvmlGetFunctionPointer_cache = dict()  # function pointers are cached to prevent unnecessary libLoadLock locking


def _nvmlGetFunctionPointer(name):
    global nvmlLib

    if name in _nvmlGetFunctionPointer_cache:
        return _nvmlGetFunctionPointer_cache[name]

    libLoadLock.acquire()
    try:
        # ensure library was loaded
        if nvmlLib is None:
            raise NVMLError(ERROR_UNINITIALIZED)
        try:
            _nvmlGetFunctionPointer_cache[name] = getattr(nvmlLib, name)
            return _nvmlGetFunctionPointer_cache[name]
        except AttributeError:
            raise NVMLError(ERROR_FUNCTION_NOT_FOUND)
    finally:
        # lock is always freed
        libLoadLock.release()


## Alternative object
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


## Unit structures
class struct_cUnit.C_TYPE(Structure):
    pass  # opaque handle


cUnit_t = POINTER(struct_c_nvmlUnit.C_TYPE)


class _PrintableStructure(Structure):
    """
    Abstract class that produces nicer __str__ output than ctypes.Structure.
    e.g. instead of:
      >>> print str(obj)
      <class_name object at 0x7fdf82fef9e0>
    this class will print
      class_name(field_name: formatted_value, field_name: formatted_value)

    _fmt_ dictionary of <str _field_ name> -> <str format>
    e.g. class that has _field_ 'hex_value', c_uint could be formatted with
      _fmt_ = {"hex_value" : "%08X"}
    to produce nicer output.
    Default fomratting string for all fields can be set with key "<default>" like:
      _fmt_ = {"<default>" : "%d MHz"} # e.g all values are numbers in MHz.
    If not set it's assumed to be just "%s"

    Exact format of returned str from this class is subject to change in the future.
    """
    _fmt_ = {}

    def __str__(self):
        result = []
        for x in self._fields_:
            key = x[0]
            value = getattr(self, key)
            fmt = "%s"
            if key in self._fmt_:
                fmt = self._fmt_[key]
            elif "<default>" in self._fmt_:
                fmt = self._fmt_["<default>"]
            result.append(("%s: " + fmt) % (key, value))
        return self.__class__.__name__ + "(" + string.join(result, ", ") + ")"


class cUnitInfo.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('name', c_char * 96),
        ('id', c_char * 96),
        ('serial', c_char * 96),
        ('firmwareVersion', c_char * 96),
    ]


class cLedState.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('cause', c_char * 256),
        ('color', LedColor.C_TYPE),
    ]


class cPSUInfo.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('state', c_char * 256),
        ('current', c_uint),
        ('voltage', c_uint),
        ('power', c_uint),
    ]


class cUnitFanInfo.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('speed', c_uint),
        ('state', FanState.C_TYPE),
    ]


class cUnitFanSpeeds.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('fans', cUnitFanInfo.C_TYPE * 24),
        ('count', c_uint)
    ]


## Device structures
class struct_cDevice.C_TYPE(Structure):
    pass  # opaque handle


cDevice_t = POINTER(struct_c_nvmlDevice.C_TYPE)


class nvmlPciInfo_t(_PrintableStructure):
    _fields_ = [
        ('busId', c_char * 16),
        ('domain', c_uint),
        ('bus', c_uint),
        ('device', c_uint),
        ('pciDeviceId', c_uint),

        # Added in 2.285
        ('pciSubSystemId', c_uint),
        ('reserved0', c_uint),
        ('reserved1', c_uint),
        ('reserved2', c_uint),
        ('reserved3', c_uint),
    ]
    _fmt_ = {
        'domain': "0x%04X",
        'bus': "0x%02X",
        'device': "0x%02X",
        'pciDeviceId': "0x%08X",
        'pciSubSystemId': "0x%08X",
    }


class cMemory.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('total', c_ulonglong),
        ('free', c_ulonglong),
        ('used', c_ulonglong),
    ]
    _fmt_ = {'<default>': "%d B"}


class cBAR1Memory.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('bar1Total', c_ulonglong),
        ('bar1Free', c_ulonglong),
        ('bar1Used', c_ulonglong),
    ]
    _fmt_ = {'<default>': "%d B"}


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
class cProcessInfo.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('pid', c_uint),
        ('usedGpuMemory', c_ulonglong),
    ]
    _fmt_ = {'usedGpuMemory': "%d B"}


class cBridgeChipInfo.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('type', BridgeChipType.C_TYPE),
        ('fwVersion', c_uint),
    ]


class cBridgeChipHierarchy.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('bridgeCount', c_uint),
        ('bridgeChipInfo', cBridgeChipInfo.C_TYPE * 128),
    ]


class cEccErrorCounts.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('l1Cache', c_ulonglong),
        ('l2Cache', c_ulonglong),
        ('deviceMemory', c_ulonglong),
        ('registerFile', c_ulonglong),
    ]


class cUtilization.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('gpu', c_uint),
        ('memory', c_uint),
    ]
    _fmt_ = {'<default>': "%d %%"}


# Added in 2.285
class cHwbcEntry.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('hwbcId', c_uint),
        ('firmwareVersion', c_char * 32),
    ]


class cValue.C_TYPE(Union):
    _fields_ = [
        ('dVal', c_double),
        ('uiVal', c_uint),
        ('ulVal', c_ulong),
        ('ullVal', c_ulonglong),
    ]


class cSample.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('timeStamp', c_ulonglong),
        ('sampleValue', cValue.C_TYPE),
    ]


class cViolationTime.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('referenceTime', c_ulonglong),
        ('violationTime', c_ulonglong),
    ]


## Event structures
class StructCNvmlEventSetT(Structure):
    pass  # opaque handle


class EventType(IntFlag):
    C_TYPE = POINTER(StructCNvmlEventSetT)

    NONE = 0
    SingleBitEccError = 1
    DoubleBitEccError = 2
    PState = 4
    XidCriticalError = 8
    Clock = 16
    All = (NONE |
        SingleBitEccError |
        DoubleBitEccError |
        PState |
        Clock |
        XidCriticalError)

## Clock Throttle Reasons defines
class ClocksThrottleReason(IntFlag):
    GpuIdle = 1
    ApplicationsClocksSetting = 2
    UserDefinedClocks = ApplicationsClocksSetting  # deprecated, use nvmlClocksThrottleReasonApplicationsClocksSetting
    SwPowerCap = 4
    HwSlowdown = 8
    Unknown = 0x8000000000000000
    NONE = 0
    All = (
            NONE |
            GpuIdle |
            ApplicationsClocksSetting |
            SwPowerCap |
            HwSlowdown |
            Unknown
    )


class cEventData.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('device', cDevice.C_TYPE),
        ('eventType', c_ulonglong),
        ('eventData', c_ulonglong)
    ]
    _fmt_ = {'eventType': "0x%08X"}


class cAccountingStats.C_TYPE(_PrintableStructure):
    _fields_ = [
        ('gpuUtilization', c_uint),
        ('memoryUtilization', c_uint),
        ('maxMemoryUsage', c_ulonglong),
        ('time', c_ulonglong),
        ('startTime', c_ulonglong),
        ('isRunning', c_uint),
        ('reserved', c_uint * 5)
    ]


## C function wrappers ##
def nvmlInit():
    _LoadNvmlLibrary()

    #
    # Initialize the library
    #
    fn = _nvmlGetFunctionPointer("nvmlInit_v2")
    ret = fn()
    _nvmlCheckReturn(ret)

    # Atomically update refcount
    global _nvmlLib_refcount
    libLoadLock.acquire()
    _nvmlLib_refcount += 1
    libLoadLock.release()
    return None


def _LoadNvmlLibrary():
    '''
    Load the library if it isn't loaded already
    '''
    global nvmlLib

    if nvmlLib is None:
        # lock to ensure only one caller loads the library
        libLoadLock.acquire()

        try:
            # ensure the library still isn't loaded
            if nvmlLib is None:
                try:
                    if sys.platform[:3] == "win":
                        searchPaths = [
                            os.path.join(os.getenv("ProgramFiles", r"C:\Program Files"),
                                         r"NVIDIA Corporation\NVSMI\nvml.dll"),
                            os.path.join(os.getenv("WinDir", r"C:\Windows"), r"System32\nvml.dll"),
                        ]
                        nvmlPath = next((x for x in searchPaths if os.path.isfile(x)), None)
                        if nvmlPath == None:
                            _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)
                        else:
                            # cdecl calling convention
                            nvmlLib = CDLL(nvmlPath)
                    else:
                        # assume linux
                        nvmlLib = CDLL("libnvidia-ml.so.1")
                except OSError as ose:
                    _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)
                if (nvmlLib == None):
                    _nvmlCheckReturn(ERROR_LIBRARY_NOT_FOUND)
        finally:
            # lock is always freed
            libLoadLock.release()


def nvmlShutdown():
    #
    # Leave the library loaded, but shutdown the interface
    #
    fn = _nvmlGetFunctionPointer("nvmlShutdown")
    ret = fn()
    _nvmlCheckReturn(ret)

    # Atomically update refcount
    global _nvmlLib_refcount
    libLoadLock.acquire()
    if (0 < _nvmlLib_refcount):
        _nvmlLib_refcount -= 1
    libLoadLock.release()
    return None


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

    hic_array = cHwbcEntry.C_TYPE * c_count.value
    hics = hic_array()
    ret = fn(byref(c_count), hics)
    _nvmlCheckReturn(ret)
    return hics


## Unit get functions
def nvmlUnitGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetCount")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlUnitGetHandleByIndex(index):
    c_index = c_uint(index)
    unit = cUnit.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetHandleByIndex")
    ret = fn(c_index, byref(unit))
    _nvmlCheckReturn(ret)
    return unit


def nvmlUnitGetUnitInfo(unit):
    c_info = cUnitInfo.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetUnitInfo")
    ret = fn(unit, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info


def nvmlUnitGetLedState(unit):
    c_state = cLedState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetLedState")
    ret = fn(unit, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state


def nvmlUnitGetPsuInfo(unit):
    c_info = cPSUInfo.C_TYPE()
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
    c_speeds = cUnitFanSpeeds.C_TYPE()
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
    device_array = cDevice.C_TYPE * c_count.value
    c_devices = device_array()
    fn = _nvmlGetFunctionPointer("nvmlUnitGetDevices")
    ret = fn(unit, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return c_devices


## Device get functions
def nvmlDeviceGetCount():
    c_count = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetCount_v2")
    ret = fn(byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlDeviceGetHandleByIndex(index):
    c_index = c_uint(index)
    device = cDevice.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByIndex_v2")
    ret = fn(c_index, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleBySerial(serial):
    c_serial = c_char_p(serial)
    device = cDevice.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleBySerial")
    ret = fn(c_serial, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleByUUID(uuid):
    c_uuid = c_char_p(uuid)
    device = cDevice.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetHandleByUUID")
    ret = fn(c_uuid, byref(device))
    _nvmlCheckReturn(ret)
    return device


def nvmlDeviceGetHandleByPciBusId(pciBusId):
    c_busId = c_char_p(pciBusId)
    device = cDevice.C_TYPE()
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
    c_type = BrandType.C_TYPE()
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


def nvmlDeviceGetInforomVersion(handle, info_rom_object:InforomObject):
    c_version = create_string_buffer(DEVICE_INFOROM_VERSION_BUFFER_SIZE)
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetInforomVersion")
    ret = fn(handle, InforomObject.C_TYPE(info_rom_object.value),
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
    c_mode = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetDisplayActive(handle):
    c_mode = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDisplayActive")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetPersistenceMode(handle):
    c_state = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPersistenceMode")
    ret = fn(handle, byref(c_state))
    _nvmlCheckReturn(ret)
    return c_state.value


def nvmlDeviceGetPciInfo(handle):
    c_info = nvmlPciInfo_t()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPciInfo_v2")
    ret = fn(handle, byref(c_info))
    _nvmlCheckReturn(ret)
    return c_info


def nvmlDeviceGetClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetClockInfo")
    ret = fn(handle, ClockType.C_TYPE(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 2.285
def nvmlDeviceGetMaxClockInfo(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMaxClockInfo")
    ret = fn(handle, ClockType.C_TYPE(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 4.304
def nvmlDeviceGetApplicationsClock(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetApplicationsClock")
    ret = fn(handle, ClockType.C_TYPE(type), byref(c_clock))
    _nvmlCheckReturn(ret)
    return c_clock.value


# Added in 5.319
def nvmlDeviceGetDefaultApplicationsClock(handle, type):
    c_clock = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDefaultApplicationsClock")
    ret = fn(handle, ClockType.C_TYPE(type), byref(c_clock))
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
    ret = fn(handle, TemperatureSensors_t(sensor), byref(c.C_TYPEemp))
    _nvmlCheckReturn(ret)
    return c_temp.value


def nvmlDeviceGetTemperatureThreshold(handle, threshold):
    c_temp = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTemperatureThreshold")
    ret = fn(handle, TemperatureThresholds_t(threshold), byref(c.C_TYPEemp))
    _nvmlCheckReturn(ret)
    return c_temp.value


# DEPRECATED use nvmlDeviceGetPerformanceState
def nvmlDeviceGetPowerState(handle):
    c_pstate = Pstates.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value


def nvmlDeviceGetPerformanceState(handle):
    c_pstate = Pstates.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPerformanceState")
    ret = fn(handle, byref(c_pstate))
    _nvmlCheckReturn(ret)
    return c_pstate.value


def nvmlDeviceGetPowerManagementMode(handle):
    c_pcapMode = EnableState.C_TYPE()
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
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPowerManagementLimitConstraints")
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
    c_currState = GpuOperationMode.C_TYPE()
    c_pendingState = GpuOperationMode.C_TYPE()
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
    c_memory = cMemory.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryInfo")
    ret = fn(handle, byref(c_memory))
    _nvmlCheckReturn(ret)
    return c_memory


def nvmlDeviceGetBAR1MemoryInfo(handle):
    c_bar1_memory = cBAR1Memory.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBAR1MemoryInfo")
    ret = fn(handle, byref(c_bar1_memory))
    _nvmlCheckReturn(ret)
    return c_bar1_memory


def nvmlDeviceGetComputeMode(handle):
    c_mode = ComputeMode.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetComputeMode")
    ret = fn(handle, byref(c_mode))
    _nvmlCheckReturn(ret)
    return c_mode.value


def nvmlDeviceGetEccMode(handle):
    c_currState = EnableState.C_TYPE()
    c_pendingState = EnableState.C_TYPE()
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
             EccCounterType.C_TYPE(counterType), byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


# This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
def nvmlDeviceGetDetailedEccErrors(handle, errorType, counterType):
    c_counts = cEccErrorCounts.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetDetailedEccErrors")
    ret = fn(handle, MemoryErrorType.C_TYPE(errorType),
             EccCounterType.C_TYPE(counterType), byref(c_counts))
    _nvmlCheckReturn(ret)
    return c_counts


# Added in 4.304
def nvmlDeviceGetMemoryErrorCounter(handle, errorType, counterType, locationType):
    c_count = c_ulonglong()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetMemoryErrorCounter")
    ret = fn(handle,
             MemoryErrorType.C_TYPE(errorType),
             EccCounterType.C_TYPE(counterType),
             MemoryLocation.C_TYPE(locationType),
             byref(c_count))
    _nvmlCheckReturn(ret)
    return c_count.value


def nvmlDeviceGetUtilizationRates(handle):
    c_util = cUtilization.C_TYPE()
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
    c_currModel = DriverModel.C_TYPE()
    c_pendingModel = DriverModel.C_TYPE()
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
        proc_array = cProcessInfo.C_TYPE * c_count.value
        c_procs = proc_array()

        # make the call again
        ret = fn(handle, byref(c_count), c_procs)
        _nvmlCheckReturn(ret)

        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
            if (obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong.value):
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
    elif (ret == ERROR_INSUFFICIENT_SIZE):
        # typical case
        # oversize the array incase more processes are created
        c_count.value = c_count.value * 2 + 5
        proc_array = cProcessInfo.C_TYPE * c_count.value
        c_procs = proc_array()

        # make the call again
        ret = fn(handle, byref(c_count), c_procs)
        _nvmlCheckReturn(ret)

        procs = []
        for i in range(c_count.value):
            # use an alternative struct for this object
            obj = nvmlStructToFriendlyObject(c_procs[i])
            if (obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong.value):
                # special case for WDDM on Windows, see comment above
                obj.usedGpuMemory = None
            procs.append(obj)

        return procs
    else:
        # error case
        raise NVMLError(ret)


def nvmlDeviceGetAutoBoostedClocksEnabled(handle):
    c_isEnabled = EnableState.C_TYPE()
    c_defaultIsEnabled = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAutoBoostedClocksEnabled")
    ret = fn(handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
    _nvmlCheckReturn(ret)
    return [c_isEnabled.value, c_defaultIsEnabled.value]
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto boosted clocks


## Set functions
def nvmlUnitSetLedState(unit, color):
    fn = _nvmlGetFunctionPointer("nvmlUnitSetLedState")
    ret = fn(unit, LedColor.C_TYPE(color))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetPersistenceMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetPersistenceMode")
    ret = fn(handle, EnableState.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetComputeMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetComputeMode")
    ret = fn(handle, ComputeMode.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceSetEccMode(handle, mode):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetEccMode")
    ret = fn(handle, EnableState.C_TYPE(mode))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceClearEccErrorCounts(handle, counterType):
    fn = _nvmlGetFunctionPointer("nvmlDeviceClearEccErrorCounts")
    ret = fn(handle, EccCounterType.C_TYPE(counterType))
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
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto boosted clocks


def nvmlDeviceSetDefaultAutoBoostedClocksEnabled(handle, enabled, flags):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetDefaultAutoBoostedClocksEnabled")
    ret = fn(handle, EnableState.C_TYPE(enabled), c_uint(flags))
    _nvmlCheckReturn(ret)
    return None
    # Throws     ERROR_NOT_SUPPORTED if hardware doesn't support setting auto boosted clocks


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
    data = cEventData.C_TYPE()
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
    c_mode = EnableState.C_TYPE()
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
    stats = cAccountingStats.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAccountingStats")
    ret = fn(handle, c_uint(pid), byref(stats))
    _nvmlCheckReturn(ret)
    if (stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong.value):
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
    c_source = PageRetirementCause.C_TYPE(sourceFilter)
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
    c_pending = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetRetiredPagesPendingStatus")
    ret = fn(device, byref(c_pending))
    _nvmlCheckReturn(ret)
    return int(c_pending.value)


def nvmlDeviceGetAPIRestriction(device, apiType):
    c_permission = EnableState.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetAPIRestriction")
    ret = fn(device, RestrictedAPI.C_TYPE(apiType), byref(c_permission))
    _nvmlCheckReturn(ret)
    return int(c_permission.value)


def nvmlDeviceSetAPIRestriction(handle, apiType, isRestricted):
    fn = _nvmlGetFunctionPointer("nvmlDeviceSetAPIRestriction")
    ret = fn(handle, RestrictedAPI_t(apiType), EnableState.C.C_TYPEYPE(isRestricted))
    _nvmlCheckReturn(ret)
    return None


def nvmlDeviceGetBridgeChipInfo(handle):
    bridgeHierarchy = cBridgeChipHierarchy.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetBridgeChipInfo")
    ret = fn(handle, byref(bridgeHierarchy))
    _nvmlCheckReturn(ret)
    return bridgeHierarchy


def nvmlDeviceGetSamples(device, sampling_type, timeStamp):
    c_sampling_type = SamplingType_t(sampling.C_TYPEype)
    c_time_stamp = c_ulonglong(timeStamp)
    c_sample_count = c_uint(0)
    c_sample_value_type = ValueType.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetSamples")

    ## First Call gets the size
    ret = fn(device, c_sampling_type, c_time_stamp, byref(c_sample_value_type), byref(c_sample_count), None)

    # Stop if this fails
    if (ret != Return.SUCCESS.value):
        raise NVMLError(ret)

    sampleArray = c_sample_count.value * cSample.C_TYPE
    c_samples = sampleArray()
    ret = fn(device, c_sampling_type, c_time_stamp, byref(c_sample_value_type), byref(c_sample_count), c_samples)
    _nvmlCheckReturn(ret)
    return (c_sample_value_type.value, c_samples[0:c_sample_count.value])


def nvmlDeviceGetViolationStatus(device, perfPolicyType):
    c_perfPolicy_type = PerfPolicyType.C_TYPE(perfPolicyType)
    c_violTime = cViolationTime.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetViolationStatus")

    ## Invoke the method to get violation time
    ret = fn(device, c_perfPolicy_type, byref(c_violTime))
    _nvmlCheckReturn(ret)
    return c_violTime


def nvmlDeviceGetPcieThroughput(device, counter):
    c_util = c_uint()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetPcieThroughput")
    ret = fn(device, PcieUtilCounter.C_TYPE(counter), byref(c_util))
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
    device_array = cDevice.C_TYPE * c_count.value
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
    device_array = cDevice.C_TYPE * c_count.value
    c_devices = device_array()
    ret = fn(device, level, byref(c_count), c_devices)
    _nvmlCheckReturn(ret)
    return map(None, c_devices[0:c_count.value])


def nvmlDeviceGetTopologyCommonAncestor(device1, device2):
    c_level = GpuTopologyLevel.C_TYPE()
    fn = _nvmlGetFunctionPointer("nvmlDeviceGetTopologyCommonAncestor")
    ret = fn(device1, device2, byref(c_level))
    _nvmlCheckReturn(ret)
    return c_level.value
