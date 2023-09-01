from pynvml3.enums import UIntEnum
from ctypes import c_char_p


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

    # new
    NVML_ERROR_IN_USE = 19
    NVML_ERROR_MEMORY = 20
    NVML_ERROR_NO_DATA = 21
    NVML_ERROR_VGPU_ECC_NOT_SUPPORTED = 22
    NVML_ERROR_INSUFFICIENT_RESOURCES = 23
    NVML_ERROR_FREQ_NOT_SUPPORTED = 24
    NVML_ERROR_ARGUMENT_VERSION_MISMATCH = 25
    NVML_ERROR_DEPRECATED = 26
    NVML_ERROR_NOT_READY = 27

    ERROR_UNKNOWN = 999

    def __str__(self):
        errcode_to_string = {
            Return.ERROR_UNINITIALIZED: "Uninitialized",
            Return.ERROR_INVALID_ARGUMENT: "Invalid Argument",
            Return.ERROR_NOT_SUPPORTED: "Not Supported",
            Return.ERROR_NO_PERMISSION: "Insufficient Permissions",
            Return.ERROR_ALREADY_INITIALIZED: "Already Initialized",
            Return.ERROR_NOT_FOUND: "Not Found",
            Return.ERROR_INSUFFICIENT_SIZE: "Insufficient Size",
            Return.ERROR_INSUFFICIENT_POWER: "Insufficient External Power",
            Return.ERROR_DRIVER_NOT_LOADED: "Driver Not Loaded",
            Return.ERROR_TIMEOUT: "Timeout",
            Return.ERROR_IRQ_ISSUE: "Interrupt Request Issue",
            Return.ERROR_LIBRARY_NOT_FOUND: "NVML Shared Library Not Found",
            Return.ERROR_FUNCTION_NOT_FOUND: "Function Not Found",
            Return.ERROR_CORRUPTED_INFOROM: "Corrupted infoROM",
            Return.ERROR_GPU_IS_LOST: "GPU is lost",
            Return.ERROR_RESET_REQUIRED: "GPU requires restart",
            Return.ERROR_OPERATING_SYSTEM: "The operating system has blocked the request.",
            Return.ERROR_LIB_RM_VERSION_MISMATCH: "RM has detected an NVML/RM version mismatch.",
            Return.NVML_ERROR_IN_USE: "An operation cannot be performed because the GPU is currently in use.",
            Return.NVML_ERROR_MEMORY: "Insufficient memory.",
            Return.NVML_ERROR_NO_DATA: "No data.",
            Return.NVML_ERROR_VGPU_ECC_NOT_SUPPORTED: "The requested vgpu operation is not available on target device, becasue ECC is enabled.",
            Return.NVML_ERROR_INSUFFICIENT_RESOURCES: "Ran out of critical resources, other than memory.",
            Return.NVML_ERROR_FREQ_NOT_SUPPORTED: "The requested frequency is not supported.",
            Return.NVML_ERROR_ARGUMENT_VERSION_MISMATCH: "The provided version is invalid/unsupported.",
            Return.NVML_ERROR_DEPRECATED: "The requested functionality has been deprecated.",
            Return.NVML_ERROR_NOT_READY: "",
            Return.ERROR_UNKNOWN: "Unknown Error",
        }
        return errcode_to_string[self]

    def get_exception(self):
        error2exception = {
            Return.ERROR_UNINITIALIZED: NVMLErrorUninitialized,
            Return.ERROR_INVALID_ARGUMENT: NVMLErrorInvalidArgument,
            Return.ERROR_NOT_SUPPORTED: NVMLErrorNotSupported,
            Return.ERROR_NO_PERMISSION: NVMLErrorInsufficientPermissions,
            Return.ERROR_ALREADY_INITIALIZED: NVMLErrorAlreadyInitialized,
            Return.ERROR_NOT_FOUND: NVMLErrorNotFound,
            Return.ERROR_INSUFFICIENT_SIZE: NVMLErrorInsufficientSize,
            Return.ERROR_INSUFFICIENT_POWER: NVMLErrorInsufficientExternalPower,
            Return.ERROR_DRIVER_NOT_LOADED: NVMLErrorDriverNotLoaded,
            Return.ERROR_TIMEOUT: NVMLErrorTimeout,
            Return.ERROR_IRQ_ISSUE: NVMLErrorInterruptRequestIssue,
            Return.ERROR_LIBRARY_NOT_FOUND: NVMLErrorSharedLibraryNotFound,
            Return.ERROR_FUNCTION_NOT_FOUND: NVMLErrorFunctionNotFound,
            Return.ERROR_CORRUPTED_INFOROM: NVMLErrorCorruptedInfoROM,
            Return.ERROR_GPU_IS_LOST: NVMLErrorGPUIsLost,
            Return.ERROR_RESET_REQUIRED: NVMLErrorGPUResetRequired,
            Return.ERROR_OPERATING_SYSTEM: NVMLErrorOperatingSystem,
            Return.ERROR_LIB_RM_VERSION_MISMATCH: NVMLErrorVersionMismatch,
            Return.NVML_ERROR_IN_USE: NVMLErrorInUse,
            Return.NVML_ERROR_MEMORY: NVMLErrorMemory,
            Return.NVML_ERROR_NO_DATA: NVMLErrorNoData,
            Return.NVML_ERROR_VGPU_ECC_NOT_SUPPORTED: NVMLErrorVgpuEccNotSupported,
            Return.NVML_ERROR_INSUFFICIENT_RESOURCES: NVMLErrorInsufficientResources,
            Return.NVML_ERROR_FREQ_NOT_SUPPORTED: NVMLErrorFreqNotSupported,
            Return.NVML_ERROR_ARGUMENT_VERSION_MISMATCH: NVMLErrorArgumentVersionMismatch,
            Return.NVML_ERROR_DEPRECATED: NVMLErrorDeprecated,
            Return.NVML_ERROR_NOT_READY: NVMLErrorNotReady,
            Return.ERROR_UNKNOWN: NVMLErrorUnknown,
        }
        return error2exception[self]

    @staticmethod
    def check(ret: int, *args):
        """Check the return-value; raises an Exception, if not successful."""
        if ret != Return.SUCCESS.value:
            raise NVMLError.from_return(ret, *args)


