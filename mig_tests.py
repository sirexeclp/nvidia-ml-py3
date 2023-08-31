from pynvml3.enums import GpuInstanceProfile
from pynvml3.errors import NVMLErrorNotSupported
from pynvml3.pynvml import NVMLLib


with NVMLLib() as lib:
    device = lib.device.from_index(1)
    print(device.get_name())
    print(device.get_mig_mode())
    supported_profiles = device.get_supported_gpu_instance_profiles(version=1)
    print(supported_profiles.keys())
    for key, value in supported_profiles.items():
        print(key)
        print(value)
    print(
        device.get_gpu_instance_remaining_capacity(
            GpuInstanceProfile.PROFILE_1_SLICE, version=1
        )
    )
    gpu_instance = device.create_gpu_instance(
        GpuInstanceProfile.PROFILE_1_SLICE, version=1
    )
    print(
        device.get_gpu_instance_remaining_capacity(
            GpuInstanceProfile.PROFILE_1_SLICE, version=1
        )
    )
    info = gpu_instance.get_info()
    print(info.id, info.profileId, info.placement.start, info.placement.size)
    gpu_instance.destroy()
    print(
        device.get_gpu_instance_remaining_capacity(
            GpuInstanceProfile.PROFILE_1_SLICE, version=1
        )
    )
