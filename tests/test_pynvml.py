from datetime import datetime, timedelta
from unittest import TestCase

from pynvml import NVMLLib
from system import System
from device import Device


class TestDevice(TestCase):
    def test_from_index(self):
        with NVMLLib():
            device = Device.from_index(0)
            # print(device.get_name())
            # print(device.get_board_id())
            # print(device.get_brand())
            # print(device.get_multi_gpu_board())
            # print("affinity", device.get_cpu_affinity(2)[0])
            # print("Minor", device.get_minor_number())
            # uuid = device.get_uuid()
            # print(uuid)
            # print(type(uuid))
            # print(type(uuid.encode("ASCII")))
            # print(uuid.encode("ASCII"))
            # # device = Device.from_uuid(uuid.encode("ASCII"))
            # # print(device.get_brand())
            # print(device.get_cuda_compute_capability())
            # # print(device.get_serial())
            # #print(device.get_inforom_version(InfoRom.ECC))
            # print("total energy", device.get_total_energy_consumption()/1_000_000)
            # print(device.query_drain_state())

            # print(device.modify_drain_state(EnableState.FEATURE_ENABLED))
            # print(device.query_drain_state())
            pci_info = device.get_pci_info()
            print(pci_info.query_drain_state())
            # Device.modify_drain_state(pci_info, EnableState.FEATURE_DISABLED)
            # print(Device.discover_gpus(PciInfo()))

    def test_nvlink(self):
        with NVMLLib():
            device = Device.from_index(0)
            for i in NvLinkCapability:
                print(str(i), device.get_nv_link_capability(0, i))

    def test_nvml_device_get_field_values(self):
        with NVMLLib():
            device = Device.from_index(0)
            values = device.get_field_values(1, FieldId.TOTAL_ENERGY_CONSUMPTION)
            ts = timedelta(microseconds=values.timestamp) + datetime.fromtimestamp(0)
            print("TimeStamp", ts)
            print("Latency-ms", values.latencyUsec / 1_000)
            print("Value", values.value.get_value(ValueType(values.valueType)))
            print("total_energy", device.get_total_energy_consumption())

    def test_system(self):
        with NVMLLib():
            system = System()
            print("driver-version", system.get_driver_version())
            print("cuda-driver-version", system.get_cuda_driver_version())
            # print("proc-name", system.get_process_name())
            print(system.get_topology_gpu_set(0))
            device = Device(system.get_topology_gpu_set(0)[0])
            print(device.get_name())
            print(device.get_supported_event_types())
            # events = device.register_events(EventType.PState)
            # data = events.wait(1_000)
            # print("data", data.eventData)
            # print("fan-speed", device.get_fan_speed())
            # print(device.get_supported_memory_clocks())
            #print("Unitcount", Unit.get_count())
            #print("unitcount", Unit(0).get_psu_info())
            print("aff", [bin(x) for x in device.get_cpu_affinity()])
