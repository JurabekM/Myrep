// aqload — AETHER-Q sidecar uchun yuk sinovi (faqat Go stdlib).
//
// Zanjirlar (har biri alohida port, hammasi 127.0.0.1):
//
//	to'g'ridan-to'g'ri:     klient → Aether_new
//	AETHER-Q (to'liq):      klient → aq-sidecar connect → aq-sidecar serve → Aether_new
//	AETHER-Q (resumption):  klient → aq-sidecar connect --resume → serve → Aether_new
//	AETHER-Q (PoW):         klient → connect → serve --pow D → Aether_new
//	standart PQ-TLS:        klient → aqctl gateway connect → gateway serve → Aether_new
//	+ echo zanjirlari (bayt yaxlitligi uchun)
//
// Hamma AETHER-Q va gateway zanjirlarida mutual auth + allowlist yoqilgan (ishlab chiqarishga yaqin).
//
// Bosqichlar:
//
//	A integrity — tasodifiy baytlar echo orqali (0 B … 8 MiB), qaytgani aynan solishtiriladi
//	B http      — 10 000 so'rov har zanjirda (1000 ulanish × 10), javob mazmuni tekshiriladi
//	C handshake — 1000 ketma-ket yangi ulanish: ulanishdan javobgacha p50/p99
//	D sweep     — parallellik 1/8/32/128: ulanish/s, kechikish, xatolar
//	E resurslar — sidecar thread/handle soni boshlang'ich holatga qaytadimi (oqish yo'qligi)
//
// Ishga tushirish: python loadtest.py (avval hammasini qayta yig'adi), yoki to'g'ridan-to'g'ri:
//
//	aqload -bin dist -out loadtest-out
//	aqload -quick   (tez tekshiruv, ≈1 daqiqa)
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"io"
	"math/rand/v2"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"runtime"
	"slices"
	"strconv"
	"strings"
	"time"
)

// Config — sinov parametrlari (hisobotga yoziladi).
type Config struct {
	Requests  int      `json:"requests"`
	PerConn   int      `json:"requests_per_connection"`
	Conc      int      `json:"concurrency"`
	HSConns   int      `json:"handshake_connections"`
	PowConns  int      `json:"pow_connections"`
	PowD      int      `json:"pow_difficulty"`
	Sweep     []int    `json:"sweep_levels"`
	SweepN    int      `json:"sweep_connections_min"`
	IntRandom int      `json:"integrity_random_streams"`
	IntConc   int      `json:"integrity_concurrency"`
	Seed      uint64   `json:"seed"`
	Base      int      `json:"port_base"`
	Phases    []string `json:"phases"`
	Quick     bool     `json:"quick"`
}

type BinInfo struct {
	Name     string    `json:"name"`
	Path     string    `json:"path"`
	Size     int64     `json:"size"`
	Modified time.Time `json:"modified"`
	SHA256   string    `json:"sha256"`
}

type EnvInfo struct {
	CPU         string    `json:"cpu"`
	LogicalCPUs int       `json:"logical_cpus"`
	OS          string    `json:"os"`
	GoVersion   string    `json:"go"`
	DynStart    int       `json:"dynamic_port_start"`
	DynCount    int       `json:"dynamic_port_count"`
	TimerStepUS float64   `json:"timer_step_us"`
	Binaries    []BinInfo `json:"binaries"`
}

type LogErrors struct {
	Count   int    `json:"count"`
	Example string `json:"example,omitempty"`
}

type ResourceRow struct {
	Label string   `json:"label"`
	Kind  string   `json:"kind"`
	Base  ProcStat `json:"baseline"`
	End   ProcStat `json:"end"`
	Leak  bool     `json:"thread_leak"`
}

type PortWait struct {
	Before  string  `json:"before"`
	Need    int     `json:"need"`
	TWStart int     `json:"time_wait_ephemeral_start"`
	Seconds float64 `json:"waited_s"`
}

type Criterion struct {
	Name   string `json:"name"`
	Pass   bool   `json:"pass"`
	Detail string `json:"detail"`
}

