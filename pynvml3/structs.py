"""Struct definitions to interact with the c api."""
import string
import typing
from collections import namedtuple
from ctypes import (
    c_char,
    c_uint,
    c_ulonglong,
    Union,
    c_double,
    c_ulong,
    Structure,
    POINTER,
    byref,
    c_longlong,
)
from typing import NamedTuple

from pynvml3.enums import (
    LedColor,
    FanState,
    BridgeChipType,
    EnableState,
    DetachGpuState,
    PcieLinkState,
    NvLinkUtilizationCountUnits,
    NvLinkUtilizationCountPktTypes,
    ValueType,
    FieldId,
)

# Alternative object
# Allows the object to be printed
# Allows mismatched types to be assigned
#  - like None when the Structure variant requires c_uint
from pynvml3.errors import Return


class Sample(NamedTuple):
    """A measurement sample with an attached timestamp."""

    timestamp: int
    value: typing.Union[int, float]


class FriendlyObject(object):
    """Construct a python object from the given dictionary."""

    def __init__(self, dictionary: dict):
        for key in dictionary:
            setattr(self, key, dictionary[key])

    def __str__(self):
        return self.__dict__.__str__()


class PrintableStructure(Structure):
    """Abstract class that produces nicer :func:`__str__` output than
    ctypes.Structure.

    Examples:
        e.g. instead of::

            print str(obj)

        <class_name object at 0x7fdf82fef9e0>

        this class will print

        class_name(field_name: formatted_value, field_name: formatted_value)
    """

    _fmt_: typing.Dict[str, str] = {}
    """typing.Dict[str, str]: define formatting for given fields

    Examples:
        e.g. class that has ``_field_`` 'hex_value', c_uint
        could be formatted with::

            _fmt_ = {"hex_value" : "%08X"}

        to produce nicer output.

        Default formatting string for all fields
        can be set with key "<default>" like::

            _fmt_ = {"<default>" : "%d MHz"} # e.g all values are numbers in MHz

        If not set it's assumed to be just "%s"

    Warnings:
        Exact format of returned str from this class
        is subject to change in the future.
    """

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


CEventSetPointer = POINTER(CEventSet)


class UnitInfo(PrintableStructure):
    """Info about the unit."""

    _fields_ = [
        # Product name.
        ("name", c_char * 96),
        # Product identifier.
        ("id", c_char * 96),
        # Product serial number.
        ("serial", c_char * 96),
        # Firmware version.
        ("firmwareVersion", c_char * 96),
    ]


class LedState(PrintableStructure):
    """LedState info."""

    _fields_ = [
        ("cause", c_char * 256),
        ("color", LedColor.c_type),
    ]


class PSUInfo(PrintableStructure):
    """Power usage information for an S-class unit.

    Args:
        current: PSU current (A).
        power: PSU power draw (W).
        state: The power supply state.
        voltage: PSU voltage (V).

    Note:
        The power supply state is a human readable string that equals
        "Normal" or contains a combination of "Abnormal"
        plus one or more of the following:

        - High voltage
        - Fan failure
        - Heatsink temperature
        - Current limit
        - Voltage below UV alarm threshold
        - Low-voltage
        - SI2C remote off command
        - MOD_DISABLE input
        - Short pin transition
    """

    _fields_ = [
        ("state", c_char * 256),
        ("current", c_uint),
        ("voltage", c_uint),
        ("power", c_uint),
    ]


class UnitFanInfo(PrintableStructure):
    _fields_ = [
        ("speed", c_uint),
        ("state", FanState.c_type),
    ]


class UnitFanSpeeds(PrintableStructure):
    """Fan speed readings for an entire S-class unit.

    Args:
        fans: Number of fans in unit.
        count: Fan speed data for each fan.
    """

    _fields_ = [("fans", UnitFanInfo * 24), ("count", c_uint)]


