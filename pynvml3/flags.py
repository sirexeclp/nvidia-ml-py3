from ctypes import POINTER, c_ulonglong
from enum import IntFlag

from pynvml3.structs import CEventSet


class EventType(IntFlag):
    """Event Types which user can be notified about."""

    @property
    def C_TYPE(self):
        """Must be a Property, because Enum Subclasses can't define members."""
        return POINTER(CEventSet)

    def as_c_type(self):
        """Get c type representation."""
        return c_ulonglong(self.value)

    NONE = 0
    SingleBitEccError = 1
    DoubleBitEccError = 2
    PState = 4
    XidCriticalError = 8
    Clock = 16
    All = (
        NONE | SingleBitEccError | DoubleBitEccError | PState | Clock | XidCriticalError
    )


class ClocksThrottleReason(IntFlag):
    GpuIdle = 1
    ApplicationsClocksSetting = 2
    # deprecated, use nvmlClocksThrottleReasonApplicationsClocksSetting
    UserDefinedClocks = ApplicationsClocksSetting
    SwPowerCap = 4
    HwSlowdown = 8
    Unknown = 0x8000000000000000
    NONE = 0
    All = NONE | GpuIdle | ApplicationsClocksSetting | SwPowerCap | HwSlowdown | Unknown