type Resumption struct {
	Opened      int `json:"tunnels_opened"`
	Resumed     int `json:"resumed"`
	FullOpened  int `json:"full_path_tunnels"`
	FullResumed int `json:"full_path_resumed"`
}

// Report — hisobot (report.json va report.md).
type Report struct {
	Started    time.Time            `json:"started"`
	Finished   time.Time            `json:"finished"`
	Env        EnvInfo              `json:"env"`
	Config     Config               `json:"config"`
	Integrity  []IntegrityResult    `json:"integrity"`
	HTTP       []HTTPResult         `json:"http"`
	Handshake  []ConnResult         `json:"handshake"`
	Sweep      []ConnResult         `json:"sweep"`
	Resources  []ResourceRow        `json:"resources"`
	LogErrors  map[string]LogErrors `json:"log_errors"`
	Resumption Resumption           `json:"resumption"`
	GwDelta    map[string]float64   `json:"gateway_metrics_delta"`
	GwEnd      map[string]float64   `json:"gateway_metrics_end"`
	PortWaits  []PortWait           `json:"port_waits"`
	Criteria   []Criterion          `json:"criteria"`
}

type Runner struct {
	cfg Config
	cl  *Cluster
	rep *Report
}

func main() {
	os.Exit(run())
}

func run() int {
	binDir := flag.String("bin", "dist", "aq-sidecar.exe, aqctl.exe, aether_new.exe papkasi")
	outDir := flag.String("out", "loadtest-out", "natija papkasi (har yugurishda qayta yaratiladi)")
	cfg := Config{}
	flag.IntVar(&cfg.Requests, "requests", 10000, "B: har zanjirda so'rovlar soni")
	flag.IntVar(&cfg.PerConn, "per-conn", 10, "B: bitta ulanishdagi so'rovlar (keep-alive)")
	flag.IntVar(&cfg.Conc, "conc", 16, "B: parallel ishchilar")
	flag.IntVar(&cfg.HSConns, "hs", 1000, "C: ketma-ket ulanishlar soni")
	flag.IntVar(&cfg.PowConns, "pow-hs", 500, "C: PoW zanjiri uchun ulanishlar soni")
	flag.IntVar(&cfg.PowD, "pow", 8, "PoW qiyinligi (serve --pow)")
	sweep := flag.String("sweep", "1,8,32,128", "D: parallellik darajalari")
	flag.IntVar(&cfg.SweepN, "sweep-n", 400, "D: har darajada kamida shuncha ulanish (≥ 4×daraja)")
	flag.IntVar(&cfg.IntRandom, "integrity-random", 35, "A: tasodifiy o'lchamli oqimlar soni (+15 chegaraviy)")
	flag.IntVar(&cfg.IntConc, "integrity-conc", 8, "A: parallel oqimlar")
	flag.Uint64Var(&cfg.Seed, "seed", 1, "tasodifiy ma'lumot urug'i (takrorlanuvchanlik uchun)")
	flag.IntVar(&cfg.Base, "base", 21000, "port bazasi (21000..21447 ishlatiladi)")
	phases := flag.String("phases", "integrity,http,handshake,sweep", "bosqichlar")
	flag.BoolVar(&cfg.Quick, "quick", false, "tez tekshiruv: kichik hajmlar (natija mezonlarga hisoblanmaydi)")
	flag.Parse()

	if cfg.Quick {
		cfg.Requests, cfg.HSConns, cfg.PowConns, cfg.SweepN, cfg.IntRandom = 1000, 100, 50, 40, 5
		*sweep = "1,8,32"
	}
	for _, s := range strings.Split(*sweep, ",") {
		if v, err := strconv.Atoi(strings.TrimSpace(s)); err == nil && v > 0 {
			cfg.Sweep = append(cfg.Sweep, v)
		}
	}
	cfg.Phases = strings.Split(*phases, ",")

	bins := Bins{
		Sidecar: filepath.Join(*binDir, exeName("aq-sidecar")),
		Aqctl:   filepath.Join(*binDir, exeName("aqctl")),
		Mono:    filepath.Join(*binDir, exeName("aether_new")),
	}
	if err := prepareOut(*outDir); err != nil {
		fmt.Fprintln(os.Stderr, "aqload:", err)
		return 2
	}
	rep := &Report{Started: time.Now(), Config: cfg, LogErrors: map[string]LogErrors{}}
	env, err := collectEnv(bins)
	if err != nil {
		fmt.Fprintln(os.Stderr, "aqload:", err)
		return 2
	}
	rep.Env = env
	work, logs := filepath.Join(*outDir, "work"), filepath.Join(*outDir, "logs")
	_ = os.MkdirAll(work, 0o755)
	_ = os.MkdirAll(logs, 0o755)
	abs := func(p string) string { a, _ := filepath.Abs(p); return a }
	cl := &Cluster{work: abs(work), logs: abs(logs), bins: Bins{abs(bins.Sidecar), abs(bins.Aqctl), abs(bins.Mono)},
		ports: Ports{cfg.Base}}

	sig := make(chan os.Signal, 1)
	signal.Notify(sig, os.Interrupt)
	go func() {
		<-sig
		fmt.Fprintln(os.Stderr, "\naqload: to'xtatildi — servislar yopilmoqda")
		cl.Stop()
		os.Exit(130)
	}()
	defer cl.Stop()

	fmt.Printf("AETHER-Q yuk sinovi — %s, %d mantiqiy CPU, %s\n", env.CPU, env.LogicalCPUs, env.OS)
	for _, b := range env.Binaries {
		fmt.Printf("  %-15s %s  sha256 %s…  %s\n", b.Name, b.Modified.Format("2006-01-02 15:04"), b.SHA256[:12], b.Path)
	}
	fmt.Println("\n[0] servislar ishga tushirilmoqda (identity, allowlist, 11 jarayon + echo)")
	if err := cl.Start(cfg.PowD); err != nil {
		fmt.Fprintln(os.Stderr, "aqload: ishga tushirish:", err, "\n  loglar:", cl.logs)
		return 2
	}
	httpPaths, echoPaths := cl.Paths()
	for _, p := range httpPaths {
		if err := waitHealthz(p.Addr); err != nil {
			fmt.Fprintf(os.Stderr, "aqload: %s tayyor emas: %v\n", p.Label, err)
			return 2
		}
	}
	for _, p := range echoPaths {
		if err := waitEcho(p.Addr); err != nil {
			fmt.Fprintf(os.Stderr, "aqload: %s tayyor emas: %v\n", p.Label, err)
			return 2
		}
	}
	time.Sleep(time.Second)
	cl.markBaseline()
	r := &Runner{cfg: cfg, cl: cl, rep: rep}
	base := r.snapshot()
	gw0 := r.gatewayMetrics()
	fmt.Println("    tayyor: hamma zanjir javob beradi")

	has := func(s string) bool { return slices.Contains(cfg.Phases, s) }
	pick := func(keys ...string) []Path {
		var out []Path
		for _, p := range httpPaths {
			if slices.Contains(keys, p.Key) {
				out = append(out, p)
			}
		}
		return out
	}

	if has("integrity") {
		fmt.Println("\n[A] bayt yaxlitligi: echo oqimlari (0 B … 8 MiB), qaytgan baytlar aynan solishtiriladi")
		sizes := integritySizes(rand.New(rand.NewPCG(cfg.Seed, 7)), cfg.IntRandom)
		for _, p := range echoPaths {
			r.ensurePorts("integrity/"+p.Key, len(sizes)*p.Hops)
			res := runIntegrity(p, sizes, cfg.IntConc, cfg.Seed)
			rep.Integrity = append(rep.Integrity, res)
			fmt.Printf("    %-30s %3d/%d oqim to'g'ri, farq %d, xato %d  (%.1f MiB, %.1f s)\n", p.Label, res.OK,
				res.Streams, res.Mismatch, sumErrs(res.Errors), float64(res.Bytes)/(1<<20), res.Seconds)
		}
	}

	if has("http") {
		conns := (cfg.Requests + cfg.PerConn - 1) / cfg.PerConn
		fmt.Printf("\n[B] %d so'rov har zanjirda (%d ulanish × %d, %d parallel): POST → GET → DELETE → /healthz\n",
			conns*cfg.PerConn, conns, cfg.PerConn, cfg.Conc)
		for _, p := range pick("direct", "aq", "aq_resume", "gw") {
			r.ensurePorts("http/"+p.Key, conns*p.Hops)
			c0 := r.cpu(p.Procs)
			res := runHTTP(p, conns, cfg.PerConn, cfg.Conc, cfg.Seed)
			res.CPU = cpuDelta(c0, r.cpu(p.Procs), 1)
			res.TWAfter = r.twEph()
			rep.HTTP = append(rep.HTTP, res)
			fmt.Printf("    %-30s %5d/%d OK, mos emas %d, xato %d, %6.0f so'rov/s, 1-so'rov p50 %.2f ms, keyingi p50 %.2f ms\n",
				p.Label, res.OK, res.Requests, res.Mismatch, sumErrs(res.Errors)-res.Mismatch, res.RPS, res.First.P50, res.Rest.P50)
		}
	}

	if has("handshake") {
		fmt.Printf("\n[C] ketma-ket yangi ulanishlar (har biri: tunel + GET /healthz, server yopadi)\n")
		for _, p := range httpPaths {
			n := cfg.HSConns
			if p.Key == "aq_pow" {
				n = cfg.PowConns
			}
			r.ensurePorts("handshake/"+p.Key, n*p.Hops)
			c0 := r.cpu(p.Procs)
			res := runConns(p, n, 1)
			res.CPUms = cpuDelta(c0, r.cpu(p.Procs), float64(n)/1000)
			res.TWAfter = r.twEph()
			rep.Handshake = append(rep.Handshake, res)
			fmt.Printf("    %-30s %4d/%d OK  p50 %6.2f  p90 %6.2f  p99 %6.2f  max %7.2f ms  (%.0f ulanish/s)\n",
				p.Label, res.OK, res.Conns, res.Latency.P50, res.Latency.P90, res.Latency.P99, res.Latency.Max, res.ConnPerS)
		}
	}

	if has("sweep") {
		fmt.Printf("\n[D] parallellik: har ulanish yangi tunel (eng og'ir holat)\n")
		for _, p := range pick("aq", "aq_resume", "gw") {
			for _, lvl := range cfg.Sweep {
				n := max(cfg.SweepN, lvl*4)
				r.ensurePorts(fmt.Sprintf("sweep/%s/%d", p.Key, lvl), n*p.Hops)
				c0 := r.cpu(p.Procs)
				res := runConns(p, n, lvl)
				res.CPUms = cpuDelta(c0, r.cpu(p.Procs), float64(n)/1000)
				res.TWAfter = r.twEph()
				rep.Sweep = append(rep.Sweep, res)
				fmt.Printf("    %-30s ×%-3d %4d/%d OK  %6.0f ulanish/s  p50 %7.2f  p99 %7.2f ms\n",
					p.Label, lvl, res.OK, res.Conns, res.ConnPerS, res.Latency.P50, res.Latency.P99)
			}
		}
	}

	fmt.Println("\n[E] resurslar: jarayonlar tinchlanishini kutish va oqishni tekshirish")
	r.settle(base)
	end := r.snapshot()
	for _, p := range cl.procs {
		row := ResourceRow{Label: p.Label, Kind: p.Kind, Base: base[p.Label], End: end[p.Label]}
		row.Leak = p.Kind == "sidecar" && row.End.Threads > row.Base.Threads+2
		rep.Resources = append(rep.Resources, row)
	}
	rep.LogErrors = cl.countLogErrors()
	rep.Resumption = r.resumption()
	gw1 := r.gatewayMetrics()
	rep.GwEnd = gw1
	rep.GwDelta = map[string]float64{}
	for k, v := range gw1 {
		rep.GwDelta[k] = v - gw0[k]
	}
	rep.Finished = time.Now()
	rep.Criteria = buildCriteria(rep)

	if err := writeReports(*outDir, rep); err != nil {
		fmt.Fprintln(os.Stderr, "aqload: hisobot:", err)
		return 2
	}
	fmt.Println("\nMEZONLAR")
	failed := 0
	for _, c := range rep.Criteria {
		mark := "PASS"
		if !c.Pass {
			mark = "FAIL"
			failed++
		}
		fmt.Printf("  %s  %s — %s\n", mark, c.Name, c.Detail)
	}
	fmt.Printf("\nNATIJA: %d/%d mezon o'tdi · %s davom etdi\n", len(rep.Criteria)-failed, len(rep.Criteria),
		rep.Finished.Sub(rep.Started).Round(time.Second))
	fmt.Println("hisobot:", filepath.Join(*outDir, "report.md"), "|", filepath.Join(*outDir, "report.json"))
	if cfg.Quick {
		fmt.Println("eslatma: -quick rejimi — hajmlar kichik, natija qabul mezoni sifatida hisoblanmaydi")
	}
	if failed > 0 {
		return 1
	}
	return 0
}

