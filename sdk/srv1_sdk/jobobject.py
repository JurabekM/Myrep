"""Windows Job Object: bola jarayonga xotira limiti va yadro bilan birga o'lish kafolati."""
# pywin32 tip ma'lumotisiz keladi; shu fayl uning yagona iste'molchisi.
# pyright: reportMissingModuleSource=false, reportUnknownMemberType=false
# pyright: reportUnknownVariableType=false, reportUnknownArgumentType=false

from typing import Any

import psutil
import win32api
import win32con
import win32job
import win32process

_ACCESS = win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE
_THREAD_SUSPEND_RESUME = 0x0002


def resume_process(pid: int) -> None:
    """`CREATE_SUSPENDED` bilan yaratilgan jarayonni davom ettiradi (hamma oqimlarini)."""
    for thread in psutil.Process(pid).threads():
        handle = win32api.OpenThread(_THREAD_SUSPEND_RESUME, False, thread.id)
        try:
            win32process.ResumeThread(handle)
        finally:
            win32api.CloseHandle(handle)


class MemoryJob:
    """Jobga biriktirilgan jarayonlar jami `limit_bytes` dan ortiq xotira band qila olmaydi.

    Limitdan oshgan ajratish muvaffaqiyatsiz bo'ladi (Python'da `MemoryError`).
    Job dastasi yopilganda (yadro o'lsa ham) undagi barcha jarayonlar o'ldiriladi.
    """

    def __init__(self, limit_bytes: int) -> None:
        self.limit_bytes = limit_bytes
        self._handle: Any = win32job.CreateJobObject(None, "")
        info = win32job.QueryInformationJobObject(
            self._handle, win32job.JobObjectExtendedLimitInformation
        )
        info["JobMemoryLimit"] = limit_bytes
        info["BasicLimitInformation"]["LimitFlags"] = (
            win32job.JOB_OBJECT_LIMIT_JOB_MEMORY | win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        )
        win32job.SetInformationJobObject(
            self._handle, win32job.JobObjectExtendedLimitInformation, info
        )

    def assign(self, pid: int) -> None:
        process = win32api.OpenProcess(_ACCESS, False, pid)
        try:
            win32job.AssignProcessToJobObject(self._handle, process)
        finally:
            win32api.CloseHandle(process)

    def peak_bytes(self) -> int:
        """Job mavjud bo'lgan davrdagi eng yuqori band qilingan xotira."""
        info = win32job.QueryInformationJobObject(
            self._handle, win32job.JobObjectExtendedLimitInformation
        )
        return int(info["PeakJobMemoryUsed"])

    def close(self) -> None:
        """Dastani yopadi; jobdagi tirik jarayonlar o'ldiriladi."""
        if self._handle is not None:
            win32api.CloseHandle(self._handle)
            self._handle = None
