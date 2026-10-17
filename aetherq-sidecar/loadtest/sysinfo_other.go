//go:build !windows

package main

import (
	"errors"
	"runtime"
)

var errUnsupported = errors.New("faqat Windows'da")

func procStats(pid int) (ProcStat, error)    { return ProcStat{PID: pid}, errUnsupported }
func timeWaitNow(_, _ int) (int, int, error) { return -1, -1, errUnsupported }
func dynamicPortRange() (int, int, error)    { return 0, 0, errUnsupported }
func cpuName() string                        { return "?" }
func osVersion() string                      { return runtime.GOOS }
