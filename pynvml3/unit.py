from ctypes import c_uint, byref
from typing import List

from pynvml3.device import Device
from pynvml3.enums import TemperatureSensors, LedColor, TemperatureType
from pynvml3.errors import Return
from pynvml3.structs import CUnitPointer, UnitInfo, LedState, PSUInfo, UnitFanSpeeds, CDevicePointer


class Unit:
    """Queries that NVML can perform against each unit.

    Notes:
        For S-class systems only.

    """

    def __init__(self, lib: "pynvml3.pynvml.NVMLLib", handle: "pynvml3.structs.CUnitPointer"):
        """Acquire the handle for a particular unit, based on its index.

        Note:
            Valid indices are derived from the unitCount returned by
            :func:`Unit.get_count()`. For example, if unitCount is 2 the valid
            indices are 0 and 1, corresponding to UNIT 0 and UNIT 1.

        Args:
            lib: a reference to the NVMLLib object
            index: The index of the target unit, >= 0 and < unitCount

        """

        self.lib = lib
        self.handle = handle


    def get_unit_info(self) -> UnitInfo:
        """Retrieves the static information associated with a unit.


        Returns:
            UnitInfo: the unit information which consists of:

            - Firmware version.
            - Product identifier.
            - Product name.
            - Product serial number.
        """
        c_info = UnitInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetUnitInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_led_state(self) -> LedState:
        """Retrieves the LED state associated with this unit.

        Returns: the current LED state

        """
        c_state = LedState()
        fn = self.lib.get_function_pointer("nvmlUnitGetLedState")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return c_state

    def get_psu_info(self) -> PSUInfo:
        """Retrieves the PSU stats for the unit.

        Returns:
            PSUInfo: the PSU information, which consists of:

            - PSU current (A).
            - PSU power draw (W).
            - The power supply state.
            - PSU voltage (V).

        """
        c_info = PSUInfo()
        fn = self.lib.get_function_pointer("nvmlUnitGetPsuInfo")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_temperature(self, temperature_type: TemperatureType) -> int:
        """Retrieves the temperature readings for the unit, in degrees C.

        Note:
            Depending on the product, readings may be available for
            intake (type=0), exhaust (type=1) and board (type=2).

        Args:
            temperature_type (TemperatureSensors):

        Returns: the intake temperature in °C

        """
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlUnitGetTemperature")
        ret = fn(self.handle, c_uint(temperature_type.value), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_fan_speed_info(self) -> UnitFanSpeeds:
        """Retrieves the fan speed readings for the unit.

        Returns: the fan speed information

        """
        c_speeds = UnitFanSpeeds()
        fn = self.lib.get_function_pointer("nvmlUnitGetFanSpeedInfo")
        ret = fn(self.handle, byref(c_speeds))
        Return.check(ret)
        return c_speeds

    def get_device_count(self) -> int:
        """Retrieves the number of GPU devices
        that are attached to the specified unit.

        Returns: the number of attached GPU devices

        """
        c_count = c_uint(0)
        # query the unit to determine device count
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), None)
        if ret == Return.ERROR_INSUFFICIENT_SIZE.value:
            ret = Return.SUCCESS.value
        Return.check(ret)
        return c_count.value

    def get_devices(self) -> List["Device"]:
        """Retrieves the set of GPU devices
        that are attached to the specified unit.

        Returns: a list of the attached GPU devices

        """
        c_count = c_uint(self.get_device_count())
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        fn = self.lib.get_function_pointer("nvmlUnitGetDevices")
        ret = fn(self.handle, byref(c_count), c_devices)
        Return.check(ret)
        return [Device(self.lib, dev) for dev in c_devices]

    def set_led_state(self, color: LedColor) -> None:
        """Set the LED state for the unit.
        The LED can be either green (0) or amber (1).

        Args:
            color: The target LED color

        Note:
            Requires root/admin permissions.

            This operation takes effect immediately.

            Current S-Class products don't provide unique LEDs for each unit.
            As such, both front and back LEDs will be toggled in unison
            regardless of which unit is specified with this command.

        Notes:
            For S-class products.

        """
        fn = self.lib.get_function_pointer("nvmlUnitSetLedState")
        ret = fn(self.handle, color.value)
        Return.check(ret)
