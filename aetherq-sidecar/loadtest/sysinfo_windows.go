//go:build windows

package main

import (
	"errors"
	"os/exec"
	"strings"
	"syscall"
	"unsafe"
)

var (
	kernel32                    = syscall.NewLazyDLL("kernel32.dll")
	procGetProcessHandleCount   = kernel32.NewProc("GetProcessHandleCount")
	procK32GetProcessMemoryInfo = kernel32.NewProc("K32GetProcessMemoryInfo")
)

// processMemoryCounters — PROCESS_MEMORY_COUNTERS (psapi.h).
type processMemoryCounters struct {
	CB                         uint32
	PageFaultCount             uint32
	PeakWorkingSetSize         uintptr
	WorkingSetSize             uintptr
	QuotaPeakPagedPoolUsage    uintptr
	QuotaPagedPoolUsage        uintptr
	QuotaPeakNonPagedPoolUsage uintptr
	QuotaNonPagedPoolUsage     uintptr
	PagefileUsage              uintptr
	PeakPagefileUsage          uintptr
}

// filetimeDuration — FILETIME (100 ns birliklar) davomiylik sifatida, sekundlarda.
func filetimeDuration(ft syscall.Filetime) float64 {
	return float64(int64(ft.HighDateTime)<<32|int64(ft.LowDateTime)) * 100 / 1e9
}

// procStats — thread soni (Toolhelp snapshot), handle soni, xotira va CPU vaqti.
func procStats(pid int) (ProcStat, error) {
	st := ProcStat{PID: pid}
	snap, err := syscall.CreateToolhelp32Snapshot(syscall.TH32CS_SNAPPROCESS, 0)
	if err != nil {
		return st, err
	}
	defer syscall.CloseHandle(snap)
	var pe syscall.ProcessEntry32
	pe.Size = uint32(unsafe.Sizeof(pe))
	found := false
	for err = syscall.Process32First(snap, &pe); err == nil; err = syscall.Process32Next(snap, &pe) {
		if int(pe.ProcessID) == pid {
			st.Threads = int(pe.Threads)
			found = true
			break
		}
	}
	if !found {
		return st, errors.New("jarayon topilmadi")
	}
	const access = 0x1000 | 0x0010 // PROCESS_QUERY_LIMITED_INFORMATION | PROCESS_VM_READ
	h, err := syscall.OpenProcess(access, false, uint32(pid))
	if err != nil {
		return st, err
	}
	defer syscall.CloseHandle(h)
	var hc uint32
	if r, _, _ := procGetProcessHandleCount.Call(uintptr(h), uintptr(unsafe.Pointer(&hc))); r != 0 {
		st.Handles = int(hc)
	}
	var mc processMemoryCounters
	mc.CB = uint32(unsafe.Sizeof(mc))
	if r, _, _ := procK32GetProcessMemoryInfo.Call(uintptr(h), uintptr(unsafe.Pointer(&mc)), uintptr(mc.CB)); r != 0 {
		st.WorkingSetMB = float64(mc.WorkingSetSize) / (1 << 20)
		st.PeakWSMB = float64(mc.PeakWorkingSetSize) / (1 << 20)
		st.PrivateMB = float64(mc.PagefileUsage) / (1 << 20)
	}
	var c, e, k, u syscall.Filetime
	if err := syscall.GetProcessTimes(h, &c, &e, &k, &u); err == nil {
		st.CPUSeconds = filetimeDuration(k) + filetimeDuration(u)
	}
	return st, nil
}

// timeWaitNow — hozirgi TIME_WAIT soketlari (jami, vaqtinchalik portlarda).
func timeWaitNow(dynStart, dynCount int) (int, int, error) {
	out, err := exec.Command("netstat", "-an", "-p", "TCP").Output()
	if err != nil {
		return -1, -1, err
	}
	t, e := countTimeWait(string(out), dynStart, dynCount)
	return t, e, nil
}

// dynamicPortRange — `netsh int ipv4 show dynamicport tcp`: boshlang'ich port va soni.
func dynamicPortRange() (int, int, error) {
	out, err := exec.Command("netsh", "int", "ipv4", "show", "dynamicport", "tcp").Output()
	if err != nil {
		return 0, 0, err
	}
	n := firstInts(string(out), 2)
	if len(n) < 2 {
		return 0, 0, errors.New("netsh chiqishi tushunarsiz")
	}
	return n[0], n[1], nil
}

// cpuName — protsessor nomi (reestrdan).
func cpuName() string {
	out, err := exec.Command("reg", "query", `HKLM\HARDWARE\DESCRIPTION\System\CentralProcessor\0`,
		"/v", "ProcessorNameString").Output()
	if err != nil {
		return "?"
	}
	for _, line := range strings.Split(string(out), "\n") {
		if i := strings.Index(line, "REG_SZ"); i >= 0 {
			return strings.TrimSpace(line[i+len("REG_SZ"):])
		}
	}
	return "?"
}

// osVersion — `ver` chiqishi.
func osVersion() string {
	out, err := exec.Command("cmd", "/c", "ver").Output()
	if err != nil {
		return "windows"
	}
	return strings.TrimSpace(string(out))
}
