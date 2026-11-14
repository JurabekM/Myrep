package main

import (
	"math"
	"sort"
	"sync"
	"time"
)

// Summary — kechikish taqsimoti (millisekundlarda).
type Summary struct {
	N    int     `json:"n"`
	Min  float64 `json:"min_ms"`
	Mean float64 `json:"mean_ms"`
	P50  float64 `json:"p50_ms"`
	P90  float64 `json:"p90_ms"`
	P99  float64 `json:"p99_ms"`
	P999 float64 `json:"p999_ms"`
	Max  float64 `json:"max_ms"`
}

// summarize — namunalar bo'yicha taqsimot. Persentil: nearest-rank (interpolyatsiyasiz).
func summarize(ds []time.Duration) Summary {
	if len(ds) == 0 {
		return Summary{}
	}
	ms := make([]float64, len(ds))
	var sum float64
	for i, d := range ds {
		ms[i] = float64(d) / float64(time.Millisecond)
		sum += ms[i]
	}
	sort.Float64s(ms)
	return Summary{
		N:    len(ms),
		Min:  ms[0],
		Mean: sum / float64(len(ms)),
		P50:  percentile(ms, 50),
		P90:  percentile(ms, 90),
		P99:  percentile(ms, 99),
		P999: percentile(ms, 99.9),
		Max:  ms[len(ms)-1],
	}
}

// percentile — tartiblangan qatorda nearest-rank persentil, p ∈ (0, 100].
func percentile(sorted []float64, p float64) float64 {
	if len(sorted) == 0 {
		return 0
	}
	rank := int(math.Ceil(p / 100 * float64(len(sorted))))
	if rank < 1 {
		rank = 1
	}
	if rank > len(sorted) {
		rank = len(sorted)
	}
	return sorted[rank-1]
}

// Recorder — goroutine'lar uchun xavfsiz namuna va xato yig'uvchi.
type Recorder struct {
	mu      sync.Mutex
	samples []time.Duration
	errors  map[string]int
	first   map[string]string // har toifaning birinchi to'liq xato matni (tashxis uchun)
}

func newRecorder(capHint int) *Recorder {
	return &Recorder{samples: make([]time.Duration, 0, capHint), errors: map[string]int{}, first: map[string]string{}}
}

func (r *Recorder) ok(d time.Duration) {
	r.mu.Lock()
	r.samples = append(r.samples, d)
	r.mu.Unlock()
}

func (r *Recorder) fail(kind, detail string) {
	r.mu.Lock()
	r.errors[kind]++
	if _, seen := r.first[kind]; !seen {
		r.first[kind] = detail
	}
	r.mu.Unlock()
}

func (r *Recorder) errCount() int {
	r.mu.Lock()
	defer r.mu.Unlock()
	n := 0
	for _, v := range r.errors {
		n += v
	}
	return n
}

func (r *Recorder) snapshot() ([]time.Duration, map[string]int, map[string]string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	s := append([]time.Duration(nil), r.samples...)
	e := make(map[string]int, len(r.errors))
	for k, v := range r.errors {
		e[k] = v
	}
	f := make(map[string]string, len(r.first))
	for k, v := range r.first {
		f[k] = v
	}
	return s, e, f
}
