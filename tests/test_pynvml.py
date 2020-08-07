from datetime import datetime, timedelta
from unittest import TestCase

from pynvml3 import FieldId, ValueType, InfoRom
from pynvml3.pynvml import NVMLLib
from pynvml3.system import System
from pynvml3.device import Device
from psutil import Process


class TestDevice(TestCase):
    def test_from_index(self):
        with NVMLLib() as lib:
            device = lib.device.from_index(0)
            print(device.get_name())
            print(device.get_board_id())
            print(device.get_brand())
            print(device.get_multi_gpu_board())
            print("affinity", device.get_cpu_affinity()[0])
            print("Minor", device.get_minor_number())
            uuid = device.get_uuid()
            print(uuid)
            device = lib.device.from_uuid(uuid)
            print(device.get_brand())
            print(device.get_cuda_compute_capability())
            # print(device.get_serial())
            # print(device.get_inforom_version(InfoRom.ECC))
            print("total energy", device.get_total_energy_consumption()/1_000_000)

            pci_info = device.get_pci_info()
            print(pci_info.query_drain_state())
            # Device.modify_drain_state(pci_info, EnableState.FEATURE_DISABLED)
            # print(Device.discover_gpus(PciInfo()))

    def test_nvlink(self):
        with NVMLLib() as lib:
            device = lib.device.from_index(0)
            gpu_processes = device.get_graphics_running_processes()
            processes = [Process(x.pid) for x in gpu_processes]
            paths = [p.cmdline()[0] + "/" + p.name() for p in processes]
            print(paths)
            print([p.usedGpuMemory / 2 ** 20 for p in gpu_processes])

            print(device.get_minor_number())

            # for i in NvLinkCapability:
            #     print(str(i), device.get_nv_link_capability(0, i))

    def test_nvml_device_get_field_values(self):
        with NVMLLib() as lib:
            device = lib.device.from_index(0)
            values = device.get_field_values(1, FieldId.TOTAL_ENERGY_CONSUMPTION)
            ts = timedelta(microseconds=values.timestamp) + datetime.fromtimestamp(0)
            print("TimeStamp", ts)
            print("Latency-ms", values.latencyUsec / 1_000)
            print("Value", values.value.get_value(ValueType(values.valueType)))
            print("total_energy", device.get_total_energy_consumption())

    def test_system(self):
        with NVMLLib() as lib:
            system = lib.system
            print("driver-version", system.get_driver_version())
            print("cuda-driver-version", system.get_cuda_driver_version())
            # print("proc-name", system.get_process_name())
            print(system.get_topology_gpu_set(0))
            device = Device(lib, system.get_topology_gpu_set(0)[0])
            print(device.get_name())
            print(device.get_supported_event_types())
            # events = device.register_events(EventType.PState)
            # data = events.wait(1_000)
            # print("data", data.eventData)
            # print("fan-speed", device.get_fan_speed())
            # print(device.get_supported_memory_clocks())
            # print("Unitcount", Unit.get_count())
            # print("unitcount", Unit(0).get_psu_info())
            print("aff", [bin(x) for x in device.get_cpu_affinity()])
