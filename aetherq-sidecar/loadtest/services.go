package main

import (
	"errors"
	"fmt"
	"io"
	"net"
	"os"
	"os/exec"
	"path/filepath"
	"strconv"
	"strings"
	"time"
)

// Bins — sinaladigan ikkilik fayllar.
type Bins struct{ Sidecar, Aqctl, Mono string }

// Port ofsetlari (-base ga qo'shiladi). Hammasi vaqtinchalik (dynamic) diapazondan tashqarida.
const (
	offAqConnFull   = 0
	offGwConnHTTP   = 1
	offAqConnResume = 2
	offAqConnEcho   = 3
	offAqConnPow    = 4
	offGwConnEcho   = 5
	offMono         = 80
	offEcho         = 90
	offMetrics      = 100
	offAqServeHTTP  = 443
	offGwServeHTTP  = 444
	offAqServeEcho  = 445
	offAqServePow   = 446
	offGwServeEcho  = 447
)

type Ports struct{ Base int }

func (p Ports) addr(off int) string { return "127.0.0.1:" + strconv.Itoa(p.Base+off) }

// Path — sinaladigan zanjir. Hops — bitta ulanish band qiladigan vaqtinchalik portlar (eng yomon holat).
type Path struct {
	Key   string
	Label string
	Addr  string
	Hops  int
	Procs []string
}

// Proc — ishga tushirilgan servis jarayoni.
type Proc struct {
	Label   string
	Kind    string // sidecar | gateway | monolith
	cmd     *exec.Cmd
	logFile *os.File
	logPath string
	done    chan struct{}
	baseOff int64 // xato sanash shu nuqtadan (ishga tushish shovqini hisobga olinmaydi)
}

func (p *Proc) pid() int { return p.cmd.Process.Pid }

// Cluster — barcha servislar va jarayon ichidagi echo server.
type Cluster struct {
	work, logs string
	bins       Bins
	ports      Ports
	procs      []*Proc
	echo       net.Listener
}

func (c *Cluster) f(name string) string { return filepath.Join(c.work, name) }

func (c *Cluster) proc(label string) *Proc {
	for _, p := range c.procs {
		if p.Label == label {
			return p
		}
	}
	return nil
}

func (c *Cluster) aqctl(args ...string) error {
	out, err := exec.Command(c.bins.Aqctl, args...).CombinedOutput()
	if err != nil {
		return fmt.Errorf("aqctl %s: %v: %s", strings.Join(args, " "), err, strings.TrimSpace(string(out)))
	}
	return nil
}

// spawn — jarayonni ishga tushiradi va log'da `marker` paydo bo'lishini kutadi (bind'dan keyin yoziladi).
func (c *Cluster) spawn(label, kind, marker, exe string, args ...string) error {
	logPath := filepath.Join(c.logs, label+".log")
	lf, err := os.Create(logPath)
	if err != nil {
		return err
	}
	cmd := exec.Command(exe, args...)
	cmd.Stdout, cmd.Stderr, cmd.Dir = lf, lf, c.work
	if err := cmd.Start(); err != nil {
		lf.Close()
		return fmt.Errorf("%s: %w", label, err)
	}
	p := &Proc{Label: label, Kind: kind, cmd: cmd, logFile: lf, logPath: logPath, done: make(chan struct{})}
	go func() { _ = cmd.Wait(); close(p.done) }()
	c.procs = append(c.procs, p)
	deadline := time.Now().Add(15 * time.Second)
	for time.Now().Before(deadline) {
		b, _ := os.ReadFile(logPath)
		if strings.Contains(string(b), marker) {
			return nil
		}
		select {
		case <-p.done:
			return fmt.Errorf("%s ishga tushmadi: %s", label, strings.TrimSpace(string(b)))
		case <-time.After(25 * time.Millisecond):
		}
	}
	return fmt.Errorf("%s: 15 s ichida tayyor bo'lmadi (%q kutildi)", label, marker)
}

