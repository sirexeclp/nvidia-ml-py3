from ctypes import c_char, c_uint, c_ulonglong, Union, c_double, c_ulong

from enums import LedColor, FanState
from pynvml import _PrintableStructure


class UnitInfo(_PrintableStructure):
    _fields_ = [
        ('name', c_char * 96),
        ('id', c_char * 96),
        ('serial', c_char * 96),
        ('firmwareVersion', c_char * 96),
    ]


class LedState(_PrintableStructure):
    _fields_ = [
        ('cause', c_char * 256),
        ('olor', LedColor),
    ]


class PSUInfo(_PrintableStructure):
    _fields_ = [
        ('state', c_char * 256),
        ('current', c_uint),
        ('voltage', c_uint),
        ('power', c_uint),
    ]


class UnitFanInfo(_PrintableStructure):
    _fields_ = [
        ('speed', c_uint),
        ('state', FanState.C_TYPE),
    ]


class UnitFanSpeeds(_PrintableStructure):
    _fields_ = [
        ('fans', UnitFanInfo * 24),
        ('count', c_uint)
    ]


class PciInfo(_PrintableStructure):
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


class Memory(_PrintableStructure):
    _fields_ = [
        ('total', c_ulonglong),
        ('free', c_ulonglong),
        ('used', c_ulonglong),
    ]
    _fmt_ = {'<default>': "%d B"}


class ProcessInfo(_PrintableStructure):
    _fields_ = [
        ('pid', c_uint),
        ('usedGpuMemory', c_ulonglong),
    ]
    _fmt_ = {'usedGpuMemory': "%d B"}


class BridgeChipInfo(_PrintableStructure):
    _fields_ = [
        ('type', BridgehipType),
        ('fwVersion', c_uint),
    ]


class BridgeChipHierarchy(_PrintableStructure):
    _fields_ = [
        ('bridgeCount', c_uint),
        ('bridgehipInfo', cBridgeChipInfo * 128),
    ]


class EccErrorCounts(_PrintableStructure):
    _fields_ = [
        ('l1Cache', c_ulonglong),
        ('l2Cache', c_ulonglong),
        ('deviceMemory', c_ulonglong),
        ('registerFile', c_ulonglong),
    ]


class Utilization(_PrintableStructure):
    _fields_ = [
        ('gpu', c_uint),
        ('memory', c_uint),
    ]
    _fmt_ = {'<default>': "%d %%"}


class HwbcEntry(_PrintableStructure):
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


class Sample(_PrintableStructure):
    _fields_ = [
        ('timeStamp', c_ulonglong),
        ('sampleValue', Value),
    ]


class ViolationTime(_PrintableStructure):
    _fields_ = [
        ('referenceTime', c_ulonglong),
        ('violationTime', c_ulonglong),
    ]


class EventData(_PrintableStructure):
    _fields_ = [
        ('devie', cDevice),
        ('eventType', c_ulonglong),
        ('eventData', c_ulonglong)
    ]
    _fmt_ = {'eventType': "0x%08X"}


class AccountingStats(_PrintableStructure):
    _fields_ = [
        ('gpuUtilization', c_uint),
        ('memoryUtilization', c_uint),
        ('maxMemoryUsage', c_ulonglong),
        ('time', c_ulonglong),
        ('startTime', c_ulonglong),
        ('isRunning', c_uint),
        ('reserved', c_uint * 5)
    ]