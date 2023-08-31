from ctypes import byref, pointer

from pynvml3.structs import CComputeInstancePointer, ComputeInstanceInfo, GpuInstanceInfo


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

    def create_compute_instance(self, profileId):
        compute_instance = CComputeInstancePointer()
        self["CreateComputeInstance"](profileId, byref(compute_instance))
        return ComputeInstance(self.lib, compute_instance)


    # def nvmlGpuInstanceGetComputeInstanceProfileInfo(device, profile, engProfile, version=2):
    #     if version == 2:
    #         c_info = c_nvmlComputeInstanceProfileInfo_v2_t()
    #         fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstanceProfileInfoV")
    #     elif version == 1:
    #         c_info = c_nvmlComputeInstanceProfileInfo_t()
    #         fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstanceProfileInfo")
    #     else:
    #         raise NVMLError(NVML_ERROR_FUNCTION_NOT_FOUND)
    #     ret = fn(device, profile, engProfile, byref(c_info))
    #     _nvmlCheckReturn(ret)
    #     return c_info

# # Define function alias for the API exposed by NVML
# nvmlGpuInstanceGetComputeInstanceProfileInfoV = nvmlGpuInstanceGetComputeInstanceProfileInfo

# def nvmlGpuInstanceGetComputeInstanceRemainingCapacity(gpuInstance, profileId):
#     c_count = c_uint()
#     fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstanceRemainingCapacity")
#     ret = fn(gpuInstance, profileId, byref(c_count))
#     _nvmlCheckReturn(ret)
#     return c_count.value

# def nvmlGpuInstanceGetComputeInstancePossiblePlacements(gpuInstance, profileId, placementsRef, countRef):
#     fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstancePossiblePlacements")
#     ret = fn(gpuInstance, profileId, placementsRef, countRef)
#     _nvmlCheckReturn(ret)
#     return ret

# def nvmlGpuInstanceCreateComputeInstanceWithPlacement(gpuInstance, profileId, placement):
#     c_instance = c_nvmlComputeInstance_t()
#     fn = _nvmlGetFunctionPointer("nvmlGpuInstanceCreateComputeInstanceWithPlacement")
#     ret = fn(gpuInstance, profileId, placement, byref(c_instance))
#     _nvmlCheckReturn(ret)
#     return c_instance

# def nvmlGpuInstanceGetComputeInstances(gpuInstance, profileId, computeInstancesRef, countRef):
#     fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstances")
#     ret = fn(gpuInstance, profileId, computeInstancesRef, countRef)
#     _nvmlCheckReturn(ret)
#     return ret

# def nvmlGpuInstanceGetComputeInstanceById(gpuInstance, computeInstanceId):
#     c_instance = c_nvmlComputeInstance_t()
#     fn = _nvmlGetFunctionPointer("nvmlGpuInstanceGetComputeInstanceById")
#     ret = fn(gpuInstance, computeInstanceId, byref(c_instance))
#     _nvmlCheckReturn(ret)
#     return c_instance
