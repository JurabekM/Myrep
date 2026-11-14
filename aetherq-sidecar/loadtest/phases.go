package main

import (
	"encoding/json"
	"fmt"
	"math/rand/v2"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"time"
)

// ---------------------------------------------------------------------------------------------
// B. HTTP: N so'rov, har ulanishda K ta (keep-alive), oxirgisida "Connection: close".
// So'rovlar aylanasi: POST (tasodifiy matn) → GET (aynan shu matn qaytishi kerak) → DELETE → /healthz.
// ---------------------------------------------------------------------------------------------

// HTTPResult — bitta zanjir uchun natija.
type HTTPResult struct {
	Path      string             `json:"path"`
	Label     string             `json:"label"`
	Requests  int                `json:"requests"`
	OK        int                `json:"ok"`
	Mismatch  int                `json:"mismatch"`
	Conns     int                `json:"connections"`
	PerConn   int                `json:"requests_per_connection"`
	Conc      int                `json:"concurrency"`
	Errors    map[string]int     `json:"errors"`
	FirstErr  map[string]string  `json:"first_errors,omitempty"`
	Seconds   float64            `json:"seconds"`
	RPS       float64            `json:"req_per_s"`
	First     Summary            `json:"first_request"`     // ulanish + tunel + 1-so'rov
	Rest      Summary            `json:"keepalive_request"` // ochiq ulanishdagi keyingi so'rovlar
	BodyBytes int64              `json:"request_body_bytes"`
	CPU       map[string]float64 `json:"cpu_s,omitempty"`
	TWAfter   int                `json:"time_wait_ephemeral_after"`
}

type recordJSON struct {
	ID    int64  `json:"id"`
	Title string `json:"title"`
	Body  string `json:"body"`
}

// opState — bitta ishchining yozuv aylanasi holati.
type opState struct {
	step        int // 0 POST, 1 GET, 2 DELETE, 3 /healthz
	id          int64
	title, body string
}

type stepOut struct {
	err    error  // transport xatosi — ulanish yaroqsiz
	bad    string // status/mazmun xatosi toifasi ("" — to'g'ri)
	detail string
	sent   int
}

func clip(b []byte) string {
	s := string(b)
	if len(s) > 160 {
		s = s[:160] + "…"
	}
	return s
}

func diffDetail(gotT, gotB, wantT, wantB string) string {
	return fmt.Sprintf("sarlavha %d/%d B (farq %d-baytda), matn %d/%d B (farq %d-baytda)",
		len(gotT), len(wantT), firstDiff([]byte(gotT), []byte(wantT)),
		len(gotB), len(wantB), firstDiff([]byte(gotB), []byte(wantB)))
}

func (s *opState) next(h *hconn, r *rand.Rand, last bool) stepOut {
	switch s.step {
	case 0:
		s.title, s.body = randTitle(r), randBody(r)
		req, _ := json.Marshal(map[string]string{"title": s.title, "body": s.body})
		out := stepOut{sent: len(req)}
		st, data, err := h.do("POST", "/api/v1/records", req, last)
		if out.err = err; err != nil {
			s.step = 0
			return out
		}
		var rec recordJSON
		switch {
		case st != 201:
			out.bad, out.detail = fmt.Sprintf("status:POST:%d", st), clip(data)
		case json.Unmarshal(data, &rec) != nil:
			out.bad, out.detail = "json:POST", clip(data)
		case rec.Title != s.title || rec.Body != s.body:
			out.bad, out.detail = "mismatch:POST", diffDetail(rec.Title, rec.Body, s.title, s.body)
		default:
			s.id, s.step = rec.ID, 1
			return out
		}
		s.step = 0
		return out
	case 1:
		st, data, err := h.do("GET", "/api/v1/records/"+strconv.FormatInt(s.id, 10), nil, last)
		out := stepOut{err: err}
		if err != nil {
			s.step = 0
			return out
		}
		var rec recordJSON
		switch {
		case st != 200:
			out.bad, out.detail = fmt.Sprintf("status:GET:%d", st), clip(data)
		case json.Unmarshal(data, &rec) != nil:
			out.bad, out.detail = "json:GET", clip(data)
		case rec.ID != s.id || rec.Title != s.title || rec.Body != s.body:
			out.bad, out.detail = "mismatch:GET", diffDetail(rec.Title, rec.Body, s.title, s.body)
		default:
			s.step = 2
			return out
		}
		s.step = 0
		return out
	case 2:
		st, data, err := h.do("DELETE", "/api/v1/records/"+strconv.FormatInt(s.id, 10), nil, last)
		out := stepOut{err: err}
		if err != nil {
			s.step = 0
			return out
		}
		if st != 204 || len(data) != 0 {
			out.bad, out.detail = fmt.Sprintf("status:DELETE:%d", st), clip(data)
			s.step = 0
			return out
		}
		s.step = 3
		return out
	default:
		st, data, err := h.do("GET", "/healthz", nil, last)
		out := stepOut{err: err}
		s.step = 0
		if err != nil {
			return out
		}
		if st != 200 || !strings.Contains(string(data), `"status":"ok"`) {
			out.bad, out.detail = fmt.Sprintf("status:healthz:%d", st), clip(data)
		}
		return out
	}
}

