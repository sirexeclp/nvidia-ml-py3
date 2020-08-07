from ctypes import c_uint, byref, pointer
from typing import List

from pynvml3.device import Device
from pynvml3.enums import TemperatureSensors, LedColor
from pynvml3.errors import Return
# from pynvml3.pynvml import NvmlBase, NVMLLib
from pynvml3.structs import CUnitPointer, UnitInfo, LedState, PSUInfo, UnitFanSpeeds, CDevicePointer


class Unit():
    """
    Unit get functions
    """

    def __init__(self, index):
        super().__init__()
        self.handle = self._get_handle_by_index(index)

    def _get_handle_by_index(self, index: int) -> pointer:
        c_index = c_uint(index)
        unit = CUnitPointer()
        fn = self.lib.get_function_pointer("nvmlUnitGetHandleByIndex")
        ret = fn(c_index, byref(unit))
        Return.check(ret)
        return unit

    @staticmethod
    def get_count() -> int:
        c_count = c_uint()
        fn = NVMLLib().get_function_pointer("nvmlUnitGetCount")
        ret = fn(byref(c_count))
        Return.check(ret)
        return c_count.value

    def get_unit_info(self) -> UnitInfo:
        c_info = UnitInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetUnitInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_led_state(self) -> LedState:
        c_state = LedState()
        fn = self.lib.get_function_pointer("nvmlUnitGetLedState")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return c_state

    def get_psu_info(self) -> PSUInfo:
        c_info = PSUInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetPsuInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_temperature(self, temperature_type: TemperatureSensors) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlUnitGetTemperature")
        ret = fn(self.handle, c_uint(temperature_type.value), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_fan_speed_info(self) -> UnitFanSpeeds:
        c_speeds = UnitFanSpeeds()
        fn = self.lib.get_function_pointer("nvmlUnitGetFanSpeedInfo")
        ret = fn(self.handle, byref(c_speeds))
        Return.check(ret)
        return c_speeds

    # added to API
    def get_device_count(self) -> int:
        c_count = c_uint(0)
        # query the unit to determine device count
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), None)
        if ret == Return.ERROR_INSUFFICIENT_SIZE.value:
            ret = Return.SUCCESS.value
        Return.check(ret)
        return c_count.value

    def get_devices(self) -> List["Device"]:
        c_count = c_uint(self.get_device_count())
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), c_devices)
        Return.check(ret)
        return [Device(dev) for dev in c_devices]

    # Set functions
    def set_led_state(self, color) -> None:
        fn = self.lib.get_function_pointer("nvmlUnitSetLedState")
        ret = fn(self.handle, LedColor(color))
        Return.check(ret)