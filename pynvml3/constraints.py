from pynvml3 import Device
from pynvml3.enums import ClockType

"""This module contains classes to Manage resource constraints on GPUS.
All classes are implemented as context managers, so the constraints will be applied when entering the context and
reset, when leaving it."""


class PowerLimit:
    """A class to manage power-limits in a nice way."""

    def __init__(
        self, device: Device, power_limit: int, set_default: bool = False, check=True
    ):
        """Set a power-limit for the given device.
        Args:
            device: a gpu device object
            power_limit: the power-limit in milliwatts
            set_default: if set to True the default limit will be applied
                on exit instead of the value, that was set before
            check: if set to True, check, that the power-limit was applied,
                raise if it failed
        """
        self.device = device

        (
            self.min_limit,
            self.max_limit,
        ) = self.device.get_power_management_limit_constraints()
        if power_limit is None or self.min_limit <= power_limit <= self.max_limit:
            self.power_limit = power_limit
        else:
            raise ValueError(
                f"PowerLimit must be in range {self.min_limit} - {self.max_limit} (inclusive)."
                f"But was {power_limit}"
            )

        self.set_default = set_default
        self.default_value = None
        self.check = check

    def __enter__(self):
        if self.power_limit is None:
            self.device.set_power_management_limit(self.max_limit)
            return
        if self.set_default:
            self.default_value = self.device.get_power_management_default_limit()
        else:
            self.default_value = self.device.get_power_management_limit()

        self.device.set_power_management_limit(self.power_limit)
        if self.check and (self.power_limit != self.device.get_enforced_power_limit()):
            raise RuntimeError(
                f"Could not set power-limit. Set power-limit to {self.power_limit}."
                + f" Actual: {self.device.get_enforced_power_limit()}."
            )
        print(
            f"Set power-limit to {self.power_limit}. Actual: {self.device.get_enforced_power_limit()}."
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.power_limit is None:
            return
        self.device.set_power_management_limit(self.default_value)
        print(f"Reset power-limit to default value ({self.default_value}).")


class ApplicationClockLimit:
    """A class to manage application clock-limits in a nice way."""

    def __init__(
        self,
        device: Device,
        mem_clock: int,
        sm_clock: int,
        set_default: bool = True,
        check=True,
    ):
        """Set application clocks for the given device.
        Args:
            device: a gpu device object
            mem_clock: the memory clock frequency in Mhz
            sm_clock: the sm clock frequency in Mhz
            set_default: if set to True the default limit will be applied
                on exit instead of the value, that was set before
            check: if set to True, check, that the clocks have been applied,
                raise if it failed
        """
        self.device = device
        self.mem_clock = mem_clock
        self.sm_clock = sm_clock
        self.set_default = set_default
        self.default_mem_clock = None
        self.default_sm_clock = None
        self.check = check

    def __enter__(self):
        if self.mem_clock is None or self.sm_clock is None:
            self.device.reset_applications_clocks()
            return
        if not self.set_default:
            self.default_mem_clock = self.device.get_applications_clock(ClockType.MEM)
            self.default_sm_clock = self.device.get_applications_clock(ClockType.SM)
        self.device.set_applications_clocks(self.mem_clock, self.sm_clock)

        mem_clock = self.device.get_applications_clock(ClockType.MEM)
        sm_clock = self.device.get_applications_clock(ClockType.SM)

        if self.check and (self.mem_clock != mem_clock or self.sm_clock != sm_clock):
            raise RuntimeError(
                f"Could not set application clocks:"
                f"Set application clocks: {self.mem_clock}|{mem_clock}mem "
                f"{self.sm_clock}|{sm_clock}sm"
            )

        print(
            f"Set application clocks: {self.mem_clock}|{mem_clock}mem "
            f"{self.sm_clock}|{sm_clock}sm"
        )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.mem_clock is None or self.sm_clock is None:
            return
        if self.set_default:
            self.device.reset_applications_clocks()
        else:
            self.device.set_applications_clocks(
                self.default_mem_clock, self.default_sm_clock
            )
        print(
            f"Reset application clocks: {self.device.get_applications_clock(ClockType.MEM)}mem "
            f"{self.device.get_applications_clock(ClockType.SM)}sm"
        )


class LockedClocks:
    """A class to manage locked clocks in a nice way."""

    def __init__(self, device: Device, min_clock: int, max_clock: int, check=True):
        """Set locked clocks for the given device.

        Args:
            device:
            min_clock:
            max_clock:
        """
        self.device = device
        self.min_clock = min_clock
        self.max_clock = max_clock
        self.check = check

    def __enter__(self):
        if self.min_clock is not None and self.max_clock is not None:
            self.device.set_gpu_locked_clocks(self.min_clock, self.max_clock)
            max_clock = self.device.get_clock(ClockType.SM, ClockId.CUSTOMER_BOOST_MAX)
            if self.check and self.max_clock != max_clock:
                raise RuntimeError(
                    f"Could not set LockedClocks! ({max_clock}/{self.max_clock})"
                )

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.min_clock is not None and self.max_clock is not None:
            self.device.reset_gpu_locked_clocks()