// runHTTP — conns ta ulanish × perConn so'rov, conc parallel ishchi.
func runHTTP(p Path, conns, perConn, conc int, seed uint64) HTTPResult {
	first, rest := newRecorder(conns), newRecorder(conns*perConn)
	var next, mismatch, bodyBytes atomic.Int64
	var wg sync.WaitGroup
	t0 := time.Now()
	for w := 0; w < conc; w++ {
		wg.Add(1)
		go func(w int) {
			defer wg.Done()
			r := rand.New(rand.NewPCG(seed, uint64(w)+1))
			var st opState
			for next.Add(1) <= int64(conns) {
				tc := time.Now()
				h, err := dialH(p.Addr)
				if err != nil {
					first.fail(errKind(err), err.Error())
					for i := 1; i < perConn; i++ {
						rest.fail("aborted-conn", "ulanish ochilmadi")
					}
					st.step = 0
					continue
				}
				for i := 0; i < perConn; i++ {
					rec, ts := rest, time.Now()
					if i == 0 {
						rec, ts = first, tc
					}
					out := st.next(h, r, i == perConn-1)
					d := time.Since(ts)
					bodyBytes.Add(int64(out.sent))
					if out.err != nil {
						rec.fail(errKind(out.err), out.err.Error())
						for j := i + 1; j < perConn; j++ {
							rest.fail("aborted-conn", "shu ulanishdagi oldingi so'rovda xato")
						}
						break
					}
					if out.bad != "" {
						if strings.HasPrefix(out.bad, "mismatch") {
							mismatch.Add(1)
						}
						rec.fail(out.bad, out.detail)
						continue
					}
					rec.ok(d)
				}
				h.close()
			}
		}(w)
	}
	wg.Wait()
	secs := time.Since(t0).Seconds()

	fs, fe, ff := first.snapshot()
	rs, re, rf := rest.snapshot()
	res := HTTPResult{Path: p.Key, Label: p.Label, Requests: conns * perConn, Conns: conns, PerConn: perConn,
		Conc: conc, Errors: map[string]int{}, FirstErr: map[string]string{}, Seconds: secs,
		First: summarize(fs), Rest: summarize(rs), BodyBytes: bodyBytes.Load(), Mismatch: int(mismatch.Load())}
	res.OK = len(fs) + len(rs)
	for _, m := range []map[string]int{fe, re} {
		for k, v := range m {
			res.Errors[k] += v
		}
	}
	for _, m := range []map[string]string{ff, rf} {
		for k, v := range m {
			if res.FirstErr[k] == "" {
				res.FirstErr[k] = v
			}
		}
	}
	res.RPS = float64(res.OK) / secs
	return res
}

// ---------------------------------------------------------------------------------------------
// C/D. Yangi ulanishlar: har biri zanjir (handshake) + GET /healthz ("Connection: close", server yopadi).
// ---------------------------------------------------------------------------------------------

// ConnResult — ulanishlar bosqichi natijasi.
type ConnResult struct {
	Path     string             `json:"path"`
	Label    string             `json:"label"`
	Conc     int                `json:"concurrency"`
	Conns    int                `json:"connections"`
	OK       int                `json:"ok"`
	Errors   map[string]int     `json:"errors"`
	FirstErr map[string]string  `json:"first_errors,omitempty"`
	Latency  Summary            `json:"latency"` // ulanishdan javobning oxirgi baytigacha
	Seconds  float64            `json:"seconds"`
	ConnPerS float64            `json:"conn_per_s"`
	CPUms    map[string]float64 `json:"cpu_ms_per_conn,omitempty"`
	TWAfter  int                `json:"time_wait_ephemeral_after"`
}

func runConns(p Path, n, conc int) ConnResult {
	rec := newRecorder(n)
	var next atomic.Int64
	var wg sync.WaitGroup
	t0 := time.Now()
	for w := 0; w < conc; w++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for next.Add(1) <= int64(n) {
				ts := time.Now()
				h, err := dialH(p.Addr)
				if err != nil {
					rec.fail(errKind(err), err.Error())
					continue
				}
				st, body, err := h.do("GET", "/healthz", nil, true)
				h.close()
				d := time.Since(ts)
				switch {
				case err != nil:
					rec.fail(errKind(err), err.Error())
				case st != 200 || !strings.Contains(string(body), `"status":"ok"`):
					rec.fail(fmt.Sprintf("status:%d", st), clip(body))
				default:
					rec.ok(d)
				}
			}
		}()
	}
	wg.Wait()
	secs := time.Since(t0).Seconds()
	s, e, f := rec.snapshot()
	return ConnResult{Path: p.Key, Label: p.Label, Conc: conc, Conns: n, OK: len(s), Errors: e, FirstErr: f,
		Latency: summarize(s), Seconds: secs, ConnPerS: float64(len(s)) / secs}
}