// Start — identity'lar, allowlist'lar, echo server va barcha servislar.
func (c *Cluster) Start(powD int) error {
	for _, n := range []string{"server", "client", "std-server", "std-client"} {
		if err := c.aqctl("identity", "new", "--out", c.f(n)); err != nil {
			return err
		}
	}
	if err := c.aqctl("allowlist", "build", "--out", c.f("allow.txt"), c.f("client.key.pub")); err != nil {
		return err
	}
	if err := c.aqctl("allowlist", "build", "--out", c.f("std-allow.txt"), c.f("std-client.key.pub")); err != nil {
		return err
	}

	ln, err := net.Listen("tcp", c.ports.addr(offEcho))
	if err != nil {
		return fmt.Errorf("echo: %w", err)
	}
	c.echo = ln
	go serveEcho(ln)

	pa := c.ports.addr
	if err := c.spawn("monolit", "monolith", "aether_new ", c.bins.Mono,
		"-listen", pa(offMono), "-data", c.f("data.json")); err != nil {
		return err
	}
	if err := waitHealthz(pa(offMono)); err != nil {
		return fmt.Errorf("monolit: %w", err)
	}

	serve := func(listen, upstream string, extra ...string) []string {
		a := []string{"serve", "--listen", listen, "--upstream", upstream, "--identity", c.f("server.key"),
			"--require-client-auth", "--allow", c.f("allow.txt")}
		return append(a, extra...)
	}
	gwServe := func(listen, upstream string, extra ...string) []string {
		a := []string{"gateway", "serve", "--listen", listen, "--upstream", upstream, "--identity", c.f("std-server.key"),
			"--require-client-auth", "--allow", c.f("std-allow.txt")}
		return append(a, extra...)
	}
	connect := func(listen, peer string, extra ...string) []string {
		a := []string{"connect", "--listen", listen, "--peer", peer, "--server-pub", c.f("server.key.pub"),
			"--identity", c.f("client.key")}
		return append(a, extra...)
	}
	gwConnect := func(listen, peer string) []string {
		return []string{"gateway", "connect", "--listen", listen, "--peer", peer,
			"--server-pub", c.f("std-server.key.pub"), "--identity", c.f("std-client.key")}
	}
	const sm, cm, gsm, gcm = "aq-sidecar: serve ", "aq-sidecar: connect ", "gateway serve ", "gateway connect "
	steps := []struct {
		label, kind, marker, exe string
		args                     []string
	}{
		{"aq_serve_http", "sidecar", sm, c.bins.Sidecar, serve(pa(offAqServeHTTP), pa(offMono))},
		{"aq_serve_echo", "sidecar", sm, c.bins.Sidecar, serve(pa(offAqServeEcho), pa(offEcho))},
		{"aq_serve_pow", "sidecar", sm, c.bins.Sidecar, serve(pa(offAqServePow), pa(offMono), "--pow", strconv.Itoa(powD))},
		{"gw_serve_http", "gateway", gsm, c.bins.Aqctl, gwServe(pa(offGwServeHTTP), pa(offMono), "--metrics", pa(offMetrics))},
		{"gw_serve_echo", "gateway", gsm, c.bins.Aqctl, gwServe(pa(offGwServeEcho), pa(offEcho))},
		{"aq_connect_full", "sidecar", cm, c.bins.Sidecar, connect(pa(offAqConnFull), pa(offAqServeHTTP))},
		{"aq_connect_resume", "sidecar", cm, c.bins.Sidecar, connect(pa(offAqConnResume), pa(offAqServeHTTP), "--resume")},
		{"aq_connect_echo", "sidecar", cm, c.bins.Sidecar, connect(pa(offAqConnEcho), pa(offAqServeEcho))},
		{"aq_connect_pow", "sidecar", cm, c.bins.Sidecar, connect(pa(offAqConnPow), pa(offAqServePow))},
		{"gw_connect_http", "gateway", gcm, c.bins.Aqctl, gwConnect(pa(offGwConnHTTP), pa(offGwServeHTTP))},
		{"gw_connect_echo", "gateway", gcm, c.bins.Aqctl, gwConnect(pa(offGwConnEcho), pa(offGwServeEcho))},
	}
	for _, s := range steps {
		if err := c.spawn(s.label, s.kind, s.marker, s.exe, s.args...); err != nil {
			return err
		}
	}
	return nil
}