func exeName(n string) string {
	if runtime.GOOS == "windows" {
		return n + ".exe"
	}
	return n
}

// prepareOut — natija papkasini tozalaydi. Begona papkani o'chirmaslik uchun faqat aqload belgisi (.aqload)
// bor papka tozalanadi. Papkaning o'zi emas, ichidagilar o'chiriladi: Windows'da papka biror terminal yoki
// Explorer'ning joriy papkasi bo'lsa, uni o'chirib bo'lmaydi.
func prepareOut(dir string) error {
	if entries, err := os.ReadDir(dir); err == nil && len(entries) > 0 {
		if _, err := os.Stat(filepath.Join(dir, ".aqload")); err != nil {
			return fmt.Errorf("%s bo'sh emas va aqload papkasi emas — o'chirilmadi; boshqa -out bering", dir)
		}
		for _, e := range entries {
			if err := os.RemoveAll(filepath.Join(dir, e.Name())); err != nil {
				return err
			}
		}
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}
	return os.WriteFile(filepath.Join(dir, ".aqload"), []byte("aqload natija papkasi\n"), 0o644)
}

func collectEnv(b Bins) (EnvInfo, error) {
	env := EnvInfo{CPU: cpuName(), LogicalCPUs: runtime.NumCPU(), OS: osVersion(), GoVersion: runtime.Version()}
	env.DynStart, env.DynCount, _ = dynamicPortRange()
	// Taymer qadami: ketma-ket time.Now() orasidagi eng kichik musbat farq.
	step := time.Hour
	for i := 0; i < 20000; i++ {
		a := time.Now()
		for {
			if d := time.Since(a); d > 0 {
				step = min(step, d)
				break
			}
		}
	}
	env.TimerStepUS = float64(step) / float64(time.Microsecond)
	for _, p := range []struct{ name, path string }{{"aq-sidecar", b.Sidecar}, {"aqctl", b.Aqctl}, {"aether_new", b.Mono}} {
		st, err := os.Stat(p.path)
		if err != nil {
			return env, fmt.Errorf("%s topilmadi: %s (avval: python loadtest.py — u hammasini yig'adi)", p.name, p.path)
		}
		f, err := os.Open(p.path)
		if err != nil {
			return env, err
		}
		h := sha256.New()
		_, _ = io.Copy(h, f)
		f.Close()
		env.Binaries = append(env.Binaries, BinInfo{Name: p.name, Path: p.path, Size: st.Size(),
			Modified: st.ModTime(), SHA256: hex.EncodeToString(h.Sum(nil))})
	}
	return env, nil
}

