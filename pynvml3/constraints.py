from pynvml3 import Device
from pynvml3.enums import ClockType

"""This module contains classes to Manage resource constraints on GPUS.
All classes are implemented as context managers, so the constraints will be applied when entering the context and
reset, when leaving it."""


class PowerLimit:
    """ A class to manage power-limits in a nice way."""

    def __init__(self, device: Device, power_limit: int, set_default: bool = False):
        self.device = device
        self.power_limit = power_limit
        self.set_default = set_default
        self.default_value = None

    def __enter__(self):
        if self.power_limit is None:
            return
        if self.set_default:
            self.default_value = self.device.get_power_management_default_limit()
        else:
            self.default_value = self.device.get_power_management_limit()

        self.device.set_power_management_limit(self.power_limit)
        print(f"Set power-limit to {self.power_limit}. Actual: {self.device.get_power_management_limit()}.")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.power_limit is None:
            return
        self.device.set_power_management_limit(self.default_value)
        print(f"Reset power-limit to default value ({self.default_value}).")


class ApplicationClockLimit:
    """A class to manage clock-limits in a nice way."""

    def __init__(self, device: Device, mem_clock: int, sm_clock: int, set_default: bool = True):
        self.device = device
        self.mem_clock = mem_clock
        self.sm_clock = sm_clock
        self.set_default = set_default
        self.default_mem_clock = None
        self.default_sm_clock = None

    def __enter__(self):
        if self.mem_clock is None or self.sm_clock is None:
            return
        if not self.set_default:
            self.default_mem_clock = self.device.get_applications_clock(ClockType.MEM)
            self.default_sm_clock = self.device.get_applications_clock(ClockType.SM)
        self.device.set_applications_clocks(self.mem_clock, self.sm_clock)
        print(f"Set application clocks: {self.mem_clock}|{self.device.get_applications_clock(ClockType.MEM)}mem "
              f"{self.sm_clock}|{self.device.get_applications_clock(ClockType.SM)}sm")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mem_clock is None or self.sm_clock is None:
            return
        if self.set_default:
            self.device.reset_applications_clocks()
        else:
            self.device.set_applications_clocks(self.default_mem_clock, self.default_sm_clock)
        print(f"Reset application clocks: {self.device.get_applications_clock(ClockType.MEM)}mem "
              f"{self.device.get_applications_clock(ClockType.SM)}sm")


class LockedClocks:
    """A class to manage locked clocks in a nice way."""

    def __init__(self, device: Device, min_clock: int, max_clock: int):
        self.device = device
        self.min_clock = min_clock
        self.max_clock = max_clock

    def __enter__(self):
        if self.min_clock is not None and self.max_clock is not None:
            self.device.set_gpu_locked_clocks(self.min_clock, self.max_clock)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.min_clock is not None and self.max_clock is not None:
            self.device.reset_gpu_locked_clocks()
