import math
import os
from ctypes import (
    c_uint,
    byref,
    c_char_p,
    c_int,
    c_ulonglong,
    create_string_buffer,
    sizeof,
    c_ulong,
    pointer,
)
from typing import Tuple, List

from pynvml3.constants import VALUE_NOT_AVAILABLE_ulonglong
from pynvml3.enums import (
    ClockType,
    ClockId,
    EccCounterType,
    RestrictedAPI,
    EnableState,
    ComputeMode,
    DriverModel,
    GpuOperationMode,
    FieldId,
    BrandType,
    InfoRom,
    TemperatureSensors,
    TemperatureThresholds,
    PowerState,
    MemoryErrorType,
    MemoryLocation,
    PageRetirementCause,
    SamplingType,
    ValueType,
    PerfPolicyType,
    PcieUtilCounter,
    GpuTopologyLevel,
)
from pynvml3.errors import Return, NVMLError, NVMLErrorNotFound
from pynvml3.event_set import EventSet
from pynvml3.flags import EventType
from pynvml3.nvlink import NvLink
from pynvml3.structs import (
    CDevicePointer,
    FieldValue,
    PciInfo,
    Memory,
    BAR1Memory,
    EccErrorCounts,
    Utilization,
    ProcessInfo,
    AccountingStats,
    BridgeChipHierarchy,
    RawSample,
    ViolationTime,
    Sample,
)