// ensurePorts — vaqtinchalik portlar zaxirasi: TIME_WAIT + kerakli portlar diapazonning 75% idan oshsa, kutadi.
// Windows'da TIME_WAIT ~2 daqiqa saqlanadi; aks holda yangi ulanishlar "port tugadi" xatosi bilan yiqiladi.
func (r *Runner) ensurePorts(label string, need int) {
	env := r.rep.Env
	if env.DynCount == 0 {
		return
	}
	limit := env.DynCount * 75 / 100
	_, eph, err := timeWaitNow(env.DynStart, env.DynCount)
	if err != nil || eph+need <= limit {
		return
	}
	start, tw0 := time.Now(), eph
	fmt.Printf("    … %s: TIME_WAIT %d + kerak %d > %d — portlar bo'shashini kutyapman\n", label, eph, need, limit)
	for eph+need > limit && time.Since(start) < 5*time.Minute {
		time.Sleep(5 * time.Second)
		if _, e, err := timeWaitNow(env.DynStart, env.DynCount); err == nil {
			eph = e
		}
	}
	r.rep.PortWaits = append(r.rep.PortWaits, PortWait{Before: label, Need: need, TWStart: tw0,
		Seconds: time.Since(start).Seconds()})
}

func (r *Runner) twEph() int {
	_, eph, err := timeWaitNow(r.rep.Env.DynStart, r.rep.Env.DynCount)
	if err != nil {
		return -1
	}
	return eph
}

