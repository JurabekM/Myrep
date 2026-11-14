package gateway

import (
	"bytes"
	"crypto/tls"
	"io"
	"net"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"aqctl/internal/identity"
)

// Oddiy echo upstream (monolit o'rnida).
func startEcho(t *testing.T) string {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	go func() {
		for {
			c, err := ln.Accept()
			if err != nil {
				return
			}
			go func(c net.Conn) {
				defer c.Close()
				_, _ = io.Copy(c, c)
			}(c)
		}
	}()
	return ln.Addr().String()
}

func startGateway(t *testing.T, srv *identity.Identity, requireClient bool, allow [][]byte, upstream string) string {
	t.Helper()
	cfg, err := ServerConfig(srv, requireClient)
	if err != nil {
		t.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	go func() { _ = Serve(ln, cfg, allow, upstream, nil, nil) }()
	return ln.Addr().String()
}

func dial(t *testing.T, addr string, cfg *tls.Config) (*tls.Conn, error) {
	t.Helper()
	d := &net.Dialer{Timeout: 5 * time.Second}
	return tls.DialWithDialer(d, "tcp", addr, cfg)
}

// Standart rejim: TLS 1.3 + X25519MLKEM768 + ML-DSA-65 pinning, tunel orqali echo.
func TestStandardModeEchoWithPQKeyShare(t *testing.T) {
	srv, _ := identity.Generate()
	echo := startEcho(t)
	addr := startGateway(t, srv, false, nil, echo)

	cfg, err := ClientConfig(nil, srv.Pub)
	if err != nil {
		t.Fatal(err)
	}
	tc, err := dial(t, addr, cfg)
	if err != nil {
		t.Fatalf("ulanish: %v", err)
	}
	defer tc.Close()
	if Curve(tc) != tls.X25519MLKEM768 {
		t.Fatalf("kalit almashinuv: %v, X25519MLKEM768 kutilgan edi", Curve(tc))
	}
	if tc.ConnectionState().Version != tls.VersionTLS13 {
		t.Fatal("TLS 1.3 emas")
	}
	msg := []byte("standart PQ-TLS rejimi")
	if _, err := tc.Write(msg); err != nil {
		t.Fatal(err)
	}
	got := make([]byte, len(msg))
	if _, err := io.ReadFull(tc, got); err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got, msg) {
		t.Fatalf("echo: %q", got)
	}
}

// Metrika: ulanish, baytlar va Prometheus chiqishi to'g'ri hisoblanadi.
func TestMetricsCountConnectionsAndBytes(t *testing.T) {
	srv, _ := identity.Generate()
	echo := startEcho(t)
	cfg, err := ServerConfig(srv, false)
	if err != nil {
		t.Fatal(err)
	}
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(func() { _ = ln.Close() })
	m := &Metrics{}
	go func() { _ = Serve(ln, cfg, nil, echo, nil, m) }()

	ccfg, _ := ClientConfig(nil, srv.Pub)
	tc, err := dial(t, ln.Addr().String(), ccfg)
	if err != nil {
		t.Fatal(err)
	}
	msg := []byte("metrika sinovi")
	_, _ = tc.Write(msg)
	got := make([]byte, len(msg))
	if _, err := io.ReadFull(tc, got); err != nil {
		t.Fatal(err)
	}
	_ = tc.Close()

	// Server tomonidagi hisoblagichlar yangilanishini kutamiz.
	deadline := time.Now().Add(3 * time.Second)
	for m.BytesUpstream.Load() < int64(len(msg)) && time.Now().Before(deadline) {
		time.Sleep(10 * time.Millisecond)
	}
	if m.ConnectionsTotal.Load() != 1 {
		t.Fatalf("connections_total=%d", m.ConnectionsTotal.Load())
	}
	if m.BytesUpstream.Load() < int64(len(msg)) {
		t.Fatalf("bytes_upstream=%d", m.BytesUpstream.Load())
	}
	if m.handshakeCount.Load() != 1 {
		t.Fatalf("handshake_count=%d", m.handshakeCount.Load())
	}
	rec := httptest.NewRecorder()
	m.Handler().ServeHTTP(rec, httptest.NewRequest("GET", "/metrics", nil))
	if !strings.Contains(rec.Body.String(), "aqgw_connections_total 1") {
		t.Fatalf("/metrics chiqishi noto'g'ri:\n%s", rec.Body.String())
	}
}

// Pinning: noto'g'ri server kaliti rad etiladi.
func TestPinnedServerKeyMismatchRejected(t *testing.T) {
	srv, _ := identity.Generate()
	other, _ := identity.Generate()
	addr := startGateway(t, srv, false, nil, startEcho(t))
	cfg, _ := ClientConfig(nil, other.Pub)
	tc, err := dial(t, addr, cfg)
	if err == nil {
		_ = tc.Close()
		t.Fatal("noto'g'ri pinned kalit qabul qilindi")
	}
}

// Mutual TLS: allowlist'dagi klient o'tadi, boshqasi rad etiladi.
func TestMutualAuthAllowlist(t *testing.T) {
	srv, _ := identity.Generate()
	allowed, _ := identity.Generate()
	stranger, _ := identity.Generate()
	allow := [][]byte{allowed.Pub}
	addr := startGateway(t, srv, true, allow, startEcho(t))

	okCfg, _ := ClientConfig(allowed, srv.Pub)
	tc, err := dial(t, addr, okCfg)
	if err != nil {
		t.Fatalf("allowlist klienti rad etildi: %v", err)
	}
	msg := []byte("ruxsat etilgan")
	_, _ = tc.Write(msg)
	got := make([]byte, len(msg))
	if _, err := io.ReadFull(tc, got); err != nil || !bytes.Equal(got, msg) {
		t.Fatalf("allowlist echo: %v %q", err, got)
	}
	_ = tc.Close()

	badCfg, _ := ClientConfig(stranger, srv.Pub)
	bc, err := dial(t, addr, badCfg)
	if err == nil {
		_ = bc.SetDeadline(time.Now().Add(3 * time.Second))
		_, _ = bc.Write([]byte("x"))
		buf := make([]byte, 1)
		if n, rerr := bc.Read(buf); rerr == nil && n == 1 {
			_ = bc.Close()
			t.Fatal("allowlist'da yo'q klient tunelga kirdi")
		}
		_ = bc.Close()
	}
}
