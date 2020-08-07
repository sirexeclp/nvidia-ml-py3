from ctypes import c_uint, byref, c_ulonglong
from typing import Tuple

from pynvml3.enums import EnableState, NvLinkCapability, NvLinkErrorCounter
from pynvml3.errors import Return
from pynvml3.structs import PciInfo, NvLinkUtilizationControl


class NvLink:
    """Methods that NVML can perform on NVLINK enabled devices."""

    def __init__(self, device, link_id):
        self.device = device
        self.link = link_id
        self.lib = self.device.lib

    def freeze_utilization_counter(self, counter: int, freeze: EnableState) -> None:
        """
        Freeze the NVLINK utilization counters Both the receive and transmit counters are operated on by this function

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be frozen (0 or 1).
        @type counter: int
        @param freeze: NVML_FEATURE_ENABLED = freeze the receive and transmit counters
            NVML_FEATURE_DISABLED = unfreeze the receive and transmit counters
        @type freeze: EnableState
        @return: None
        @rtype: None
        """
        fn = self.lib.get_function_pointer("nvmlDeviceFreezeNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(self.link), c_uint(counter), freeze.as_c_type())
        Return.check(ret)

    def get_capability(self, link: int, capability: NvLinkCapability) -> bool:
        """
        Retrieves the requested capability from the device's NvLink for the link specified.
        Please refer to the nvmlNvLinkCapability_t structure for the specific caps that can be queried.
        The return value should be treated as a boolean.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param capability: Specifies the nvmlNvLinkCapability_t to be queried
        @type capability: NvLinkCapability
        @return: A boolean for the queried capability indicating that feature is available
        @rtype: bool
        """
        cap_result = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkCapability")
        ret = fn(self.device.handle, c_uint(link), capability.as_c_type(), byref(cap_result))
        Return.check(ret)
        return bool(cap_result.value)

    def get_error_counter(self, link: int, counter: NvLinkErrorCounter) -> int:
        """ Retrieves the specified error counter value.
        Please refer to nvmlNvLinkErrorCounter_t for error counters that are available

        PASCAL_OR_NEWER
        @return: error counter value
        @rtype: int
        """
        counter_value = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkErrorCounter")
        ret = fn(self.device.handle, c_uint(link), counter.as_c_type(), byref(counter_value))
        Return.check(ret)
        return counter_value.value

    def get_remote_pci_info(self, link: int) -> PciInfo:
        """Retrieves the PCI information for the remote node on a NvLink link
        Note: pciSubSystemId is not filled in this function and is indeterminate

        PASCAL_OR_NEWER"""
        pci_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkRemotePciInfo")
        ret = fn(self.device.handle, c_uint(link), byref(pci_info))
        Return.check(ret)
        return pci_info

    def get_state(self, link: int) -> EnableState:
        """Retrieves the state of the device's NvLink for the link specified

        PASCAL_OR_NEWER"""
        is_active = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkState")
        ret = fn(self.device.handle, c_uint(link), byref(is_active))
        Return.check(ret)
        return EnableState(is_active.value)

    def get_utilization_control(self, link: int, counter: int) -> NvLinkUtilizationControl:
        """Get the NVLINK utilization counter control information for the specified counter, 0 or 1.
        Please refer to nvmlNvLinkUtilizationControl_t for the structure definition.

        PASCAL_OR_NEWER
        @param link: Specifies the NvLink link to be queried
        @type link: int
        @param counter: Specifies the counter that should be set (0 or 1).
        @type counter: int
        @return: NvLink utilization counter control information for the specified counter
        @rtype: NvLinkUtilizationControl
        """

        control = NvLinkUtilizationControl()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationControl")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(control))
        Return.check(ret)
        return control

    def get_utilization_counter(self, link: int, counter: int) -> Tuple[int ,int]:
        rx_counter, tx_counter = c_ulonglong(), c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(rx_counter), byref(tx_counter))
        Return.check(ret)
        return rx_counter.value, tx_counter.value

    def get_version(self, link: int) -> int:
        version = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetNvLinkVersion")
        ret = fn(self.device.handle, c_uint(link), byref(version))
        Return.check(ret)
        return version.value

    def reset_error_counters(self, link: int) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceResetNvLinkErrorCounters")
        ret = fn(self.device.handle, c_uint(link))
        Return.check(ret)

    def reset_utilization_counter(self, link: int, counter: int) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceResetNvLinkUtilizationCounter")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter))
        Return.check(ret)

    def set_utilization_control(self, link: int, counter: int,
                                        control: NvLinkUtilizationControl, reset: bool) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetNvLinkUtilizationControl")
        ret = fn(self.device.handle, c_uint(link), c_uint(counter), byref(control), c_uint(reset))
        Return.check(ret)