class Device:
    """Queries that NVML can perform against each device.

    In each case the device is identified with an nvmlDevice_t handle.
    This handle is obtained by calling one of nvmlDeviceGetHandleByIndex(),
    nvmlDeviceGetHandleBySerial(), nvmlDeviceGetHandleByPciBusId() or nvmlDeviceGetHandleByUUID().
    """

    INFOROM_VERSION_BUFFER_SIZE = 16
    UUID_BUFFER_SIZE = 80
    NAME_BUFFER_SIZE = 64
    SERIAL_BUFFER_SIZE = 30
    VBIOS_VERSION_BUFFER_SIZE = 32
    PCI_BUS_ID_BUFFER_SIZE = 16

    def __init__(self, lib: "NVMLLib", handle: pointer):
        self.lib = lib
        self.handle = handle

    #
    # New Methods
    #
    #################################
    #        Device Queries         #
    #################################

    def get_clock(self, clock_type: ClockType, clock_id: ClockId) -> int:
        """
        Retrieves the clock speed for the clock specified by the clock type and clock ID.

        KEPLER_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @param clock_id: Identify which clock in the domain to query
        @type clock_id: ClockId
        @return: clock in MHz
        @rtype: int
        """
        clock_mhz = c_uint()
        self.lib.nvmlDeviceGetClock(
            self.handle, clock_type.as_c_type(), clock_id.as_c_type(), byref(clock_mhz)
        )
        return clock_mhz.value

    def get_cuda_compute_capability(self) -> Tuple[int, int]:
        """

        @return:
        @rtype:
        """
        major, minor = c_int(), c_int()
        fn = self.lib.nvmlDeviceGetCudaComputeCapability(
            self.handle, byref(major), byref(minor)
        )
        return major.value, minor.value

    def get_max_customer_boost_clock(self, clock_type: ClockType) -> int:
        """Retrieves the customer defined maximum boost clock speed for the given clock type."""
        clock_mhz = c_uint()
        self.lib.nvmlDeviceGetMaxCustomerBoostClock(
            self.handle, clock_type.as_c_type(), byref(clock_mhz)
        )
        return clock_mhz.value

    def get_total_energy_consumption(self) -> int:
        """Retrieves total energy consumption for this GPU in millijoules (mJ)
        since the driver was last reloaded.

        VOLTA_OR_NEWER
        @return: energy consumption for this GPU in millijoules (mJ)
        @rtype: int
        """
        energy = c_ulonglong()
        fn = self.lib.nvmlDeviceGetTotalEnergyConsumption(self.handle, byref(energy))
        return energy.value

    #################################
    #          Drain State          #
    #################################

    #################################
    #        Device Commands        #
    #################################
    """
        This chapter describes NVML operations that change the state of the device.
        Each of these requires root/admin access.
        Non-admin users will see an NVML_ERROR_NO_PERMISSION error code when invoking any of these methods. 
    """

    def clear_ecc_error_counts(self, counterType: EccCounterType) -> None:
        """
        Clear the ECC error and other memory error counts for the device.
        KEPLER_OR_NEWER% Only applicable to devices with ECC.
        Requires NVML_INFOROM_ECC version 2.0 or higher to clear aggregate location-based ECC counts.
        Requires NVML_INFOROM_ECC version 1.0 or higher to clear all other ECC counts.
        Requires root/admin permissions.
        Requires ECC Mode to be enabled.
        Sets all of the specified ECC counters to 0, including both detailed and total counts.
        This operation takes effect immediately.
        See nvmlMemoryErrorType_t for details on available counter types.
        See also:
        nvmlDeviceGetDetailedEccErrors()
        nvmlDeviceGetTotalEccErrors()

        @param counterType:
        @type counterType:
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceClearEccErrorCounts")
        ret = fn(self.handle, counterType.as_c_type())
        Return.check(ret)

    def reset_gpu_locked_clocks(self) -> None:
        """
        @summary: Resets the gpu clock to the default value
        This is the gpu clock that will be used after system reboot or driver reload.
        Default values are idle clocks, but the current values can be changed using
        nvmlDeviceSetApplicationsClocks.
        VOLTA_OR_NEWER
        """
        fn = self.lib.get_function_pointer("nvmlDeviceResetGpuLockedClocks")
        ret = fn(self.handle)
        Return.check(ret)

    def set_api_restriction(
        self, api_type: RestrictedAPI, is_restricted: EnableState
    ) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetAPIRestriction")
        ret = fn(self.handle, api_type.as_c_type(), is_restricted.as_c_type())
        Return.check(ret)

    # Added in 4.304
    def set_applications_clocks(
        self, max_mem_clock_mhz: int, max_graphics_clock_mhz: int
    ) -> None:
        self.lib.nvmlDeviceSetApplicationsClocks(
            self.handle, c_uint(max_mem_clock_mhz), c_uint(max_graphics_clock_mhz)
        )

    def set_compute_mode(self, mode: ComputeMode) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetComputeMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_driver_model(self, model: DriverModel) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetDriverModel")
        ret = fn(self.handle, model.as_c_type())
        Return.check(ret)

    def set_ecc_mode(self, mode: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetEccMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_gpu_locked_clocks(
        self, min_gpu_clock_mhz: int, max_gpu_clock_mhz: int
    ) -> None:
        """
        Set clocks that device will lock to.
        Sets the clocks that the device will be running at to the value in the range of minGpuClockMHz
        to maxGpuClockMHz. Setting this will supercede application clock values and
        take effect regardless if a cuda app is running. See /ref nvmlDeviceSetApplicationsClocks
        Can be used as a setting to request constant performance.
        Requires root/admin permissions.
        After system reboot or driver reload applications clocks go back to their default value.
        See nvmlDeviceResetGpuLockedClocks.

        VOLTA_OR_NEWER
        @param min_gpu_clock_mhz: minimum gpu clock in MHz
        @type min_gpu_clock_mhz: int
        @param max_gpu_clock_mhz: maximum gpu clock in MHz
        @type max_gpu_clock_mhz: int
        """
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuLockedClocks")
        ret = fn(self.handle, c_uint(min_gpu_clock_mhz), c_uint(max_gpu_clock_mhz))
        Return.check(ret)

    # Added in 4.304
    def set_gpu_operation_mode(self, mode: GpuOperationMode) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetGpuOperationMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def set_persistence_mode(self, enable_state: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetPersistenceMode")
        ret = fn(self.handle, enable_state.as_c_type())
        Return.check(ret)

    # Added in 4.304
    def set_power_management_limit(self, limit: int) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetPowerManagementLimit")
        ret = fn(self.handle, c_uint(limit))
        Return.check(ret)

    #################################
    #        NvLink Methods         #
    #################################

    def get_nvlink(self, link_id: int) -> "NvLink":
        """
        Create an NvLink object, which provides nvlink methods.
        @param link_id: the id of the nvlink
        @type link_id: int
        @return: NvLink object
        @rtype: NvLink
        """
        return NvLink(self, link_id)

    #################################
    #      Field Value Queries      #
    #################################

    def get_field_values(self, values_count: int, field_id: FieldId) -> FieldValue:
        """Request values for a list of fields for a device.
        This API allows multiple fields to be queried at once.
        If any of the underlying fieldIds are populated by the same driver call,
        the results for those field IDs will be populated from a single call
        rather than making a driver call for each fieldId."""

        fn = self.lib.get_function_pointer("nvmlDeviceGetFieldValues")
        field_value: FieldValue = FieldValue()
        field_value.unused = 0
        field_value.fieldId = field_id.as_c_type()
        ret = fn(self.handle, c_int(values_count), byref(field_value))
        Return.check(ret)
        return field_value

    #################################
    #          Old Methods          #
    #################################

    def get_name(self) -> str:
        c_name = create_string_buffer(Device.NAME_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetName")
        ret = fn(self.handle, c_name, c_uint(Device.NAME_BUFFER_SIZE))
        Return.check(ret)
        return c_name.value.decode("UTF-8")

    def get_board_id(self) -> int:
        c_id = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBoardId")
        ret = fn(self.handle, byref(c_id))
        Return.check(ret)
        return c_id.value

    def get_multi_gpu_board(self) -> bool:
        c_multiGpu = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMultiGpuBoard")
        ret = fn(self.handle, byref(c_multiGpu))
        Return.check(ret)
        return bool(c_multiGpu.value)

    def get_brand(self) -> BrandType:
        c_type = BrandType.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBrand")
        ret = fn(self.handle, byref(c_type))
        Return.check(ret)
        return BrandType(c_type.value)

    def get_serial(self) -> str:
        c_serial = create_string_buffer(Device.SERIAL_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSerial")
        ret = fn(self.handle, c_serial, c_uint(Device.SERIAL_BUFFER_SIZE))
        Return.check(ret)
        return c_serial.value.decode("UTF-8")

    def get_cpu_affinity(self) -> List[int]:
        cpu_set_size = math.ceil(os.cpu_count() / sizeof(c_ulong))
        affinity_array = c_ulong * cpu_set_size
        c_affinity = affinity_array()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCpuAffinity")
        ret = fn(self.handle, c_uint(cpu_set_size), byref(c_affinity))
        Return.check(ret)
        return list(c_affinity)

    def set_cpu_affinity(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetCpuAffinity")
        ret = fn(self.handle)
        Return.check(ret)
        return None

    def clear_cpu_affinity(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceClearCpuAffinity")
        ret = fn(self.handle)
        Return.check(ret)
        return None

    def get_minor_number(self) -> int:
        c_minor_number = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMinorNumber")
        ret = fn(self.handle, byref(c_minor_number))
        Return.check(ret)
        return c_minor_number.value

    def get_uuid(self) -> str:
        c_uuid = create_string_buffer(Device.UUID_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetUUID")
        ret = fn(self.handle, c_uuid, c_uint(Device.UUID_BUFFER_SIZE))
        Return.check(ret)
        return c_uuid.value.decode("UTF-8")

    def get_inforom_version(self, info_rom_object: InfoRom) -> str:
        c_version = create_string_buffer(Device.INFOROM_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomVersion")
        ret = fn(
            self.handle,
            InfoRom.c_type(info_rom_object.value),
            c_version,
            c_uint(Device.INFOROM_VERSION_BUFFER_SIZE),
        )
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 4.304
    def get_inforom_image_version(self) -> str:
        c_version = create_string_buffer(Device.INFOROM_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomImageVersion")
        ret = fn(self.handle, c_version, c_uint(Device.INFOROM_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    # Added in 4.304
    def get_inforom_configuration_checksum(self) -> int:
        c_checksum = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetInforomConfigurationChecksum")
        ret = fn(self.handle, byref(c_checksum))
        Return.check(ret)
        return c_checksum.value

    # Added in 4.304
    def validate_inforom(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceValidateInforom")
        ret = fn(self.handle)
        Return.check(ret)

    def get_display_mode(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def get_display_active(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDisplayActive")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def get_persistence_mode(self) -> EnableState:
        c_state = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPersistenceMode")
        ret = fn(self.handle, byref(c_state))
        Return.check(ret)
        return EnableState(c_state.value)

    def get_pci_info(self) -> PciInfo:
        c_info = PciInfo()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPciInfo_v2")
        ret = fn(self.handle, byref(c_info))
        Return.check(ret)
        return c_info

    def get_clock_info(self, clock_type: ClockType) -> int:
        """
        Retrieves the current clock speeds for the device.
        FERMI_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @return: the clock speed in MHz
        @rtype: int
        """
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetClockInfo")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 2.285
    def get_max_clock_info(self, clock_type: ClockType) -> int:
        """
        Retrieves the maximum clock speeds for the device.
        FERMI_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @return: the clock speed in MHz
        @rtype: int
        """
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxClockInfo")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def get_applications_clock(self, clock_type: ClockType) -> int:
        """Retrieves the current setting of a clock that applications will use
        unless an overspec situation occurs. Can be changed using nvmlDeviceSetApplicationsClocks.
        KEPLER_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @return: the clock in MHz
        @rtype: int
        """
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetApplicationsClock")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 5.319
    def get_default_applications_clock(self, clock_type: ClockType) -> int:
        """
        Retrieves the default applications clock that GPU boots with or defaults to after nvmlDeviceResetApplicationsClocks call.
        KEPLER_OR_NEWER
        @param clock_type: Identify which clock domain to query
        @type clock_type: ClockType
        @return: the default clock in MHz
        @rtype: int
        """
        c_clock = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDefaultApplicationsClock")
        ret = fn(self.handle, clock_type.as_c_type(), byref(c_clock))
        Return.check(ret)
        return c_clock.value

    # Added in 4.304
    def get_supported_memory_clocks(self) -> List[int]:
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedMemoryClocks")
        ret = fn(self.handle, byref(c_count), None)

        result = Return(ret)
        if result == Return.SUCCESS:
            # special case, no clocks
            return []
        elif result == Return.ERROR_INSUFFICIENT_SIZE:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_clocks)
            Return.check(ret)
            return list(c_clocks)
        else:
            # error case
            raise NVMLError.from_return(ret)

    # Added in 4.304
    def get_supported_graphics_clocks(self, memory_clock_mhz: int) -> List[int]:
        # first call to get the size
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedGraphicsClocks")
        ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), None)
        result = Return(ret)

        if result == Return.SUCCESS:
            # special case, no clocks
            return []
        elif result == Return.ERROR_INSUFFICIENT_SIZE:
            # typical case
            clocks_array = c_uint * c_count.value
            c_clocks = clocks_array()

            # make the call again
            ret = fn(self.handle, c_uint(memory_clock_mhz), byref(c_count), c_clocks)
            Return.check(ret)
            return list(c_clocks)
        else:
            # error case
            raise NVMLError(ret)

    def get_fan_speed(self) -> int:
        c_speed = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetFanSpeed_v2")
        fan = c_uint(0)
        ret = fn(self.handle, fan, byref(c_speed))
        Return.check(ret)
        return c_speed.value

    def get_temperature(self, sensor: TemperatureSensors) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperature")
        ret = fn(self.handle, sensor.as_c_type(), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    def get_temperature_threshold(self, threshold: TemperatureThresholds) -> int:
        c_temp = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTemperatureThreshold")
        ret = fn(self.handle, threshold.as_c_type(), byref(c_temp))
        Return.check(ret)
        return c_temp.value

    # DEPRECATED use nvmlDeviceGetPerformanceState
    def get_power_state(self) -> PowerState:
        """
        Warnings:
            deprecated
            use :func:`Device.get_performance_state`
        """
        power_state = PowerState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerState")
        ret = fn(self.handle, byref(power_state))
        Return.check(ret)
        return PowerState(power_state.value)

    def get_performance_state(self) -> PowerState:
        performance_state = PowerState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPerformanceState")
        ret = fn(self.handle, byref(performance_state))
        Return.check(ret)
        return PowerState(performance_state.value)

    def get_power_management_mode(self) -> EnableState:
        pcap_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementMode")
        ret = fn(self.handle, byref(pcap_mode))
        Return.check(ret)
        return EnableState(pcap_mode.value)

    def get_power_management_limit(self) -> int:
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 4.304
    def get_power_management_limit_constraints(self) -> Tuple[int, int]:
        c_minLimit = c_uint()
        c_maxLimit = c_uint()
        fn = self.lib.get_function_pointer(
            "nvmlDeviceGetPowerManagementLimitConstraints"
        )
        ret = fn(self.handle, byref(c_minLimit), byref(c_maxLimit))
        Return.check(ret)
        return c_minLimit.value, c_maxLimit.value

    # Added in 4.304
    def get_power_management_default_limit(self) -> int:
        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerManagementDefaultLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    # Added in 331
    def get_enforced_power_limit(self) -> int:
        """Get the effective power limit that the driver enforces
        after taking into account all limiters.

        Note:
            This can be different from the :func:`Device.get_power_management_limit`
            if other limits are set elsewhere.
            This includes the out of band power limit interface.

        Returns: the power management limit in milliwatts

        """

        c_limit = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEnforcedPowerLimit")
        ret = fn(self.handle, byref(c_limit))
        Return.check(ret)
        return c_limit.value

    def get_power_usage(self) -> int:
        milli_watts = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPowerUsage")
        ret = fn(self.handle, byref(milli_watts))
        Return.check(ret)
        return milli_watts.value

    # Added in 4.304
    def get_gpu_operation_mode(self) -> Tuple[GpuOperationMode, GpuOperationMode]:
        c_currState = GpuOperationMode.c_type()
        c_pendingState = GpuOperationMode.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetGpuOperationMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return GpuOperationMode(c_currState.value), GpuOperationMode(
            c_pendingState.value
        )

    # Added in 4.304
    def get_current_gpu_operation_mode(self) -> GpuOperationMode:
        return self.get_gpu_operation_mode()[0]

    # Added in 4.304
    def get_pending_gpu_operation_mode(self) -> GpuOperationMode:
        return self.get_gpu_operation_mode()[1]

    def get_memory_info(self) -> Memory:
        c_memory = Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryInfo")
        ret = fn(self.handle, byref(c_memory))
        Return.check(ret)
        return c_memory

    def get_bar1_memory_info(self) -> BAR1Memory:
        c_bar1_memory = BAR1Memory()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBAR1MemoryInfo")
        ret = fn(self.handle, byref(c_bar1_memory))
        Return.check(ret)
        return c_bar1_memory

    def get_compute_mode(self) -> ComputeMode:
        c_mode = ComputeMode.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return ComputeMode(c_mode.value)

    def get_ecc_mode(self) -> Tuple[EnableState, EnableState]:
        c_currState = EnableState.c_type()
        c_pendingState = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEccMode")
        ret = fn(self.handle, byref(c_currState), byref(c_pendingState))
        Return.check(ret)
        return EnableState(c_currState.value), EnableState(c_pendingState.value)

    # added to API
    def get_current_ecc_mode(self) -> EnableState:
        return self.get_ecc_mode()[0]

    # added to API
    def get_pending_ecc_mode(self) -> EnableState:
        return self.get_ecc_mode()[1]

    def get_total_ecc_errors(
        self, error_type: MemoryErrorType, counter_type: EccCounterType
    ) -> int:
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTotalEccErrors")
        ret = fn(
            self.handle,
            error_type.as_c_type(),
            counter_type.as_c_type(),
            byref(c_count),
        )
        Return.check(ret)
        return c_count.value

    # This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter
    def get_detailed_ecc_errors(
        self, error_type: MemoryErrorType, counter_type: EccCounterType
    ) -> EccErrorCounts:
        """@deprecated: This is deprecated, instead use nvmlDeviceGetMemoryErrorCounter"""
        c_counts = EccErrorCounts()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDetailedEccErrors")
        ret = fn(
            self.handle,
            error_type.as_c_type(),
            counter_type.as_c_type(),
            byref(c_counts),
        )
        Return.check(ret)
        return c_counts

    # Added in 4.304
    def get_memory_error_counter(
        self,
        error_type: MemoryErrorType,
        counter_type: EccCounterType,
        location_type: MemoryLocation,
    ) -> int:
        c_count = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetMemoryErrorCounter")
        ret = fn(
            self.handle,
            error_type.as_c_type(),
            counter_type.as_c_type(),
            location_type.as_c_type(),
            byref(c_count),
        )
        Return.check(ret)
        return c_count.value

    def get_utilization_rates(self) -> Utilization:
        c_util = Utilization()
        fn = self.lib.get_function_pointer("nvmlDeviceGetUtilizationRates")
        ret = fn(self.handle, byref(c_util))
        Return.check(ret)
        return c_util

    def get_encoder_utilization(self) -> Tuple[int, int]:
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetEncoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return c_util.value, c_samplingPeriod.value

    def get_decoder_utilization(self) -> Tuple[int, int]:
        c_util = c_uint()
        c_samplingPeriod = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDecoderUtilization")
        ret = fn(self.handle, byref(c_util), byref(c_samplingPeriod))
        Return.check(ret)
        return c_util.value, c_samplingPeriod.value

    def get_pcie_replay_counter(self) -> int:
        c_replay = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieReplayCounter")
        ret = fn(self.handle, byref(c_replay))
        Return.check(ret)
        return c_replay.value

    def get_driver_model(self) -> Tuple[DriverModel, DriverModel]:
        c_currModel = DriverModel.c_type()
        c_pendingModel = DriverModel.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetDriverModel")
        ret = fn(self.handle, byref(c_currModel), byref(c_pendingModel))
        Return.check(ret)
        return DriverModel(c_currModel.value), DriverModel(c_pendingModel.value)

    # added to API
    def get_current_driver_model(self) -> DriverModel:
        return self.get_driver_model()[0]

    # added to API
    def get_pending_driver_model(self) -> DriverModel:
        return self.get_driver_model()[1]

    # Added in 2.285
    def get_vbios_version(self) -> str:
        c_version = create_string_buffer(Device.VBIOS_VERSION_BUFFER_SIZE)
        fn = self.lib.get_function_pointer("nvmlDeviceGetVbiosVersion")
        ret = fn(self.handle, c_version, c_uint(Device.VBIOS_VERSION_BUFFER_SIZE))
        Return.check(ret)
        return c_version.value.decode("UTF-8")

    def _get_running_processes(self, fn) -> List[ProcessInfo]:
        """

        Note:
            On Windows with the WDDM driver, usedGpuMemory is reported as None
            Code that processes this structure should check for None, I.E.::

                if (info.usedGpuMemory == None):
                    # handle the error
                    pass

            See NVML documentation for more information
        Args:
            fn ():

        Returns:

        """
        # first call to get the size
        c_count = c_uint(0)
        ret = fn(self.handle, byref(c_count), None)
        result = Return(ret)

        if result == Return.SUCCESS:
            # special case, no running processes
            return []
        elif result == Return.ERROR_INSUFFICIENT_SIZE:
            # typical case
            # oversize the array incase more processes are created
            c_count.value = c_count.value * 2 + 5
            proc_array = ProcessInfo * c_count.value
            c_procs = proc_array()

            # make the call again
            ret = fn(self.handle, byref(c_count), c_procs)
            Return.check(ret)

            procs = []
            for i in range(c_count.value):
                # use an alternative struct for this object
                obj: ProcessInfo = c_procs[i].get_friendly_object()
                if obj.usedGpuMemory == VALUE_NOT_AVAILABLE_ulonglong:
                    # special case for WDDM on Windows, see comment above
                    obj.usedGpuMemory = None
                procs.append(obj)
            return procs
        else:
            # error case
            raise NVMLError(ret)

    # Added in 2.285
    def get_compute_running_processes(self) -> List[ProcessInfo]:
        """

        Note:
            On Windows with the WDDM driver, usedGpuMemory is reported as None
            Code that processes this structure should check for None, I.E.::

                if (info.usedGpuMemory == None):
                    # handle the error
                    pass

            See NVML documentation for more information
        Returns:

        """
        fn = self.lib.get_function_pointer("nvmlDeviceGetComputeRunningProcesses")
        return self._get_running_processes(fn)

    def get_graphics_running_processes(self) -> List[ProcessInfo]:
        """

        Note:
            On Windows with the WDDM driver, usedGpuMemory is reported as None
            Code that processes this structure should check for None, I.E.::

                if (info.usedGpuMemory == None):
                    # handle the error
                    pass

            See NVML documentation for more information

        Returns:

        """
        fn = self.lib.get_function_pointer("nvmlDeviceGetGraphicsRunningProcesses")
        return self._get_running_processes(fn)

    def get_auto_boosted_clocks_enabled(self) -> Tuple[EnableState, EnableState]:
        """

        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        c_isEnabled = EnableState.c_type()
        c_defaultIsEnabled = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAutoBoostedClocksEnabled")
        ret = fn(self.handle, byref(c_isEnabled), byref(c_defaultIsEnabled))
        Return.check(ret)
        return EnableState(c_isEnabled.value), EnableState(c_defaultIsEnabled.value)

    def set_auto_boosted_clocks_enabled(self, enabled: EnableState) -> None:
        """

        @param enabled:
        @type enabled:
        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        fn = self.lib.get_function_pointer("nvmlDeviceSetAutoBoostedClocksEnabled")
        ret = fn(self.handle, enabled.as_c_type())
        Return.check(ret)

    def set_default_auto_boosted_clocks_enabled(
        self, enabled: EnableState, flags: int = 0
    ) -> None:
        """

        @param flags: unused
        @type flags: int
        @param enabled:
        @type enabled:
        @return:
        @rtype:
        @raise NVMLErrorNotSupported: if hardware doesn't support setting auto boosted clocks
        """
        fn = self.lib.get_function_pointer(
            "nvmlDeviceSetDefaultAutoBoostedClocksEnabled"
        )
        ret = fn(self.handle, enabled.as_c_type(), c_uint(flags))
        Return.check(ret)

    # Added in 4.304
    def reset_applications_clocks(self) -> None:
        """
        Resets the application clock to the default value
        This is the applications clock that will be used after system reboot or driver reload.
        Default value is constant, but the current value an be changed using
        nvmlDeviceSetApplicationsClocks. On Pascal and newer hardware, if clocks were previously
        locked with nvmlDeviceSetApplicationsClocks, this call will unlock clocks.
        This returns clocks their default behavior of automatically boosting
        above base clocks as thermal limits allow.
        FERMI_OR_NEWER_GF
        """
        fn = self.lib.get_function_pointer("nvmlDeviceResetApplicationsClocks")
        ret = fn(self.handle)
        Return.check(ret)

    #################################
    #         Event Methods         #
    #################################

    # Added in 2.285
    def register_events(self, event_types: EventType) -> "EventSet":
        """
        Starts recording of events on a specified devices and add the events to specified nvmlEventSet_t
        FERMI_OR_NEWER
        Ecc events are available only on ECC enabled devices (see nvmlDeviceGetTotalEccErrors)
        Power capping events are available only on Power Management enabled devices
        (see nvmlDeviceGetPowerManagementMode)
        For Linux only.
        IMPORTANT: Operations on set are not thread safe
        This call starts recording of events on specific device.
        All events that occurred before this call are not recorded.
        Checking if some event occurred can be done with nvmlEventSetWait.
        If function reports NVML_ERROR_UNKNOWN, event set is in undefined state and should be freed.
        If function reports NVML_ERROR_NOT_SUPPORTED, event set can still be used.
        None of the requested eventTypes are registered in that case.
        @param event_types:
        @type event_types:
        @param event_set:
        @type event_set: EventSet
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceRegisterEvents")
        event_set = EventSet()
        ret = fn(self.handle, event_types.as_c_type(), event_set.handle)
        Return.check(ret)
        return event_set

    # Added in 2.285
    def get_supported_event_types(self) -> EventType:
        """Returns information about events supported on device
        FERMI_OR_NEWER
        Events are not supported on Windows. So this function returns an empty mask in eventTypes on Windows."""
        c_eventTypes = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSupportedEventTypes")
        ret = fn(self.handle, byref(c_eventTypes))
        Return.check(ret)
        return EventType(c_eventTypes.value)

    ### TODO:
    # Added in 3.295
    def on_same_board(self, device_2: "Device") -> bool:
        """

        @param device_2:
        @type device_2: Device
        @return:
        @rtype:
        """
        fn = self.lib.get_function_pointer("nvmlDeviceOnSameBoard")
        onSameBoard = c_int()
        ret = fn(self.handle, device_2.handle, byref(onSameBoard))
        Return.check(ret)
        return onSameBoard.value != 0

    # Added in 3.295
    def get_curr_pcie_link_generation(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkGeneration")
        gen = c_uint()
        ret = fn(self.handle, byref(gen))
        Return.check(ret)
        return gen.value

    # Added in 3.295
    def get_max_pcie_link_generation(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkGeneration")
        gen = c_uint()
        ret = fn(self.handle, byref(gen))
        Return.check(ret)
        return gen.value

    # Added in 3.295
    def get_curr_pcie_link_width(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrPcieLinkWidth")
        width = c_uint()
        ret = fn(self.handle, byref(width))
        Return.check(ret)
        return width.value

    # Added in 3.295
    def get_max_pcie_link_width(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetMaxPcieLinkWidth")
        width = c_uint()
        ret = fn(self.handle, byref(width))
        Return.check(ret)
        return width.value

    # Added in 4.304
    def get_supported_clocks_throttle_reasons(self) -> int:
        c_reasons = c_ulonglong()
        fn = self.lib.get_function_pointer(
            "nvmlDeviceGetSupportedClocksThrottleReasons"
        )
        ret = fn(self.handle, byref(c_reasons))
        Return.check(ret)
        return c_reasons.value

    # Added in 4.304
    def get_current_clocks_throttle_reasons(self) -> int:
        c_reasons = c_ulonglong()
        fn = self.lib.get_function_pointer("nvmlDeviceGetCurrentClocksThrottleReasons")
        ret = fn(self.handle, byref(c_reasons))
        Return.check(ret)
        return c_reasons.value

    # Added in 5.319
    def get_index(self) -> int:
        fn = self.lib.get_function_pointer("nvmlDeviceGetIndex")
        c_index = c_uint()
        ret = fn(self.handle, byref(c_index))
        Return.check(ret)
        return c_index.value

    # Added in 5.319
    def get_accounting_mode(self) -> EnableState:
        c_mode = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAccountingMode")
        ret = fn(self.handle, byref(c_mode))
        Return.check(ret)
        return EnableState(c_mode.value)

    def set_accounting_mode(self, mode: EnableState) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceSetAccountingMode")
        ret = fn(self.handle, mode.as_c_type())
        Return.check(ret)

    def clear_accounting_pids(self) -> None:
        fn = self.lib.get_function_pointer("nvmlDeviceClearAccountingPids")
        ret = fn(self.handle)
        Return.check(ret)

    def get_accounting_stats(self, pid: int) -> AccountingStats:
        stats = AccountingStats()
        fn = self.lib.nvmlDeviceGetAccountingStats(self.handle, c_uint(pid), byref(stats))
        if stats.maxMemoryUsage == VALUE_NOT_AVAILABLE_ulonglong:
            # special case for WDDM on Windows, see comment above
            stats.maxMemoryUsage = None
        return stats

    def get_accounting_buffer_size(self) -> int:
        bufferSize = c_uint()
        self.lib.nvmlDeviceGetAccountingBufferSize(self.handle, byref(bufferSize))
        return bufferSize.value

    def get_accounting_pids(self) -> List[int]:
        count = c_uint(self.get_accounting_buffer_size())
        pids = (c_uint * count.value)()
        self.lib.nvmlDeviceGetAccountingPids(self.handle, byref(count), pids)
        return list(pids)

    def get_retired_pages(self, source_filter: PageRetirementCause) -> List[int]:
        c_source = source_filter.as_c_type()
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPages")

        # First call will get the size
        ret = fn(self.handle, c_source, byref(c_count), None)
        result = Return(ret)

        Return.check(ret)

        # # this should only fail with insufficient size
        # if ((result != Return.SUCCESS) and
        #         (result != Return.ERROR_INSUFFICIENT_SIZE)):
        #     raise NVMLError(ret)

        # call again with a buffer
        # oversize the array for the rare cases where additional pages
        # are retired between NVML calls
        c_count.value = c_count.value * 2 + 5
        page_array = c_ulonglong * c_count.value
        c_pages = page_array()
        ret = fn(self.handle, c_source, byref(c_count), c_pages)
        Return.check(ret)
        return list(c_pages)

    def get_retired_pages_pending_status(self) -> EnableState:
        c_pending = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetRetiredPagesPendingStatus")
        ret = fn(self.handle, byref(c_pending))
        Return.check(ret)
        return EnableState(c_pending.value)

    def get_api_restriction(self, api_type: RestrictedAPI) -> EnableState:
        c_permission = EnableState.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetAPIRestriction")
        ret = fn(self.handle, api_type.as_c_type(), byref(c_permission))
        Return.check(ret)
        return EnableState(c_permission.value)

    def get_bridge_chip_info(self) -> BridgeChipHierarchy:
        bridge_hierarchy = BridgeChipHierarchy()
        fn = self.lib.get_function_pointer("nvmlDeviceGetBridgeChipInfo")
        ret = fn(self.handle, byref(bridge_hierarchy))
        Return.check(ret)
        return bridge_hierarchy

    def _get_raw_samples(
        self, sampling_type: SamplingType, time_stamp: int
    ) -> Tuple[ValueType, List[RawSample]]:
        c_sampling_type = sampling_type.as_c_type()
        c_time_stamp = c_ulonglong(time_stamp)
        c_sample_count = c_uint(0)
        c_sample_value_type = ValueType.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetSamples")

        # First Call gets the size
        ret = fn(
            self.handle,
            c_sampling_type,
            c_time_stamp,
            byref(c_sample_value_type),
            byref(c_sample_count),
            None,
        )
        Return.check(ret)

        sampleArray = c_sample_count.value * RawSample
        c_samples = sampleArray()
        ret = fn(
            self.handle,
            c_sampling_type,
            c_time_stamp,
            byref(c_sample_value_type),
            byref(c_sample_count),
            c_samples,
        )
        Return.check(ret, sampling_type)

        # keep only c_sample_count first samples; others are invalid
        valid_samples = list(c_samples)[: c_sample_count.value]
        return ValueType(c_sample_value_type.value), valid_samples

    # column oriented
    # def get_samples(self, sampling_type: SamplingType, time_stamp: int) -> Tuple[List[int], List[Union[int, float]]]:
    #     value_type, raw_samples = self._get_raw_samples(sampling_type, time_stamp)
    #     time_stamps = [x.timeStamp for x in raw_samples]
    #     values = [x.sampleValue.get_value(value_type) for x in raw_samples]
    #     return time_stamps, values

    # row oriented
    def get_samples(self, sampling_type: SamplingType, time_stamp: int) -> List[Sample]:
        value_type, raw_samples = self._get_raw_samples(sampling_type, time_stamp)
        # time_stamps = [x.timeStamp for x in raw_samples]
        # values = [x.sampleValue.get_value(value_type) for x in raw_samples]
        samples = [
            Sample(x.timeStamp, x.sampleValue.get_value(value_type))
            for x in raw_samples
        ]
        return samples

    def try_get_samples(
        self, sampling_type: SamplingType, time_stamp: int
    ) -> List[Sample]:
        try:
            return self.get_samples(sampling_type, time_stamp)
        except NVMLErrorNotFound:
            return []

    def get_violation_status(self, perf_policy_type: PerfPolicyType) -> ViolationTime:
        c_violTime = ViolationTime()
        fn = self.lib.get_function_pointer("nvmlDeviceGetViolationStatus")

        # Invoke the method to get violation time
        ret = fn(self.handle, perf_policy_type.as_c_type(), byref(c_violTime))
        Return.check(ret)
        return c_violTime

    def get_pcie_throughput(self, counter: PcieUtilCounter) -> int:
        c_util = c_uint()
        fn = self.lib.get_function_pointer("nvmlDeviceGetPcieThroughput")
        ret = fn(self.handle, counter.as_c_type(), byref(c_util))
        Return.check(ret)
        return c_util.value

    def get_topology_nearest_gpus(self, level: GpuTopologyLevel):
        """

        @param level:
        @type level:
        @return:
        @rtype: List[Device]
        """
        c_count = c_uint(0)
        fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyNearestGpus")

        # First call will get the size
        ret = fn(self.handle, level.as_c_type(), byref(c_count), None)
        Return.check(ret)

        # call again with a buffer
        device_array = CDevicePointer * c_count.value
        c_devices = device_array()
        ret = fn(self.handle, level.as_c_type(), byref(c_count), c_devices)
        Return.check(ret)
        return [Device(x) for x in c_devices]

    def get_topology_common_ancestor(self, device2: "Device") -> GpuTopologyLevel:
        """

        @param device2:
        @type device2: Device
        @return:
        @rtype: GpuTopologyLevel
        """
        c_level = GpuTopologyLevel.c_type()
        fn = self.lib.get_function_pointer("nvmlDeviceGetTopologyCommonAncestor")
        ret = fn(self.handle, device2.handle, byref(c_level))
        Return.check(ret)
        return GpuTopologyLevel(c_level.value)
