from ctypes import create_string_buffer, c_uint, byref, c_int, pointer
from typing import List, Tuple

from pynvml3.constants import (
    SYSTEM_NVML_VERSION_BUFFER_SIZE,
    SYSTEM_DRIVER_VERSION_BUFFER_SIZE,
)
from pynvml3.errors import Return
from pynvml3.structs import HwbcEntry, CDevicePointer


class System:
    """Queries that NVML can perform against the local system.
    These queries are not device-specific.

    """

    def __init__(self, lib):
        self.lib = lib

    def get_nvml_version(self) -> str:
        """Retrieves the version of the NVML library.

        The version identifier is an alphanumeric string.
        It will not exceed 80 characters in length (including the NULL terminator).
        See nvmlConstants::NVML_SYSTEM_NVML_VERSION_BUFFER_SIZE."""
        c_version = create_string_buffer(SYSTEM_NVML_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetNVMLVersion")
        ret = fn(c_version, c_uint(SYSTEM_NVML_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 2.285
    def get_process_name(self, pid: int) -> str:
        """Gets name of the process with provided process id
        ALL_PRODUCTS
        Returned process name is cropped to provided length.
        name string is encoded in ANSI."""
        c_name = create_string_buffer(1024)
        fn = self.lib.get_function_pointer("nvmlSystemGetProcessName")
        ret = fn(c_uint(pid), c_name, c_uint(1024))
        Return.check(ret)
        return c_name.value.decode("UTF-8")

    def get_driver_version(self) -> str:
        """Retrieves the version of the system's graphics driver.
        ALL_PRODUCTS
        The version identifier is an alphanumeric string.
        It will not exceed 80 characters in length (including the NULL terminator).
        See nvmlConstants::NVML_SYSTEM_DRIVER_VERSION_BUFFER_SIZE."""
        c_version = create_string_buffer(SYSTEM_DRIVER_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlSystemGetDriverVersion")
        ret = fn(c_version, c_uint(SYSTEM_DRIVER_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 2.285
    def get_hic_version(self) -> List[HwbcEntry]:
        """Retrieves the IDs and firmware versions for any Host Interface Cards (HICs) in the system.
        S_CLASS
        The hwbcCount argument is expected to be set to the size of the input hwbcEntries array.
        The HIC must be connected to an S-class system for it to be reported by this function."""
        c_count = c_uint(0)
        hics = None
        fn = self.lib.get_function_pointer("nvmlSystemGetHicVersion")

        # get the count
        ret = fn(byref(c_count), None)

        # this should only fail with insufficient size
        return_value = Return(ret)
        if (
            return_value != Return.SUCCESS
            and return_value != Return.ERROR_INSUFFICIENT_SIZE
        ):
            raise return_value.get_exception()

        # if there are no hics
        if c_count.value == 0:
            return []

        hic_array = HwbcEntry * c_count.value
        hics = hic_array()
        ret = fn(byref(c_count), hics)
        Return.check(ret)
        return list(hics)

    def _get_cuda_driver_version(self) -> int:
        """Retrieves the version of the CUDA driver from the shared library."""
        fn = self.lib.get_function_pointer("nvmlSystemGetCudaDriverVersion_v2")
        cuda_driver_version = c_int()
        ret = fn(byref(cuda_driver_version))
        Return.check(ret)
        return cuda_driver_version.value

    def get_cuda_driver_version(self) -> Tuple[int, int]:
        """Retrieves the version of the CUDA driver from the shared library."""
        version = self._get_cuda_driver_version()
        major, minor = version // 1_000, (version % 1_000) // 10
        return major, minor

    def get_topology_gpu_set(self, cpu_number: int) -> List[pointer]:
        """Retrieve the set of GPUs that have a CPU affinity with the given CPU number.
        ALL_PRODUCTS
        Supported on Linux only."""
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlSystemGetTopologyGpuSet")
        # First call will get the size
        ret = fn(cpu_number, byref(c_count), None)
        Return.check(ret)
        # call again with a buffer
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        ret = fn(cpu_number, byref(c_count), c_devices)
        Return.check(ret)
        return list(c_devices)