class PciInfo(PrintableStructure):
    _fields_ = [
        ("busId", c_char * 16),
        ("domain", c_uint),
        ("bus", c_uint),
        ("device", c_uint),
        ("pciDeviceId", c_uint),
        # Added in 2.285
        ("pciSubSystemId", c_uint),
        ("reserved0", c_uint),
        ("reserved1", c_uint),
        ("reserved2", c_uint),
        ("reserved3", c_uint),
    ]
    _fmt_ = {
        "domain": "0x%04X",
        "bus": "0x%02X",
        "device": "0x%02X",
        "pciDeviceId": "0x%08X",
        "pciSubSystemId": "0x%08X",
    }

    def remove_gpu(
        self, gpu_state=DetachGpuState.REMOVE, link_state=PcieLinkState.KEEP
    ):
        """
        This method will remove the specified GPU from the view of both NVML
        and the NVIDIA kernel driver as long as no other processes are attached.
        If other processes are attached, this call will return NVML_ERROR_IN_USE
        and the GPU will be returned to its original "draining" state.

        Note: the only situation where a process can still be attached
            after nvmlDeviceModifyDrainState() is called to initiate
            the draining state is if that process was using, and is still using,
            a GPU before the call was made. Also note, persistence mode
            counts as an attachment to the GPU thus it must be disabled prior to this call.

        For long-running NVML processes please note that this will change the enumeration
        of current GPUs. For example, if there are four GPUs present and GPU1 is removed,
        the new enumeration will be 0-2. Also, device handles after the removed GPU will
        not be valid and must be re-established. Must be run as administrator. For Linux only.

        PASCAL_OR_NEWER, Some Kepler devices supported.
        """
        from pynvml3.errors import Return
        from pynvml3.pynvml import NVMLLib

        # if self.get_persistence_mode() == EnableState.FEATURE_ENABLED:
        #     self.set_persistence_mode(EnableState.FEATURE_DISABLED)
        pci_info = self  # .nvml_device_get_pci_info()
        fn = NVMLLib().get_function_pointer("nvmlDeviceRemoveGpu")
        ret = fn(byref(pci_info), gpu_state.as_c_type(), link_state.as_c_type())
        Return.check(ret)

    # @staticmethod
    def discover_gpus(self):
        """Request the OS and the NVIDIA kernel driver to rediscover a portion
        of the PCI subsystem looking for GPUs that were previously removed. The
        portion of the PCI tree can be narrowed by specifying a domain, bus,
        and device. If all are zeroes then the entire PCI tree will be
        searched. Please note that for long-running NVML processes the
        enumeration will change based on how many GPUs are discovered and where
        they are inserted in bus order. In addition, all newly discovered GPUs
        will be initialized and their ECC scrubbed which may take several
        seconds per GPU. Also, all device handles are no longer guaranteed to
        be valid post discovery.

        Must be run as administrator. For Linux only.

        PASCAL_OR_NEWER, Some Kepler devices supported.
        """
        from pynvml3.errors import Return
        from pynvml3.pynvml import NVMLLib

        # The PCI tree to be searched.
        # Only the domain, bus, and device fields are used in this call.
        fn = NVMLLib().get_function_pointer("nvmlDeviceDiscoverGpus")
        ret = fn(byref(self))
        Return.check(ret)

    # @staticmethod
    def modify_drain_state(self, new_state: EnableState) -> None:
        """Modify the drain state of a GPU. This method forces a GPU to no
        longer accept new incoming requests. Any new NVML process will no
        longer see this GPU. Persistence mode for this GPU must be turned off
        before this call is made. Must be called as administrator. For Linux
        only.

        PASCAL_OR_NEWER, Some Kepler devices supported.

        @param new_state: The drain state that should be entered, see EnableState
        @type new_state: EnableState
        """
        from pynvml3.errors import Return
        from pynvml3.pynvml import NVMLLib

        # pci_info = self.nvml_device_get_pci_info()
        fn = NVMLLib().get_function_pointer("nvmlDeviceModifyDrainState")
        ret = fn(byref(self), new_state.as_c_type())
        Return.check(ret)

    def query_drain_state(self) -> EnableState:
        """Query the drain state of a GPU.

        This method is used to check if a GPU is in a currently draining state. For Linux only.

        PASCAL_OR_NEWER, Some Kepler devices supported.

        @return: The current drain state for this GPU, see EnableState
        @rtype: EnableState
        """
        from pynvml3.errors import Return
        from pynvml3.pynvml import NVMLLib

        current_state = EnableState.c_type()
        pci_info = self  # .nvml_device_get_pci_info()
        fn = NVMLLib().get_function_pointer("nvmlDeviceQueryDrainState")
        ret = fn(byref(pci_info), byref(current_state))
        Return.check(ret)
        return EnableState(current_state.value)


