from unittest import TestCase

from pynvml import Device, NVMLLib, InfoRom, EnableState, PciInfo, NvLinkCapability


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

            #print(device.modify_drain_state(EnableState.FEATURE_ENABLED))
            #print(device.query_drain_state())
            pci_info = device.nvml_device_get_pci_info()
            print(pci_info.query_drain_state())
            #Device.modify_drain_state(pci_info, EnableState.FEATURE_DISABLED)
            #print(Device.discover_gpus(PciInfo()))

    def test_nvlink(self):
        with NVMLLib():
            device = Device.from_index(0)
            for i in NvLinkCapability:
                print(str(i)), device.get_nv_link_capability(0, i))