// Paths — HTTP zanjirlari va echo zanjirlari.
func (c *Cluster) Paths() (httpPaths, echoPaths []Path) {
	pa := c.ports.addr
	httpPaths = []Path{
		{"direct", "to'g'ridan-to'g'ri (monolit)", pa(offMono), 1, nil},
		{"aq", "AETHER-Q (to'liq handshake)", pa(offAqConnFull), 3, []string{"aq_connect_full", "aq_serve_http"}},
		{"aq_resume", "AETHER-Q (resumption)", pa(offAqConnResume), 3, []string{"aq_connect_resume", "aq_serve_http"}},
		{"aq_pow", "AETHER-Q (PoW yoqilgan)", pa(offAqConnPow), 3, []string{"aq_connect_pow", "aq_serve_pow"}},
		{"gw", "standart PQ-TLS (gateway)", pa(offGwConnHTTP), 3, []string{"gw_connect_http", "gw_serve_http"}},
	}
	echoPaths = []Path{
		{"echo_direct", "to'g'ridan-to'g'ri (echo)", pa(offEcho), 1, nil},
		{"echo_aq", "AETHER-Q (echo)", pa(offAqConnEcho), 3, []string{"aq_connect_echo", "aq_serve_echo"}},
		{"echo_gw", "standart PQ-TLS (echo)", pa(offGwConnEcho), 3, []string{"gw_connect_echo", "gw_serve_echo"}},
	}
	return
}

// markBaseline — xato sanash nuqtasini hozirgi log oxiriga qo'yadi.
func (c *Cluster) markBaseline() {
	for _, p := range c.procs {
		if st, err := os.Stat(p.logPath); err == nil {
			p.baseOff = st.Size()
		}
	}
}

// logSince — baseline'dan keyingi log matni.
func (p *Proc) logSince() string {
	b, err := os.ReadFile(p.logPath)
	if err != nil || int64(len(b)) < p.baseOff {
		return ""
	}
	return string(b[p.baseOff:])
}

// errorPatterns — jarayon turi bo'yicha xato qatorlari.
var errorPatterns = map[string][]string{
	"sidecar":  {"handshake rad etildi", "handshake muvaffaqiyatsiz", "record xatosi", "ulanmadi", "accept:"},
	"gateway":  {"rad etildi", "ulanmadi", "allowlist'da yo'q", "sertifikati yo'q", "ML-DSA emas", "metrics:"},
	"monolith": {"http: ", "panic", "aether_new: "},
}

// countLogErrors — har jarayon uchun baseline'dan keyingi xato qatorlari soni va birinchi namunasi.
func (c *Cluster) countLogErrors() map[string]LogErrors {
	out := map[string]LogErrors{}
	for _, p := range c.procs {
		le := LogErrors{}
		for _, line := range strings.Split(p.logSince(), "\n") {
			for _, pat := range errorPatterns[p.Kind] {
				if strings.Contains(line, pat) {
					le.Count++
					if le.Example == "" {
						le.Example = strings.TrimSpace(line)
					}
					break
				}
			}
		}
		out[p.Label] = le
	}
	return out
}

// Stop — barcha jarayonlarni to'xtatadi.
func (c *Cluster) Stop() {
	for i := len(c.procs) - 1; i >= 0; i-- {
		p := c.procs[i]
		_ = p.cmd.Process.Kill()
		select {
		case <-p.done:
		case <-time.After(5 * time.Second):
		}
		_ = p.logFile.Close()
	}
	if c.echo != nil {
		_ = c.echo.Close()
	}
}

// serveEcho — oddiy TCP echo: o'qiganini qaytaradi, EOF'da yozish tomonini yopadi (half-close).
func serveEcho(ln net.Listener) {
	for {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		go func(conn net.Conn) {
			defer conn.Close()
			_, _ = io.Copy(conn, conn)
			if tc, ok := conn.(*net.TCPConn); ok {
				_ = tc.CloseWrite()
			}
		}(conn)
	}
}

// waitHealthz — zanjir orqali GET /healthz 200 bo'lguncha (≤15 s).
func waitHealthz(addr string) error {
	var last error
	for i := 0; i < 60; i++ {
		h, err := dialH(addr)
		if err == nil {
			st, body, err2 := h.do("GET", "/healthz", nil, true)
			h.close()
			if err2 == nil && st == 200 && strings.Contains(string(body), `"status":"ok"`) {
				return nil
			}
			if err2 != nil {
				err = err2
			} else {
				err = fmt.Errorf("HTTP %d", st)
			}
		}
		last = err
		time.Sleep(250 * time.Millisecond)
	}
	return last
}

// waitEcho — echo zanjiri orqali 32 bayt qaytguncha (≤15 s).
func waitEcho(addr string) error {
	payload := []byte("aqload-echo-tayyorlik-tekshiruvi")
	var last error
	for i := 0; i < 60; i++ {
		_, got, err := echoOnce(addr, payload, []int{len(payload)})
		if err == nil && string(got) == string(payload) {
			return nil
		}
		if err == nil {
			err = errors.New("echo javobi mos emas")
		}
		last = err
		time.Sleep(250 * time.Millisecond)
	}
	return last
}
