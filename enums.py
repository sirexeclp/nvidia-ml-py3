from ctypes import c_uint
from enum import Enum


class UIntEnum(Enum):
    C_TYPE = c_uint


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


class InforomObject(UIntEnum):
    OEM = 0
    ECC = 1
    POWER = 2


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

    def extract_value(self, union: Sample):
        sample_value = union.sampleValue
        mapping = {
            ValueType.DOUBLE: sample_value.dVal,
            ValueType.U_INT: sample_value.uiVal,
            ValueType.U_LONG: sample_value.ulVal,
            ValueType.U_LONG_LONG: sample_value.ullVal
        }
        return mapping[self]


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


class PcieUtilCounter(UIntEnum):
    TX_BYTES = 0
    PRX_BYTES = 1