func (r *Runner) cpu(labels []string) map[string]float64 {
	m := map[string]float64{}
	for _, l := range labels {
		if p := r.cl.proc(l); p != nil {
			if st, err := procStats(p.pid()); err == nil {
				m[l] = st.CPUSeconds
			}
		}
	}
	return m
}

// cpuDelta — CPU vaqti farqi (sekund) / per. per = 1 → sekund; per = n/1000 → ms/ulanish.
func cpuDelta(a, b map[string]float64, per float64) map[string]float64 {
	out := map[string]float64{}
	for k, v := range b {
		out[k] = (v - a[k]) / per
	}
	return out
}

func (r *Runner) snapshot() map[string]ProcStat {
	m := map[string]ProcStat{}
	for _, p := range r.cl.procs {
		if st, err := procStats(p.pid()); err == nil {
			m[p.Label] = st
		}
	}
	return m
}

// settle — sidecar thread'lari boshlang'ich holatga qaytguncha kutadi (≤ 20 s).
func (r *Runner) settle(base map[string]ProcStat) {
	deadline := time.Now().Add(20 * time.Second)
	for time.Now().Before(deadline) {
		cur := r.snapshot()
		ok := true
		for _, p := range r.cl.procs {
			if p.Kind == "sidecar" && cur[p.Label].Threads > base[p.Label].Threads+2 {
				ok = false
			}
		}
		if ok {
			return
		}
		time.Sleep(500 * time.Millisecond)
	}
}

