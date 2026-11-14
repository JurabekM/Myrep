package main

import (
	"bytes"
	"encoding/binary"
	"fmt"
	"io"
	"math/rand/v2"
	"net"
	"sync"
	"sync/atomic"
	"time"
)

// IntegrityResult — bayt yaxlitligi bosqichi (bitta echo zanjiri).
type IntegrityResult struct {
	Path     string            `json:"path"`
	Label    string            `json:"label"`
	Streams  int               `json:"streams"`
	OK       int               `json:"ok"`
	Mismatch int               `json:"mismatch"`
	Errors   map[string]int    `json:"errors"`
	FirstErr map[string]string `json:"first_errors,omitempty"`
	Bytes    int64             `json:"bytes_each_way"`
	MaxSize  int               `json:"max_stream_bytes"`
	Seconds  float64           `json:"seconds"`
	Big      Summary           `json:"big_stream_ms"` // ≥ 1 MiB oqimlar (yozish + to'liq qaytish)
}

// integritySizes — chegaraviy o'lchamlar (bo'sh, record chegarasi 16 KiB atrofi, 64 KiB, 1 MiB, 8 MiB)
// va tasodifiy o'lchamlar.
func integritySizes(r *rand.Rand, nRandom int) []int {
	sizes := []int{0, 1, 2, 100, 1000, 16383, 16384, 16385, 32768, 65535, 65536, 65537, 1 << 20, 1<<20 + 1, 8 << 20}
	for i := 0; i < nRandom; i++ {
		sizes = append(sizes, 1+r.IntN(512<<10))
	}
	return sizes
}

func fillRandom(r *rand.Rand, b []byte) {
	var w [8]byte
	for i := 0; i < len(b); i += 8 {
		binary.LittleEndian.PutUint64(w[:], r.Uint64())
		copy(b[i:], w[:])
	}
}

// chunkPlan — yozish bo'laklari: 1 bayt .. 64 KiB tasodifiy (record chegaralari turli joyga tushsin).
func chunkPlan(r *rand.Rand, total int) []int {
	var out []int
	for sum := 0; sum < total; {
		n := 1 + r.IntN(64<<10)
		if r.IntN(10) == 0 {
			n = 1 + r.IntN(16)
		}
		out = append(out, n)
		sum += n
	}
	return out
}

func firstDiff(a, b []byte) int {
	n := min(len(a), len(b))
	for i := 0; i < n; i++ {
		if a[i] != b[i] {
			return i
		}
	}
	return n
}

// echoOnce — payload'ni `chunks` bo'laklarida yozadi, so'ng yozish tomonini yopadi (half-close) va
// javobni EOF'gacha o'qiydi. Davomiylik: ulanishdan oxirgi baytgacha.
func echoOnce(addr string, payload []byte, chunks []int) (time.Duration, []byte, error) {
	t0 := time.Now()
	c, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return 0, nil, &opError{"dial", err}
	}
	defer c.Close()
	_ = c.SetDeadline(time.Now().Add(120 * time.Second))
	werr := make(chan error, 1)
	go func() {
		off := 0
		for _, n := range chunks {
			if off >= len(payload) {
				break
			}
			end := min(off+n, len(payload))
			if _, err := c.Write(payload[off:end]); err != nil {
				werr <- &opError{"write", err}
				return
			}
			off = end
		}
		if off < len(payload) {
			if _, err := c.Write(payload[off:]); err != nil {
				werr <- &opError{"write", err}
				return
			}
		}
		if tc, ok := c.(*net.TCPConn); ok {
			if err := tc.CloseWrite(); err != nil {
				werr <- &opError{"close-write", err}
				return
			}
		}
		werr <- nil
	}()
	got, rerr := io.ReadAll(c)
	if rerr != nil {
		_ = c.Close() // yozuvchi bloklanib qolmasin
	}
	if err := <-werr; err != nil {
		return 0, got, err
	}
	if rerr != nil {
		return 0, got, &opError{"read", rerr}
	}
	return time.Since(t0), got, nil
}

// runIntegrity — har oqim: tasodifiy baytlar → zanjir → echo → qaytgan baytlar aynan solishtiriladi.
func runIntegrity(p Path, sizes []int, conc int, seed uint64) IntegrityResult {
	res := IntegrityResult{Path: p.Key, Label: p.Label, Streams: len(sizes),
		Errors: map[string]int{}, FirstErr: map[string]string{}}
	for _, s := range sizes {
		res.MaxSize = max(res.MaxSize, s)
	}
	var mu sync.Mutex
	var big []time.Duration
	var next atomic.Int64
	var wg sync.WaitGroup
	t0 := time.Now()
	for w := 0; w < conc; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for {
				i := int(next.Add(1)) - 1
				if i >= len(sizes) {
					return
				}
				r := rand.New(rand.NewPCG(seed, uint64(i)+1000))
				payload := make([]byte, sizes[i])
				fillRandom(r, payload)
				d, got, err := echoOnce(p.Addr, payload, chunkPlan(r, len(payload)))
				mu.Lock()
				switch {
				case err != nil:
					k := errKind(err)
					res.Errors[k]++
					if res.FirstErr[k] == "" {
						res.FirstErr[k] = fmt.Sprintf("%d B oqim: %v", len(payload), err)
					}
				case !bytes.Equal(got, payload):
					res.Mismatch++
					if res.FirstErr["mismatch"] == "" {
						res.FirstErr["mismatch"] = fmt.Sprintf("%d B yuborildi, %d B qaytdi, birinchi farq %d-baytda",
							len(payload), len(got), firstDiff(got, payload))
					}
				default:
					res.OK++
					res.Bytes += int64(len(payload))
					if len(payload) >= 1<<20 {
						big = append(big, d)
					}
				}
				mu.Unlock()
			}
		}()
	}
	wg.Wait()
	res.Seconds = time.Since(t0).Seconds()
	res.Big = summarize(big)
	return res
}
