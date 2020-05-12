from ctypes import POINTER
from enum import IntFlag

from structs import CEventSet


class EventType(IntFlag):
    @property
    def C_TYPE(self):
        """ Must be a Property, because Enum Subclasses can't define members."""
        return POINTER(CEventSet)

    NONE = 0
    SingleBitEccError = 1
    DoubleBitEccError = 2
    P = 4
    XidCriticalError = 8
    Clock = 16
    All = (NONE |
           SingleBitEccError |
           DoubleBitEccError |
           P |
           Clock |
           XidCriticalError)


class ClocksThrottleReason(IntFlag):
    GpuIdle = 1
    ApplicationsClocksSetting = 2
    # deprecated, use nvmlClocksThrottleReasonApplicationsClocksSetting
    UserDefinedClocks = ApplicationsClocksSetting
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