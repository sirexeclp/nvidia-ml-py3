from ctypes import byref, c_uint, pointer
from pynvml3.enums import ComputeInstanceEngineProfile, ComputeInstanceProfile
from pynvml3.errors import NVMLErrorFunctionNotFound

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
        func = self.lib.get_function_pointer(fn_name, check=True)

        def function_with_handle(*args, **kwargs):
            return func(self.handle, *args, **kwargs)

        return function_with_handle

    def destroy(self):
        self["Destroy"]()

    def get_info_v2(self):
        c_info = ComputeInstanceInfo()
        self["GetInfo_v2"](byref(c_info))
        return c_info

    def get_info(self):
        return self.get_info_v2()


class GpuInstance:
    def __init__(self, lib: "NVMLLib", handle: pointer):
        self.lib = lib
        self.handle = handle

    def __getitem__(self, key):
        fn_name = f"nvmlGpuInstance{key}"
        func = self.lib.get_function_pointer(fn_name, check=True)

        def function_with_handle(*args, **kwargs):
            return func(self.handle, *args, **kwargs)

        return function_with_handle

    def destroy(self):
        self["Destroy"]()

    def get_info(self):
        info = GpuInstanceInfo()
        self["GetInfo"](byref(info))
        return info

    def create_compute_instance(
        self,
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        version: int = 2,
    ):
        compute_instance = CComputeInstancePointer()
        info = self.get_compute_instance_profile_info(
            ci_profile, ci_engine_profile, version=version
        )
        self["CreateComputeInstance"](info.id, byref(compute_instance))
        return ComputeInstance(self.lib, compute_instance)

    def get_compute_instance_remaining_capacity(
        self,
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        version: int = 2,
    ):
        c_count = c_uint()
        info = self.get_compute_instance_profile_info(
            ci_profile, ci_engine_profile, version=version
        )
        self["GetComputeInstanceRemainingCapacity"](info.id, byref(c_count))
        return c_count.value

    def get_compute_instance_profile_info(
        self,
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        version: int = 2,
    ) -> ComputeInstanceProfileInfo | ComputeInstanceProfileInfo_v2:
        if version == 2:
            c_info = ComputeInstanceProfileInfo_v2()
            fn = self["GetComputeInstanceProfileInfoV"]
        elif version == 1:
            c_info = ComputeInstanceProfileInfo()
            fn = self["GetComputeInstanceProfileInfo"]
        else:
            raise NVMLErrorFunctionNotFound
        ret = fn(ci_profile.value, ci_engine_profile.value, byref(c_info))
        return c_info

    # # Define function alias for the API exposed by NVML
    def get_compute_instance_profile_info_v(self, *args, **kwargs):
        return self.get_compute_instance_profile_info(*args, **kwargs)

    def get_compute_instance_possible_placements(
        self,
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        version: int = 2,
    ):
        info = self.get_compute_instance_profile_info(
            ci_profile, ci_engine_profile, version=version
        )

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
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        placement: ComputeInstancePlacement,
        version: int = 2,
    ):
        compute_instance = CComputeInstancePointer()
        info = self.get_compute_instance_profile_info(
            ci_profile, ci_engine_profile, version=version
        )
        self["CreateComputeInstanceWithPlacement"](
            info.id, placement, byref(compute_instance)
        )
        return compute_instance

    def get_compute_instances(
        self,
        ci_profile: ComputeInstanceProfile,
        ci_engine_profile: ComputeInstanceEngineProfile,
        version: int = 2,
    ):
        info = self.get_compute_instance_profile_info(
            ci_profile, ci_engine_profile, version=version
        )
        compute_instance_array = ComputeInstance * info.instanceCount
        c_compute_instances = compute_instance_array()
        count = c_uint()
        self["GetComputeInstances"](info.id, c_compute_instances, byref(count))
        return [
            ComputeInstance(self.lib, handle)
            for handle in c_compute_instances[: count.value]
        ]

    def get_compute_instance_by_id(self, ci_id):
        ci_handle = CComputeInstancePointer()
        self["GetComputeInstanceById"](ci_id, byref(ci_handle))
        return ComputeInstance(self.lib, ci_handle)