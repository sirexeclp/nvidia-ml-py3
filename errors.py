from enums import UIntEnum


# from pynvml import nvmlErrorString


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
            Return.ERROR_UNKNOWN: "Unknown Error",
        }
        return errcode_to_string[self]

    def get_exception(self):
        error2exception = {
            Return.ERROR_UNINITIALIZED: NVMLErrorUninitialized,
            Return.ERROR_INVALID_ARGUMENT: NVMLErrorUninitializedInvalidArgument,
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
            Return.ERROR_UNKNOWN: NVMLErrorUnknown,
        }
        return error2exception[self]


class NVMLError(Exception):
    def __init__(self, return_value: int):
        self.return_value = return_value

    def __str__(self):
        try:
            if self.return_value not in Return:
                return  # str(nvmlErrorString(self.return_value))
            else:
                return str(Return(self.return_value))
        except NVMLErrorUninitialized:
            return "NVML Error with code %d" % self.return_value

    def __eq__(self, other):
        return self.return_value == other.return_value

    @staticmethod
    def from_return(return_value: int):
        if return_value in Return:
            return Return(return_value).get_exception()
        else:
            return NVMLError(return_value)


class NVMLErrorUninitialized(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_UNINITIALIZED.value)


class NVMLErrorUninitializedInvalidArgument(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_INVALID_ARGUMENT.value)


class NVMLErrorNotSupported(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_NOT_SUPPORTED.value)


class NVMLErrorInsufficientPermissions(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_NO_PERMISSION.value)


class NVMLErrorAlreadyInitialized(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_ALREADY_INITIALIZED.value)


class NVMLErrorNotFound(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_NOT_FOUND.value)


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


class NVMLErrorUnknown(NVMLError):
    def __init__(self):
        super().__init__(Return.ERROR_UNKNOWN.value)
