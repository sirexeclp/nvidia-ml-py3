from ctypes import byref, c_uint, pointer
from pynvml3.enums import ComputeInstanceEngineProfile, ComputeInstanceProfile
from pynvml3.errors import NVMLErrorFunctionNotFound, NVMLErrorInvalidArgument, NVMLErrorNotSupported, Return

from pynvml3.structs import (
    CComputeInstancePointer,
    CDevicePointer,
    ComputeInstanceInfo,
    ComputeInstancePlacement,
    ComputeInstanceProfileInfo,
    ComputeInstanceProfileInfo_v2,
    GpuInstanceInfo,
)


class ComputeInstance:
    def __init__(self, lib: "NVMLLib", handle: pointer):
        self.lib = lib
        self.handle = handle

    def __getitem__(self, key):
        fn_name = f"nvmlComputeInstance{key}"
        func = self.lib.get_function_pointer(fn_name, check=False)

        def function_with_handle(*args, **kwargs):
            ret = func(self.handle, *args, **kwargs)
            Return.check(ret)
            return

        return function_with_handle

    def destroy(self):
        self["Destroy"]()

    def get_info_v2(self) -> ComputeInstanceInfo:
        c_info = ComputeInstanceInfo()
        self["GetInfo_v2"](byref(c_info))
        return c_info

    def get_info(self):
        return self.get_info_v2()



class GpuInstance:
    def __init__(self, lib: "NVMLLib", handle: pointer, device: "Device", mig_version: int = 2):
        self.lib = lib
        self.handle = handle
        self.device = device
        self.mig_version = mig_version

    def __getitem__(self, key):
        fn_name = f"nvmlGpuInstance{key}"
        func = self.lib.get_function_pointer(fn_name, check=False)

        def function_with_handle(*args, **kwargs):
            ret = func(self.handle, *args, **kwargs)
            Return.check(ret)
            return

        return function_with_handle

    def __str__(self) -> str:
        info = self.get_info()
        return f"GpuInstance(id={info.id}, start={info.placement.start}, size={info.placement.size})"

    def __repr__(self) -> str:
        return str(self)

    def destroy(self):
        self["Destroy"]()

    def get_info(self) -> GpuInstanceInfo:
        info = GpuInstanceInfo()
        self["GetInfo"](byref(info))
        return info

    def get_id(self) -> int:
        return self.get_info().id
    
    def get_mig_device(self) -> "MigDevice":
        devices = self.device.get_mig_devices()
        my_id = self.get_id()
        for device in devices:
            if device.get_gpu_instance_id() == my_id:
                return device

    def create_compute_instance(
        self,
        profile: ComputeInstanceProfile,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ):
        compute_instance = CComputeInstancePointer()
        info = self.get_compute_instance_profile_info(profile, engine_profile)
        self["CreateComputeInstance"](info.id, byref(compute_instance))
        return ComputeInstance(self.lib, compute_instance)

    def get_compute_instance_remaining_capacity(
        self,
        profile: ComputeInstanceProfile,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ):
        c_count = c_uint()
        info = self.get_compute_instance_profile_info(profile, engine_profile)
        self["GetComputeInstanceRemainingCapacity"](info.id, byref(c_count))
        return c_count.value

    def get_compute_instance_profile_info(
        self,
        profile: ComputeInstanceProfile,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ) -> ComputeInstanceProfileInfo | ComputeInstanceProfileInfo_v2:
        if self.mig_version == 2:
            c_info = ComputeInstanceProfileInfo_v2()
            func = self["GetComputeInstanceProfileInfoV"]
        elif self.mig_version == 1:
            c_info = ComputeInstanceProfileInfo()
            func = self["GetComputeInstanceProfileInfo"]
        else:
            raise NVMLErrorFunctionNotFound
        func(profile.value, engine_profile.value, byref(c_info))
        return c_info

    # # Define function alias for the API exposed by NVML
    def get_compute_instance_profile_info_v(self, *args, **kwargs):
        return self.get_compute_instance_profile_info(*args, **kwargs)

    def get_compute_instance_possible_placements(
        self,
        profile: ComputeInstanceProfile,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ):
        info = self.get_compute_instance_profile_info(profile, engine_profile)

        # get # of entries in array
        count = c_uint(0)
        self["GetComputeInstancePossiblePlacements"](info.id, None, byref(count))

        placements_array = ComputeInstancePlacement * count
        c_placements = placements_array()
        self["GetComputeInstancePossiblePlacements"](
            info.id, c_placements, byref(count)
        )
        return list(c_placements)

    def create_compute_instance_with_placement(
        self,
        profile: ComputeInstanceProfile,
        placement: ComputeInstancePlacement,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ):
        compute_instance = CComputeInstancePointer()
        info = self.get_compute_instance_profile_info(profile, engine_profile)
        self["CreateComputeInstanceWithPlacement"](
            info.id, placement, byref(compute_instance)
        )
        return compute_instance

    def get_compute_instances(
        self,
        profile: ComputeInstanceProfile,
        engine_profile: ComputeInstanceEngineProfile = ComputeInstanceEngineProfile.SHARED,
    ):
        info = self.get_compute_instance_profile_info(profile, engine_profile)
        compute_instance_array = CComputeInstancePointer * info.instanceCount
        c_compute_instances = compute_instance_array()
        count = c_uint()
        self["GetComputeInstances"](info.id, c_compute_instances, byref(count))
        return [
            ComputeInstance(self.lib, handle)
            for handle in c_compute_instances[: count.value]
        ]

    def get_compute_instance_supported_profiles(self) -> dict[ComputeInstanceProfile, ComputeInstanceProfileInfo | ComputeInstanceProfileInfo_v2]:
        supported_profiles = {}
        for profile in ComputeInstanceProfile:
            try:
                info = self.get_compute_instance_profile_info(profile)
                supported_profiles[profile] = info
            except NVMLErrorNotSupported:
                pass
            except NVMLErrorInvalidArgument:
                pass
        return supported_profiles

    def get_all_compute_instances(self) -> dict[ComputeInstanceProfile, list[ComputeInstance]] :
        instances = {}
        for profile in self.get_compute_instance_supported_profiles():
            instances[profile] = self.get_compute_instances(profile=profile)
        return instances

    def destroy_all_compute_instances(self, profile: ComputeInstanceProfile  = None):
        if profile is None:
            instances = self.get_all_compute_instances()
        else:
            instances = {profile: self.get_compute_instances(profile=profile)}
        for instance_type in instances.values():
            for instance in instance_type:
                try:
                    instance.destroy()
                except Exception as e:
                    print(e)

    def get_compute_instance_by_id(self, ci_id):
        ci_handle = CComputeInstancePointer()
        self["GetComputeInstanceById"](ci_id, byref(ci_handle))
        return ComputeInstance(self.lib, ci_handle)

    