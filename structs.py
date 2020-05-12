import string
from ctypes import c_char, c_uint, c_ulonglong, Union, c_double, c_ulong, Structure, POINTER

from enums import LedColor, FanState, BridgeChipType


# Alternative object
# Allows the object to be printed
# Allows mismatched types to be assigned
#  - like None when the Structure variant requires c_uint
class FriendlyObject(object):
    def __init__(self, dictionary):
        for x in dictionary:
            setattr(self, x, dictionary[x])

    def __str__(self):
        return self.__dict__.__str__()


class PrintableStructure(Structure):
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

    def get_friendly_object(self):
        d = {}
        for x in self._fields_:
            key = x[0]
            value = getattr(self, key)
            d[key] = value
        obj = FriendlyObject(d)
        return obj

    @classmethod
    def from_friendly_object(cls, obj):
        model = cls()
        for x in model._fields_:
            key = x[0]
            value = obj.__dict__[key]
            setattr(model, key, value)
        return model


class CUnit(Structure):
    pass  # opaque handle


CUnitPointer = POINTER(CUnit)


class CDevice(Structure):
    pass  # opaque handle


CDevicePointer = POINTER(CDevice)


class CEventSet(Structure):
    pass  # opaque handle


class UnitInfo(PrintableStructure):
    _fields_ = [
        ('name', c_char * 96),
        ('id', c_char * 96),
        ('serial', c_char * 96),
        ('firmwareVersion', c_char * 96),
    ]


class LedState(PrintableStructure):
    _fields_ = [
        ('cause', c_char * 256),
        ('color', LedColor.c_type),
    ]


class PSUInfo(PrintableStructure):
    _fields_ = [
        ('state', c_char * 256),
        ('current', c_uint),
        ('voltage', c_uint),
        ('power', c_uint),
    ]


class UnitFanInfo(PrintableStructure):
    _fields_ = [
        ('speed', c_uint),
        ('state', FanState.c_type),
    ]


class UnitFanSpeeds(PrintableStructure):
    _fields_ = [
        ('fans', UnitFanInfo * 24),
        ('count', c_uint)
    ]


class PciInfo(PrintableStructure):
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


class Memory(PrintableStructure):
    _fields_ = [
        ('total', c_ulonglong),
        ('free', c_ulonglong),
        ('used', c_ulonglong),
    ]
    _fmt_ = {'<default>': "%d B"}


class ProcessInfo(PrintableStructure):
    _fields_ = [
        ('pid', c_uint),
        ('usedGpuMemory', c_ulonglong),
    ]
    _fmt_ = {'usedGpuMemory': "%d B"}


class BridgeChipInfo(PrintableStructure):
    _fields_ = [
        ('type', BridgeChipType.c_type),
        ('fwVersion', c_uint),
    ]


class BridgeChipHierarchy(PrintableStructure):
    _fields_ = [
        ('bridgeCount', c_uint),
        ('bridgeChipInfo', BridgeChipInfo * 128),
    ]


class EccErrorCounts(PrintableStructure):
    _fields_ = [
        ('l1Cache', c_ulonglong),
        ('l2Cache', c_ulonglong),
        ('deviceMemory', c_ulonglong),
        ('registerFile', c_ulonglong),
    ]


class Utilization(PrintableStructure):
    _fields_ = [
        ('gpu', c_uint),
        ('memory', c_uint),
    ]
    _fmt_ = {'<default>': "%d %%"}


class HwbcEntry(PrintableStructure):
    _fields_ = [
        ('hwbcId', c_uint),
        ('firmwareVersion', c_char * 32),
    ]


class Value(Union):
    _fields_ = [
        ('dVal', c_double),
        ('uiVal', c_uint),
        ('ulVal', c_ulong),
        ('ullVal', c_ulonglong),
    ]


class Sample(PrintableStructure):
    _fields_ = [
        ('timeStamp', c_ulonglong),
        ('sampleValue', Value),
    ]


class ViolationTime(PrintableStructure):
    _fields_ = [
        ('referenceTime', c_ulonglong),
        ('violationTime', c_ulonglong),
    ]


class EventData(PrintableStructure):
    _fields_ = [
        ('device', CDevicePointer),
        ('eventType', c_ulonglong),
        ('eventData', c_ulonglong)
    ]
    _fmt_ = {'eventType': "0x%08X"}


class AccountingStats(PrintableStructure):
    _fields_ = [
        ('gpuUtilization', c_uint),
        ('memoryUtilization', c_uint),
        ('maxMemoryUsage', c_ulonglong),
        ('time', c_ulonglong),
        ('startTime', c_ulonglong),
        ('isRunning', c_uint),
        ('reserved', c_uint * 5)
    ]


class BAR1Memory(PrintableStructure):
    _fields_ = [
        ('bar1Total', c_ulonglong),
        ('bar1Free', c_ulonglong),
        ('bar1Used', c_ulonglong),
    ]
    _fmt_ = {'<default>': "%d B"}