class NVMLError(Exception):
    def __init__(self, return_value: int, *args):
        self.return_value = return_value
        self.args = args

    def __str__(self):
        try:
            if self.return_value not in Return:
                return self.get_error_string()
            return str(Return(self.return_value)) + (str(self.args) if self.args else "")
        except NVMLErrorUninitialized:
            return f"NVML Error with code {self.return_value}"

    def __eq__(self, other):
        return self.return_value == other.return_value

    # Added in 2.285
    def get_error_string(self) -> str:
        from pynvml3.pynvml import NVMLLib

        with NVMLLib() as lib:
            fn = lib.get_function_pointer("nvmlErrorString")
            fn.restype = c_char_p  # otherwise return is an int
            ret = fn(self.return_value)
            return ret.decode("UTF-8")

    @staticmethod
    def from_return(return_value: int, *args):
        if return_value in Return:
            return Return(return_value).get_exception()(*args)
        else:
            return NVMLError(return_value, *args)


class NVMLErrorUninitialized(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_UNINITIALIZED.value)


class NVMLErrorInvalidArgument(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_INVALID_ARGUMENT.value)


class NVMLErrorNotSupported(NVMLError):
    def __init__(self, *args):
        super().__init__(Return.ERROR_NOT_SUPPORTED.value, *args)


class NVMLErrorInsufficientPermissions(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_NO_PERMISSION.value)


class NVMLErrorAlreadyInitialized(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_ALREADY_INITIALIZED.value)


class NVMLErrorNotFound(NVMLError):
    def __init__(self, *args):
        super().__init__(Return.ERROR_NOT_FOUND.value, *args)


class NVMLErrorInsufficientSize(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_INSUFFICIENT_SIZE.value)


class NVMLErrorInsufficientExternalPower(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_INSUFFICIENT_POWER.value)


class NVMLErrorDriverNotLoaded(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_DRIVER_NOT_LOADED.value)


class NVMLErrorTimeout(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_TIMEOUT.value)


class NVMLErrorInterruptRequestIssue(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_IRQ_ISSUE.value)


class NVMLErrorSharedLibraryNotFound(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_LIBRARY_NOT_FOUND.value)


class NVMLErrorFunctionNotFound(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_FUNCTION_NOT_FOUND.value)


class NVMLErrorCorruptedInfoROM(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_CORRUPTED_INFOROM.value)


class NVMLErrorGPUIsLost(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_GPU_IS_LOST.value)


class NVMLErrorGPUResetRequired(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_RESET_REQUIRED.value)


class NVMLErrorOperatingSystem(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_OPERATING_SYSTEM.value)


class NVMLErrorVersionMismatch(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_LIB_RM_VERSION_MISMATCH.value)


class NVMLErrorInUse(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_IN_USE.value)


class NVMLErrorInUse(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_IN_USE.value)


class NVMLErrorMemory(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_MEMORY.value)


class NVMLErrorNoData(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_NO_DATA.value)


class NVMLErrorVgpuEccNotSupported(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_VGPU_ECC_NOT_SUPPORTED.value)


class NVMLErrorInsufficientResources(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_INSUFFICIENT_RESOURCES.value)


class NVMLErrorFreqNotSupported(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_FREQ_NOT_SUPPORTED.value)


class NVMLErrorArgumentVersionMismatch(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_ARGUMENT_VERSION_MISMATCH.value)


class NVMLErrorDeprecated(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_DEPRECATED.value)


class NVMLErrorNotReady(NVMLError):
    def __init__(self):
        super().__init__(Return.NVML_ERROR_NOT_READY.value)


class NVMLErrorUnknown(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_UNKNOWN.value)
