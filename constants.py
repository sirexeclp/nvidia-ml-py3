from ctypes import c_ulonglong, c_uint

nvmlFlagDefault = 0
nvmlFlagForce = 1
DEVICE_INFOROM_VERSION_BUFFER_SIZE = 16
DEVICE_UUID_BUFFER_SIZE = 80
SYSTEM_DRIVER_VERSION_BUFFER_SIZE = 81
SYSTEM_NVML_VERSION_BUFFER_SIZE = 80
DEVICE_NAME_BUFFER_SIZE = 64
DEVICE_SERIAL_BUFFER_SIZE = 30
DEVICE_VBIOS_VERSION_BUFFER_SIZE = 32
DEVICE_PCI_BUS_ID_BUFFER_SIZE = 16
VALUE_NOT_AVAILABLE_ulonglong = c_ulonglong(-1)
VALUE_NOT_AVAILABLE_uint = c_uint(-1)