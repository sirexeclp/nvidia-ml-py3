"""Define some constants for the c library."""
from ctypes import c_ulonglong, c_uint

NVML_FLAG_DEFAULT = 0
NVML_FLAG_FORCE = 1

SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 81
SYSTEM_NVML_VERSION_BUFFER_SIZE = 80

VALUE_NOT_AVAILABLE_ulonglong = c_ulonglong(-1)
VALUE_NOT_AVAILABLE_uint = c_uint(-1)

NVML_NVLINK_MAX_LINKS = 6
