from ctypes import byref, c_uint, pointer

from pynvml3.errors import Return
from pynvml3.structs import CEventSetPointer, EventData


class EventSet:
    """Handle to an event set,
    methods that NVML can perform against each device to register
    and wait for some event to occur."""

    def __init__(self, lib):
        """Create a new EventSet.
        Args:
            lib (NVMLLib): a reference to the NVMLLib object
        """
        self.lib = lib
        self.handle = self._create()

    def __del__(self):
        if self.handle is not None:
            self.free()

    def _create(self) -> pointer:
        """Create an empty set of events.

        Notes:
            - FERMI_OR_NEWER
            - Added in 2.285

        """
        fn = self.lib.get_function_pointer("nvmlEventSetCreate")
        eventSet = CEventSetPointer()
        ret = fn(byref(eventSet))
        Return.check(ret)
        return eventSet

    def free(self) -> None:
        """Releases events in the set.

        Notes:
            - FERMI_OR_NEWER
            - Added in 2.285

        """
        fn = self.lib.get_function_pointer("nvmlEventSetFree")
        ret = fn(self.handle)
        Return.check(ret)
        self.handle = None

    # Added in 2.285
    # raises ERROR_TIMEOUT exception on timeout
    def wait(self, timeout_ms: int) -> EventData:
        """Waits on events and delivers events

        Args:
            timeout_ms: Maximum amount of wait time in
                milliseconds for registered event.

        Note:
            - If some events are ready to be delivered at the time of the call,
              function returns immediately.

            - If there are no events ready to be delivered,
              function sleeps till event arrives but not
              longer than specified timeout.

            - This function in certain conditions can return before specified
              timeout passes (e.g. when interrupt arrives)

            - In case of xid error, the function returns the most recent xid
              error type seen by the system.

            - If there are multiple xid errors generated before ``wait``
              is invoked then the last seen xid error type
              is returned for all xid error events.

        Notes:
            For Fermi or newer fully supported devices.

        Returns: event data

        Raises:
             NVMLErrorTimeout: on timeout

        Important:
            TODO: Implement using ``nvmlEventSetWait_v2``

        """
        fn = self.lib.get_function_pointer("nvmlEventSetWait")
        data = EventData()
        ret = fn(self.handle, byref(data), c_uint(timeout_ms))
        Return.check(ret)
        return data
