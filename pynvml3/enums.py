from ctypes import c_char_p, c_uint
from enum import Enum, EnumMeta


def to_c_str(python_str: str):
    """Convert the python string to a c string."""
    return c_char_p(str(python_str).encode("ASCII"))


class MetaEnum(EnumMeta):
    def __contains__(cls, item):
        return cls.has_value(item)

    c_type = c_uint


class UIntEnum(Enum, metaclass=MetaEnum):
    # @staticmethod
    # def c_type():
    #     """ Must be a Property, because Enum Subclasses can't define members."""
    #     return c_uint

    @classmethod
    def has_value(cls, value):
        try:
            cls(value)
        except ValueError as e:
            return False
        else:
            return True

    def as_c_type(self):
        return UIntEnum.c_type(self.value)


class EnableState(UIntEnum):
    FEATURE_DISABLED = 0
    FEATURE_ENABLED = 1


class BrandType(UIntEnum):
    UNKNOWN = 0
    QUADRO = 1
    TESLA = 2
    NVS = 3
    GRID = 4
    GEFORCE = 5


class TemperatureThresholds(UIntEnum):
    SHUTDOWN = 0
    SLOWDOWN = 1


class TemperatureSensors(UIntEnum):
    TEMPERATURE_GPU = 0


class TemperatureType(UIntEnum):
    INTAKE = 0
    EXHAUST = 1
    BOARD = 2


class ComputeMode(UIntEnum):
    DEFAULT = 0
    EXCLUSIVE_THREAD = 1
    PROHIBITED = 2
    EXCLUSIVE_PROCESS = 3


class MemoryLocation(UIntEnum):
    L1_CACHE = 0
    L2_CACHE = 1
    DEVICE_MEMORY = 2
    REGISTER_FILE = 3
    TEXTURE_MEMORY = 4


class EccBitType(UIntEnum):
    SINGLE_BIT_ECC = 0
    DOUBLE_BIT_ECC = 1
    COUNT = 2


class EccCounterType(UIntEnum):
    VOLATILE_ECC = 0
    AGGREGATE_ECC = 1
    COUNT = 2


class MemoryErrorType(UIntEnum):
    CORRECTED = 0
    UNCORRECTED = 1


class ClockType(UIntEnum):
    GRAPHICS = 0
    SM = 1
    MEM = 2


class DriverModel(UIntEnum):
    WDDM = 0
    WDM = 1


class PowerState(UIntEnum):
    P_0 = 0
    P_1 = 1
    P_2 = 2
    P_3 = 3
    P_4 = 4
    P_5 = 5
    P_6 = 6
    P_7 = 7
    P_8 = 8
    P_9 = 9
    P_10 = 10
    P_11 = 11
    P_12 = 12
    P_13 = 13
    P_14 = 14
    P_15 = 15
    P_UNKNOWN = 32


class InfoRom(UIntEnum):
    OEM = 0
    ECC = 1
    POWER = 2


class FanState(UIntEnum):
    NORMAL = 0
    FAILED = 1


class LedColor(UIntEnum):
    """Led color enum."""

    GREEN = 0
    """GREEN, indicates good health."""

    AMBER = 1
    """AMBER, indicates problem."""


class GpuTopologyLevel(UIntEnum):
    INTERNAL = 0
    SINGLE = 10
    MULTIPLE = 20
    HOSTBRIDGE = 30
    CPU = 40
    SYSTEM = 50


class GpuOperationMode(UIntEnum):
    GOM_ALL_ON = 0
    GOM_COMPUTE = 1
    GOM_LOW_DP = 2


class PageRetirementCause(UIntEnum):
    DOUBLE_BIT_ECC_ERROR = 0
    MULTIPLE_SINGLE_BIT_ECC_ERRORS = 1


class RestrictedAPI(UIntEnum):
    SET_APPLICATION_CLOCKS = 0
    SET_AUTO_BOOSTED_CLOCKS = 1


class BridgeChipType(UIntEnum):
    PLX = 0
    BRO4 = 1
    MAX_PHYSICAL_BRIDGE = 128


