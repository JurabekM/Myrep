package main

import (
	"strconv"
	"strings"
)

// ProcStat — jarayon resurslari (Windows'da OS'dan o'qiladi; boshqa OS'da mavjud emas).
type ProcStat struct {
	PID          int     `json:"pid"`
	Threads      int     `json:"threads"`
	Handles      int     `json:"handles"`
	WorkingSetMB float64 `json:"working_set_mb"`
	PeakWSMB     float64 `json:"peak_working_set_mb"`
	PrivateMB    float64 `json:"private_mb"`
	CPUSeconds   float64 `json:"cpu_s"`
}

// countTimeWait — `netstat -an` chiqishidan TIME_WAIT soketlarini sanaydi: jami va mahalliy porti
// vaqtinchalik (dynamic) diapazonda bo'lganlar (aynan shular yangi ulanishlar uchun port tugashiga olib keladi).
func countTimeWait(netstatOut string, dynStart, dynCount int) (total, ephemeral int) {
	for _, line := range strings.Split(netstatOut, "\n") {
		f := strings.Fields(line)
		if len(f) < 4 || !strings.EqualFold(f[0], "TCP") || f[3] != "TIME_WAIT" {
			continue
		}
		total++
		local := f[1]
		i := strings.LastIndexByte(local, ':')
		if i < 0 {
			continue
		}
		port, err := strconv.Atoi(local[i+1:])
		if err == nil && port >= dynStart && port < dynStart+dynCount {
			ephemeral++
		}
	}
	return total, ephemeral
}

// firstInts — matndagi birinchi n ta butun son (lokalizatsiyalangan chiqishdan raqamlarni olish uchun).
func firstInts(s string, n int) []int {
	var out []int
	cur := -1
	flush := func() {
		if cur >= 0 {
			out = append(out, cur)
			cur = -1
		}
	}
	for _, r := range s {
		if r >= '0' && r <= '9' {
			if cur < 0 {
				cur = 0
			}
			cur = cur*10 + int(r-'0')
			continue
		}
		flush()
		if len(out) >= n {
			return out[:n]
		}
	}
	flush()
	if len(out) > n {
		out = out[:n]
	}
	return out
}
