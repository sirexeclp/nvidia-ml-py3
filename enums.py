from ctypes import c_uint
from enum import Enum, EnumMeta


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
    GREEN = 0
    AMBER = 1


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
        sample_value = union.sampleValue
        mapping = {
            ValueType.DOUBLE: sample_value.dVal,
            ValueType.U_INT: sample_value.uiVal,
            ValueType.U_LONG: sample_value.ulVal,
            ValueType.U_LONG_LONG: sample_value.ullVal
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


class PcieUtilCounter(UIntEnum):
    TX_BYTES = 0
    PRX_BYTES = 1


#################################
#          New Enums            #
#################################

class ClockId(UIntEnum):
    """
    Clock Ids. These are used in combination with ClockType to specify a single clock value.
    """
    # Current actual clock value.
    CURRENT = 0
    # Target application clock.
    APP_CLOCK_TARGET = 1
    # Default application clock target.
    APP_CLOCK_DEFAULT = 2
    # OEM - defined maximum clock rate.
    CUSTOMER_BOOST_MAX = 3


#################################
#          Drain State          #
#################################

class DetachGpuState(UIntEnum):
    """
    Is the GPU device to be removed from the kernel by nvmlDeviceRemoveGpu()
    """
    KEEP = 0
    REMOVE = 1


class PcieLinkState(UIntEnum):
    """
    Parent bridge PCIe link state requested by nvmlDeviceRemoveGpu()
    """
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
    """Enum to represent the NvLink utilization counter packet types to count
    ** this is ONLY applicable with the units as packets or bytes
    ** as specified in nvmlNvLinkUtilizationCountUnits_t
    ** all packet filter descriptions are target GPU centric
    ** these can be "OR'd" together"""

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
    #  How long did power violations cause the GPU to be below application clocks.
    PERF_POLICY_POWER = 0
    # How long did thermal violations cause the GPU to be below application clocks.
    PERF_POLICY_THERMAL = 1
    # How long did sync boost cause the GPU to be below application clocks.
    PERF_POLICY_COUNT = 2
    # How long did the board limit cause the GPU to be below application clocks.
    BOARD_LIMIT = 3
    # How long did low utilization cause the GPU to be below application clocks.        
    LOW_UTILIZATION = 4
    # How long did the board reliability limit cause the GPU to be below application clocks.
    RELIABILITY = 5
    # Total time the GPU was held below application clocks by any limiter (0 - 5 above).
    TOTAL_APP_CLOCKS = 10
    # Total time the GPU was held below base clocks.
    TOTAL_BASE_CLOCKS = 11