class Memory(PrintableStructure):
    _fields_ = [
        ("total", c_ulonglong),
        ("free", c_ulonglong),
        ("used", c_ulonglong),
    ]
    _fmt_ = {"<default>": "%d B"}


class ProcessInfo(PrintableStructure):
    _fields_ = [
        # Process ID.
        ("pid", c_uint),
        # Amount of used GPU memory in bytes.
        ("usedGpuMemory", c_ulonglong),
    ]
    _fmt_ = {"usedGpuMemory": "%d B"}


class BridgeChipInfo(PrintableStructure):
    _fields_ = [
        ("type", BridgeChipType.c_type),
        ("fwVersion", c_uint),
    ]


class BridgeChipHierarchy(PrintableStructure):
    _fields_ = [
        ("bridgeCount", c_uint),
        ("bridgeChipInfo", BridgeChipInfo * 128),
    ]


class EccErrorCounts(PrintableStructure):
    _fields_ = [
        ("l1Cache", c_ulonglong),
        ("l2Cache", c_ulonglong),
        ("deviceMemory", c_ulonglong),
        ("registerFile", c_ulonglong),
    ]


class Utilization(PrintableStructure):
    _fields_ = [
        ("gpu", c_uint),
        ("memory", c_uint),
    ]
    _fmt_ = {"<default>": "%d %%"}


class HwbcEntry(PrintableStructure):
    _fields_ = [
        ("hwbcId", c_uint),
        ("firmwareVersion", c_char * 32),
    ]


class Value(Union):
    _fields_ = [
        ("dVal", c_double),
        ("uiVal", c_uint),
        ("ulVal", c_ulong),
        ("ullVal", c_ulonglong),
    ]

    def get_value(self, value_type):  # ValueType
        return value_type.extract_value(self)


class RawSample(PrintableStructure):
    _fields_ = [
        ("timeStamp", c_ulonglong),
        ("sampleValue", Value),
    ]


class ViolationTime(PrintableStructure):
    _fields_ = [
        ("referenceTime", c_ulonglong),
        ("violationTime", c_ulonglong),
    ]


class EventData(PrintableStructure):
    """Information about occurred event.

    Args:
        device: Specific device where the event occurred.
        eventType: Information about what specific event occurred.
        eventData: Stores XID error for the device in
            the event of nvmlEventTypeXidCriticalError.
    """

    _fields_ = [
        ("device", CDevicePointer),
        ("eventType", c_ulonglong),
        ("eventData", c_ulonglong),
    ]
    _fmt_ = {"eventType": "0x%08X"}


class AccountingStats(PrintableStructure):
    _fields_ = [
        ("gpuUtilization", c_uint),
        ("memoryUtilization", c_uint),
        ("maxMemoryUsage", c_ulonglong),
        ("time", c_ulonglong),
        ("startTime", c_ulonglong),
        ("isRunning", c_uint),
        ("reserved", c_uint * 5),
    ]


class BAR1Memory(PrintableStructure):
    _fields_ = [
        ("bar1Total", c_ulonglong),
        ("bar1Free", c_ulonglong),
        ("bar1Used", c_ulonglong),
    ]
    _fmt_ = {"<default>": "%d B"}


#################################
#          NVML DEVICE          #
#################################


class NvLinkUtilizationControl(PrintableStructure):
    _fields_ = [
        ("units", NvLinkUtilizationCountUnits.c_type),
        ("pktfilter", NvLinkUtilizationCountPktTypes.c_type),
    ]


class FieldValue(PrintableStructure):
    """Information for a Field Value Sample."""

    _fields_ = [
        # ID of the NVML field to retrieve. This must be set before any call that uses this struct.
        # See the constants starting with NVML_FI_ above.
        ("fieldId", FieldId.c_type),
        # Currently unused. This should be initialized to 0 by the caller before any API call
        ("unused", c_uint),
        # CPU Timestamp of this value in microseconds since 1970
        ("timestamp", c_longlong),
        # How long this field value took to update (in usec) within NVML.
        # This may be averaged across several fields that are serviced by the same driver call.
        ("latencyUsec", c_longlong),
        # Type of the value stored in value
        ("valueType", ValueType.c_type),
        # Return code for retrieving this value. This must be checked before looking at value,
        # as value is undefined if nvmlReturn != NVML_SUCCESS
        ("nvmlReturn", Return.c_type),
        # Value for this field. This is only valid if nvmlReturn == NVML_SUCCESS
        ("value", Value),
    ]