class ValueType(UIntEnum):
    DOUBLE = 0
    UNSIGNED_INT = 1
    UNSIGNED_LONG = 2
    UNSIGNED_LONG_LONG = 3

    def extract_value(self, union):
        sample_value = union
        mapping = {
            ValueType.DOUBLE: sample_value.dVal,
            ValueType.UNSIGNED_INT: sample_value.uiVal,
            ValueType.UNSIGNED_LONG: sample_value.ulVal,
            ValueType.UNSIGNED_LONG_LONG: sample_value.ullVal,
        }
        return mapping[self]


class SamplingType(UIntEnum):
    TOTAL_POWER_SAMPLES = 0
    GPU_UTILIZATION_SAMPLES = 1
    MEMORY_UTILIZATION_SAMPLES = 2
    ENC_UTILIZATION_SAMPLES = 3
    DEC_UTILIZATION_SAMPLES = 4
    PROCESSOR_CLK_SAMPLES = 5
    MEMORY_CLK_SAMPLES = 6

    def get_filename(self) -> str:
        """Get a file system friendly representation of this SamplingType.

        Returns: The SamplingType as lower case string.

        """
        return str(self).split(".")[1].lower()


class PcieUtilCounter(UIntEnum):
    TX_BYTES = 0
    RX_BYTES = 1


#################################
#          New Enums            #
#################################


class ClockId(UIntEnum):
    """Clock Ids. These are used in combination with
    ClockType to specify a single clock value.
    """

    CURRENT = 0
    """Current actual clock value."""

    APP_CLOCK_TARGET = 1
    """Target application clock."""

    APP_CLOCK_DEFAULT = 2
    """Default application clock target."""

    CUSTOMER_BOOST_MAX = 3
    """OEM - defined maximum clock rate."""


#################################
#          Drain State          #
#################################


class DetachGpuState(UIntEnum):
    """Is the GPU device to be removed from the kernel by nvmlDeviceRemoveGpu()"""

    KEEP = 0
    REMOVE = 1


class PcieLinkState(UIntEnum):
    """Parent bridge PCIe link state requested by nvmlDeviceRemoveGpu()"""

    KEEP = 0
    SHUT_DOWN = 1


#################################
#          NVML DEVICE          #
#################################


class NvLinkCapability(UIntEnum):
    """Enum to represent NvLink queryable capabilities"""

    P2P_SUPPORTED = 0
    SYSMEM_ACCESS = 1
    P2P_ATOMICS = 2
    SYSMEM_ATOMICS = 3
    SLI_BRIDGE = 4
    VALID = 5


class NvLinkErrorCounter(UIntEnum):
    """Enum to represent NvLink queryable error counters"""

    REPLAY = 0
    RECOVERY = 1
    CRC_FLIT = 2
    CRC_DATA = 3


class NvLinkUtilizationCountPktTypes(UIntEnum):
    """Enum to represent the NvLink utilization counter packet types to count.

    Note:
        This is ONLY applicable with the units as packets or bytes
        as specified in nvmlNvLinkUtilizationCountUnits_t
        all packet filter descriptions are target GPU centric
        these can be "OR'd" together

    """

    NOP = 0x1
    READ = 0x2
    WRITE = 0x4
    RATOM = 0x8
    NRATOM = 0x10
    FLUSH = 0x20
    RESPDATA = 0x40
    RESPNODATA = 0x80
    ALL = 0xFF


class NvLinkUtilizationCountUnits(UIntEnum):
    """Enum to represent the NvLink utilization counter packet units"""

    CYCLES = 0
    PACKETS = 1
    BYTES = 2
    RESERVED = 3


class PerfPolicyType(UIntEnum):
    """Represents type of perf policy for which violation times can be queried"""

    PERF_POLICY_POWER = 0
    """ How long did power violations cause the GPU to be below application clocks."""
    PERF_POLICY_THERMAL = 1
    """How long did thermal violations cause the GPU to be below application clocks."""
    PERF_POLICY_COUNT = 2
    """How long did sync boost cause the GPU to be below application clocks."""
    BOARD_LIMIT = 3
    """How long did the board limit cause the GPU to be below application clocks."""
    LOW_UTILIZATION = 4
    """How long did low utilization cause the GPU to be below application clocks."""
    RELIABILITY = 5
    """How long did the board reliability limit cause the GPU to be below application clocks."""
    TOTAL_APP_CLOCKS = 10
    """Total time the GPU was held below application clocks by any limiter (0 - 5 above)."""
    TOTAL_BASE_CLOCKS = 11
    """Total time the GPU was held below base clocks."""


