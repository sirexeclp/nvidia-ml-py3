from unittest import TestCase

from pynvml import Device, NVMLLib, InfoRom


class TestDevice(TestCase):
    def test_from_index(self):
        with NVMLLib():
            device = Device.from_index(0)
            print(device.get_name())
            print(device.get_board_id())
            print(device.get_brand())
            print(device.get_multi_gpu_board())
            print(device.get_cpu_affinity(2)[1])
            print("Minor", device.get_minor_number())
            uuid = device.get_uuid()
            print(uuid)

            device = Device.from_uuid(uuid)
            print(device.get_brand())
            # print(device.get_serial())
            print(device.get_inforom_version(InfoRom.ECC))