func (r *Runner) resumption() Resumption {
	var out Resumption
	if p := r.cl.proc("aq_connect_resume"); p != nil {
		l := p.logSince()
		out.Opened, out.Resumed = strings.Count(l, "tunel ochildi"), strings.Count(l, "(resumption)")
	}
	if p := r.cl.proc("aq_connect_full"); p != nil {
		l := p.logSince()
		out.FullOpened, out.FullResumed = strings.Count(l, "tunel ochildi"), strings.Count(l, "(resumption)")
	}
	return out
}

// gatewayMetrics — gateway /metrics (Prometheus matni) → nom → qiymat.
func (r *Runner) gatewayMetrics() map[string]float64 {
	out := map[string]float64{}
	client := http.Client{Timeout: 5 * time.Second}
	resp, err := client.Get("http://" + r.cl.ports.addr(offMetrics) + "/metrics")
	if err != nil {
		return out
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(resp.Body)
	for _, line := range strings.Split(string(body), "\n") {
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		i := strings.LastIndexByte(line, ' ')
		if i < 0 {
			continue
		}
		if v, err := strconv.ParseFloat(line[i+1:], 64); err == nil {
			out[line[:i]] = v
		}
	}
	return out
}

func sumErrs(m map[string]int) int {
	n := 0
	for _, v := range m {
		n += v
	}
	return n
}

// buildCriteria — faqat bajarilgan bosqichlar bo'yicha mezonlar.
func buildCriteria(rep *Report) []Criterion {
	var out []Criterion
	add := func(name string, pass bool, detail string) { out = append(out, Criterion{name, pass, detail}) }

	if len(rep.Integrity) > 0 {
		pass, streams, biggest := true, 0, 0
		for _, r := range rep.Integrity {
			streams += r.Streams
			biggest = max(biggest, r.MaxSize)
			if r.OK != r.Streams || r.Mismatch != 0 {
				pass = false
			}
		}
		add("A. Bayt yaxlitligi (echo)", pass, fmt.Sprintf("%d zanjir, jami %d oqim, eng kattasi %.0f MiB; har biri aynan solishtirildi",
			len(rep.Integrity), streams, float64(biggest)/(1<<20)))
	}
	if len(rep.HTTP) > 0 {
		pass, parts := true, []string{}
		for _, r := range rep.HTTP {
			if r.OK != r.Requests || r.Mismatch != 0 {
				pass = false
			}
			parts = append(parts, fmt.Sprintf("%s %d/%d", r.Path, r.OK, r.Requests))
		}
		add(fmt.Sprintf("B. %d so'rov har zanjirda, javob mazmuni bir xil", rep.HTTP[0].Requests), pass, strings.Join(parts, ", "))
	}
	if len(rep.Handshake) > 0 {
		pass, parts := true, []string{}
		for _, r := range rep.Handshake {
			if r.OK != r.Conns {
				pass = false
			}
			parts = append(parts, fmt.Sprintf("%s %d/%d", r.Path, r.OK, r.Conns))
		}
		add("C. Ketma-ket yangi ulanishlar xatosiz", pass, strings.Join(parts, ", "))
	}
	if len(rep.Sweep) > 0 {
		pass, errs, total := true, 0, 0
		for _, r := range rep.Sweep {
			total += r.Conns
			if r.OK != r.Conns {
				pass = false
				errs += r.Conns - r.OK
			}
		}
		add("D. Parallel ulanishlar xatosiz", pass, fmt.Sprintf("%d ulanish, %d xato", total, errs))
	}
	if len(rep.Resources) > 0 {
		pass, parts := true, []string{}
		for _, r := range rep.Resources {
			if r.Kind != "sidecar" {
				continue
			}
			if r.Leak {
				pass = false
			}
			parts = append(parts, fmt.Sprintf("%s %d→%d", r.Label, r.Base.Threads, r.End.Threads))
		}
		add("E. Sidecar thread'lari boshlang'ich holatga qaytdi (oqish yo'q)", pass, "thread: "+strings.Join(parts, ", "))
	}
	{
		n, parts := 0, []string{}
		for label, le := range rep.LogErrors {
			if le.Count > 0 {
				n += le.Count
				parts = append(parts, fmt.Sprintf("%s: %d", label, le.Count))
			}
		}
		slices.Sort(parts)
		detail := "xato qatori yo'q"
		if n > 0 {
			detail = strings.Join(parts, ", ")
		}
		add("F. Servis log'larida xato yo'q", n == 0, detail)
	}
	if rep.Resumption.Opened > 0 {
		rs := rep.Resumption
		ratio := float64(rs.Resumed) / float64(rs.Opened)
		add("G. Resumption zanjirida ≥95% tunel resumption bilan", ratio >= 0.95 && rs.FullResumed == 0,
			fmt.Sprintf("%d/%d (%.1f%%); to'liq zanjirda resumption %d (0 bo'lishi kerak)", rs.Resumed, rs.Opened, ratio*100, rs.FullResumed))
	}
	if len(rep.GwEnd) > 0 {
		active, fails := rep.GwEnd["aqgw_active_connections"], rep.GwDelta["aqgw_handshake_failures_total"]
		add("H. Gateway: oxirida faol tunel 0, handshake xatosi 0", active == 0 && fails == 0,
			fmt.Sprintf("faol %.0f, xato %.0f, yangi ulanish %.0f", active, fails, rep.GwDelta["aqgw_connections_total"]))
	}
	return out
}

func writeReports(dir string, rep *Report) error {
	js, err := json.MarshalIndent(rep, "", "  ")
	if err != nil {
		return err
	}
	if err := os.WriteFile(filepath.Join(dir, "report.json"), js, 0o644); err != nil {
		return err
	}
	md := renderMarkdown(rep)
	if md == "" {
		return errors.New("bo'sh hisobot")
	}
	return os.WriteFile(filepath.Join(dir, "report.md"), []byte(md), 0o644)
}