# ( *)([\w_]*) *([0-9]+) *//!< (\w.*)
#    #$4\n    $2 = $3


class FieldId(UIntEnum):
    """Field Identifiers.
    All Identifiers pertain to a device.
    Each ID is only used once and is guaranteed never to change.
    """

    ECC_CURRENT = 1
    """Current ECC mode. 1=Active. 0=Inactive"""
    ECC_PENDING = 2
    """Pending ECC mode. 1=Active. 0=Inactive
    
    Note:
        ECC Count Totals
    
    """

    ECC_SBE_VOL_TOTAL = 3
    """Total single bit volatile ECC errors"""
    ECC_DBE_VOL_TOTAL = 4
    """Total double bit volatile ECC errors"""
    ECC_SBE_AGG_TOTAL = 5
    """Total single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_TOTAL = 6
    """Total double bit aggregate (persistent) ECC errors
    
    Note:
        Individual ECC locations
    
    """
    ECC_SBE_VOL_L1 = 7
    """L1 cache single bit volatile ECC errors"""
    ECC_DBE_VOL_L1 = 8
    """L1 cache double bit volatile ECC errors"""
    ECC_SBE_VOL_L2 = 9
    """L2 cache single bit volatile ECC errors"""
    ECC_DBE_VOL_L2 = 10
    """L2 cache double bit volatile ECC errors"""
    ECC_SBE_VOL_DEV = 11
    """Device memory single bit volatile ECC errors"""
    ECC_DBE_VOL_DEV = 12
    """Device memory double bit volatile ECC errors"""
    ECC_SBE_VOL_REG = 13
    """Register file single bit volatile ECC errors"""
    ECC_DBE_VOL_REG = 14
    """Register file double bit volatile ECC errors"""
    ECC_SBE_VOL_TEX = 15
    """Texture memory single bit volatile ECC errors"""
    ECC_DBE_VOL_TEX = 16
    """Texture memory double bit volatile ECC errors"""
    ECC_DBE_VOL_CBU = 17
    """CBU double bit volatile ECC errors"""
    ECC_SBE_AGG_L1 = 18
    """L1 cache single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_L1 = 19
    """L1 cache double bit aggregate (persistent) ECC errors"""
    ECC_SBE_AGG_L2 = 20
    """L2 cache single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_L2 = 21
    """L2 cache double bit aggregate (persistent) ECC errors"""
    ECC_SBE_AGG_DEV = 22
    """Device memory single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_DEV = 23
    """Device memory double bit aggregate (persistent) ECC errors"""
    ECC_SBE_AGG_REG = 24
    """Register File single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_REG = 25
    """Register File double bit aggregate (persistent) ECC errors"""
    ECC_SBE_AGG_TEX = 26
    """Texture memory single bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_TEX = 27
    """Texture memory double bit aggregate (persistent) ECC errors"""
    ECC_DBE_AGG_CBU = 28
    """CBU double bit aggregate ECC errors

    Note:
        Page Retirement
    
    """
    RETIRED_SBE = 29
    """Number of retired pages because of single bit errors"""
    RETIRED_DBE = 30
    """Number of retired pages because of double bit errors"""
    RETIRED_PENDING = 31
    """If any pages are pending retirement. 1=yes. 0=no.

    Note:
        NvLink Flit Error Counters
    
    """
    NVLINK_CRC_FLIT_ERROR_COUNT_L0 = 32
    """NVLink flow control CRC  Error Counter for Lane 0"""
    NVLINK_CRC_FLIT_ERROR_COUNT_L1 = 33
    """NVLink flow control CRC  Error Counter for Lane 1"""
    NVLINK_CRC_FLIT_ERROR_COUNT_L2 = 34
    """NVLink flow control CRC  Error Counter for Lane 2"""
    NVLINK_CRC_FLIT_ERROR_COUNT_L3 = 35
    """NVLink flow control CRC  Error Counter for Lane 3"""
    NVLINK_CRC_FLIT_ERROR_COUNT_L4 = 36
    """NVLink flow control CRC  Error Counter for Lane 4"""
    NVLINK_CRC_FLIT_ERROR_COUNT_L5 = 37
    """NVLink flow control CRC  Error Counter for Lane 5"""
    NVLINK_CRC_FLIT_ERROR_COUNT_TOTAL = 38
    """NVLink flow control CRC  Error Counter total for all Lanes

    Note:
        NvLink CRC Data Error Counters

    """
    NVLINK_CRC_DATA_ERROR_COUNT_L0 = 39
    """NVLink data CRC Error Counter for Lane 0"""
    NVLINK_CRC_DATA_ERROR_COUNT_L1 = 40
    """NVLink data CRC Error Counter for Lane 1"""
    NVLINK_CRC_DATA_ERROR_COUNT_L2 = 41
    """NVLink data CRC Error Counter for Lane 2"""
    NVLINK_CRC_DATA_ERROR_COUNT_L3 = 42
    """NVLink data CRC Error Counter for Lane 3"""
    NVLINK_CRC_DATA_ERROR_COUNT_L4 = 43
    """NVLink data CRC Error Counter for Lane 4"""
    NVLINK_CRC_DATA_ERROR_COUNT_L5 = 44
    """NVLink data CRC Error Counter for Lane 5"""
    NVLINK_CRC_DATA_ERROR_COUNT_TOTAL = 45
    """NvLink data CRC Error Counter total for all Lanes

    Note:
        NvLink Replay Error Counters

    """
    NVLINK_REPLAY_ERROR_COUNT_L0 = 46
    """NVLink Replay Error Counter for Lane 0"""
    NVLINK_REPLAY_ERROR_COUNT_L1 = 47
    """NVLink Replay Error Counter for Lane 1"""
    NVLINK_REPLAY_ERROR_COUNT_L2 = 48
    """NVLink Replay Error Counter for Lane 2"""
    NVLINK_REPLAY_ERROR_COUNT_L3 = 49
    """NVLink Replay Error Counter for Lane 3"""
    NVLINK_REPLAY_ERROR_COUNT_L4 = 50
    """NVLink Replay Error Counter for Lane 4"""
    NVLINK_REPLAY_ERROR_COUNT_L5 = 51
    """NVLink Replay Error Counter for Lane 5"""
    NVLINK_REPLAY_ERROR_COUNT_TOTAL = 52
    """NVLink Replay Error Counter total for all Lanes

    Note:
        NvLink Recovery Error Counters

    """
    NVLINK_RECOVERY_ERROR_COUNT_L0 = 53
    """NVLink Recovery Error Counter for Lane 0"""
    NVLINK_RECOVERY_ERROR_COUNT_L1 = 54
    """NVLink Recovery Error Counter for Lane 1"""
    NVLINK_RECOVERY_ERROR_COUNT_L2 = 55
    """NVLink Recovery Error Counter for Lane 2"""
    NVLINK_RECOVERY_ERROR_COUNT_L3 = 56
    """NVLink Recovery Error Counter for Lane 3"""
    NVLINK_RECOVERY_ERROR_COUNT_L4 = 57
    """NVLink Recovery Error Counter for Lane 4"""
    NVLINK_RECOVERY_ERROR_COUNT_L5 = 58
    """NVLink Recovery Error Counter for Lane 5"""
    NVLINK_RECOVERY_ERROR_COUNT_TOTAL = 59
    """NVLink Recovery Error Counter total for all Lanes

    Note:
        NvLink Bandwidth Counters

    """
    NVLINK_BANDWIDTH_C0_L0 = 60
    """NVLink Bandwidth Counter for Counter Set 0, Lane 0"""
    NVLINK_BANDWIDTH_C0_L1 = 61
    """NVLink Bandwidth Counter for Counter Set 0, Lane 1"""
    NVLINK_BANDWIDTH_C0_L2 = 62
    """NVLink Bandwidth Counter for Counter Set 0, Lane 2"""
    NVLINK_BANDWIDTH_C0_L3 = 63
    """NVLink Bandwidth Counter for Counter Set 0, Lane 3"""
    NVLINK_BANDWIDTH_C0_L4 = 64
    """NVLink Bandwidth Counter for Counter Set 0, Lane 4"""
    NVLINK_BANDWIDTH_C0_L5 = 65
    """NVLink Bandwidth Counter for Counter Set 0, Lane 5"""
    NVLINK_BANDWIDTH_C0_TOTAL = 66
    """NVLink Bandwidth Counter Total for Counter Set 0, All Lanes

    Note:
        NvLink Bandwidth Counters

    """
    NVLINK_BANDWIDTH_C1_L0 = 67
    """NVLink Bandwidth Counter for Counter Set 1, Lane 0"""
    NVLINK_BANDWIDTH_C1_L1 = 68
    """NVLink Bandwidth Counter for Counter Set 1, Lane 1"""
    NVLINK_BANDWIDTH_C1_L2 = 69
    """NVLink Bandwidth Counter for Counter Set 1, Lane 2"""
    NVLINK_BANDWIDTH_C1_L3 = 70
    """NVLink Bandwidth Counter for Counter Set 1, Lane 3"""
    NVLINK_BANDWIDTH_C1_L4 = 71
    """NVLink Bandwidth Counter for Counter Set 1, Lane 4"""
    NVLINK_BANDWIDTH_C1_L5 = 72
    """NVLink Bandwidth Counter for Counter Set 1, Lane 5"""
    NVLINK_BANDWIDTH_C1_TOTAL = 73
    """NVLink Bandwidth Counter Total for Counter Set 1, All Lanes

    Note:
        NVML Perf Policy Counters

    """
    PERF_POLICY_POWER = 74
    """Perf Policy Counter for Power Policy"""
    PERF_POLICY_THERMAL = 75
    """Perf Policy Counter for Thermal Policy"""
    PERF_POLICY_SYNC_BOOST = 76
    """Perf Policy Counter for Sync boost Policy"""
    PERF_POLICY_BOARD_LIMIT = 77
    """Perf Policy Counter for Board Limit"""
    PERF_POLICY_LOW_UTILIZATION = 78
    """Perf Policy Counter for Low GPU Utilization Policy"""
    PERF_POLICY_RELIABILITY = 79
    """Perf Policy Counter for Reliability Policy"""
    PERF_POLICY_TOTAL_APP_CLOCKS = 80
    """Perf Policy Counter for Total App Clock Policy"""
    PERF_POLICY_TOTAL_BASE_CLOCKS = 81
    """Perf Policy Counter for Total Base Clocks Policy

    Note:
        Memory temperatures

    """
    MEMORY_TEMP = 82
    """Memory temperature for the device
    
    Note:
        Energy Counter
    
    """
    TOTAL_ENERGY_CONSUMPTION = 83
    """Total energy consumption for the GPU in mJ
    since the driver was last reloaded.

    Note:
        NVLink Speed
    
    """
    NVLINK_SPEED_MBPS_L0 = 84
    """NVLink Speed in MBps for Link 0"""
    NVLINK_SPEED_MBPS_L1 = 85
    """NVLink Speed in MBps for Link 1"""
    NVLINK_SPEED_MBPS_L2 = 86
    """NVLink Speed in MBps for Link 2"""
    NVLINK_SPEED_MBPS_L3 = 87
    """NVLink Speed in MBps for Link 3"""
    NVLINK_SPEED_MBPS_L4 = 88
    """NVLink Speed in MBps for Link 4"""
    NVLINK_SPEED_MBPS_L5 = 89
    """NVLink Speed in MBps for Link 5"""
    NVLINK_SPEED_MBPS_COMMON = 90
    """Common NVLink Speed in MBps for active links"""

    NVLINK_LINK_COUNT = 91
    """Number of NVLinks present on the device"""

    RETIRED_PENDING_SBE = 92
    """If any pages are pending retirement due to SBE. 1=yes. 0=no."""
    RETIRED_PENDING_DBE = 93
    """If any pages are pending retirement due to DBE. 1=yes. 0=no."""

    PCIE_REPLAY_COUNTER = 94
    """PCIe replay counter"""
    PCIE_REPLAY_ROLLOVER_COUNTER = 95
    """PCIe replay rollover counter"""


class GpuInstanceProfile(UIntEnum):
    PROFILE_1_SLICE = 0x0
    PROFILE_2_SLICE = 0x1
    PROFILE_3_SLICE = 0x2
    PROFILE_4_SLICE = 0x3
    PROFILE_7_SLICE = 0x4
    PROFILE_8_SLICE = 0x5
    PROFILE_6_SLICE = 0x6
    PROFILE_1_SLICE_REV1 = 0x7

    # these seem to be invalid for Version 1
    PROFILE_2_SLICE_REV1 = 0x8
    PROFILE_1_SLICE_REV2 = 0x9
    PROFILE_COUNT = 0xA
