// Package gateway — standart PQ-TLS rejimi (qo'shimcha): TLS 1.3, X25519MLKEM768 gibrid kalit almashinuvi,
// ML-DSA-65 sertifikat (pinning yoki allowlist). Asosiy rejim — AETHER-Q (Rust aq-sidecar).
//
// Ikkala tomon ham o'z identity'sining ML-DSA kalitini ishlatadi; sertifikat o'z-o'zidan imzolangan,
// ishonch CA orqali emas, balki PINNING orqali (tomonlar bir-birining ochiq kalitini biladi).
package gateway

import (
	"bytes"
	"crypto/mldsa"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"crypto/x509/pkix"
	"errors"
	"io"
	"math/big"
	"net"
	"sync/atomic"
	"time"

	"aqctl/internal/identity"
)

const handshakeTimeout = 20 * time.Second

// certFor — identity kaliti bilan o'z-o'zidan imzolangan ML-DSA-65 sertifikat.
func certFor(id *identity.Identity, cn string) (tls.Certificate, error) {
	serial, err := rand.Int(rand.Reader, big.NewInt(1<<62))
	if err != nil {
		return tls.Certificate{}, err
	}
	tmpl := &x509.Certificate{
		SerialNumber:          serial,
		Subject:               pkix.Name{CommonName: cn},
		NotBefore:             time.Now().Add(-time.Hour),
		NotAfter:              time.Now().AddDate(1, 0, 0),
		KeyUsage:              x509.KeyUsageDigitalSignature,
		ExtKeyUsage:           []x509.ExtKeyUsage{x509.ExtKeyUsageServerAuth, x509.ExtKeyUsageClientAuth},
		BasicConstraintsValid: true,
	}
	der, err := x509.CreateCertificate(rand.Reader, tmpl, tmpl, id.PrivateKey().PublicKey(), id.PrivateKey())
	if err != nil {
		return tls.Certificate{}, err
	}
	return tls.Certificate{Certificate: [][]byte{der}, PrivateKey: id.PrivateKey()}, nil
}

// leafPub — birinchi sertifikatning ML-DSA ochiq kaliti (baytlarda).
func leafPub(raw [][]byte) ([]byte, error) {
	if len(raw) == 0 {
		return nil, errors.New("gateway: sertifikat yo'q")
	}
	leaf, err := x509.ParseCertificate(raw[0])
	if err != nil {
		return nil, err
	}
	pk, ok := leaf.PublicKey.(*mldsa.PublicKey)
	if !ok {
		return nil, errors.New("gateway: sertifikat kaliti ML-DSA emas")
	}
	return pk.Bytes(), nil
}

// ServerConfig — server TLS konfiguratsiyasi. requireClient → klient ML-DSA sertifikati talab qilinadi;
// allowlist esa Serve da handshake'dan keyin tekshiriladi.
func ServerConfig(id *identity.Identity, requireClient bool) (*tls.Config, error) {
	cert, err := certFor(id, "aq-gateway-server")
	if err != nil {
		return nil, err
	}
	cfg := &tls.Config{MinVersion: tls.VersionTLS13, Certificates: []tls.Certificate{cert}}
	if requireClient {
		cfg.ClientAuth = tls.RequireAnyClientCert
	}
	return cfg, nil
}

// ClientConfig — klient TLS konfiguratsiyasi. serverPin — kutilayotgan server ochiq kaliti.
// id != nil bo'lsa mutual TLS uchun klient sertifikati yuboriladi.
func ClientConfig(id *identity.Identity, serverPin []byte) (*tls.Config, error) {
	cfg := &tls.Config{
		MinVersion: tls.VersionTLS13,
		// CA zanjiri o'rniga pinning: quyidagi VerifyPeerCertificate server kalitini tekshiradi.
		InsecureSkipVerify: true,
		VerifyPeerCertificate: func(raw [][]byte, _ [][]*x509.Certificate) error {
			pub, err := leafPub(raw)
			if err != nil {
				return err
			}
			if !bytes.Equal(pub, serverPin) {
				return errors.New("gateway: server ochiq kaliti pinned kalitga mos emas")
			}
			return nil
		},
	}
	if id != nil {
		cert, err := certFor(id, "aq-gateway-client")
		if err != nil {
			return nil, err
		}
		cfg.Certificates = []tls.Certificate{cert}
	}
	return cfg, nil
}

// checkPeer — mutual auth: klient ochiq kaliti allowlist'da bo'lishi kerak.
func checkPeer(c *tls.Conn, allow [][]byte) ([]byte, error) {
	st := c.ConnectionState()
	if len(st.PeerCertificates) == 0 {
		return nil, errors.New("gateway: klient sertifikati yo'q")
	}
	pk, ok := st.PeerCertificates[0].PublicKey.(*mldsa.PublicKey)
	if !ok {
		return nil, errors.New("gateway: klient kaliti ML-DSA emas")
	}
	pub := pk.Bytes()
	if allow != nil && !identity.Allowed(allow, pub) {
		return nil, errors.New("gateway: klient allowlist'da yo'q")
	}
	return pub, nil
}

type closeWriter interface{ CloseWrite() error }

// pump — ikki oqimni o'zaro bog'laydi. up: a→b baytlar, down: b→a baytlar hisoblagichi.
func pump(a, b net.Conn, up, down *atomic.Int64) {
	done := make(chan struct{}, 2)
	go func() {
		_, _ = io.Copy(countWriter{b, up}, a)
		if cw, ok := b.(closeWriter); ok {
			_ = cw.CloseWrite()
		}
		done <- struct{}{}
	}()
	go func() {
		_, _ = io.Copy(countWriter{a, down}, b)
		if cw, ok := a.(closeWriter); ok {
			_ = cw.CloseWrite()
		}
		done <- struct{}{}
	}()
	<-done
	<-done
	_ = a.Close()
	_ = b.Close()
}

// Serve — TLS listener; har ulanish uchun upstream (monolit) ga tunnel.
// logf ixtiyoriy (nil bo'lsa jim).
// m — hisoblagichlar (nil bo'lishi mumkin).
func Serve(ln net.Listener, cfg *tls.Config, allow [][]byte, upstream string, logf func(string, ...any), m *Metrics) error {
	if m == nil {
		m = &Metrics{}
	}
	tl := tls.NewListener(ln, cfg)
	needClient := cfg.ClientAuth != tls.NoClientCert
	for {
		c, err := tl.Accept()
		if err != nil {
			return err
		}
		m.ConnectionsTotal.Add(1)
		go handleServer(c, needClient, allow, upstream, logf, m)
	}
}

func handleServer(c net.Conn, needClient bool, allow [][]byte, upstream string, logf func(string, ...any), m *Metrics) {
	m.ActiveConnections.Add(1)
	defer m.ActiveConnections.Add(-1)
	tc := c.(*tls.Conn)
	start := time.Now()
	_ = tc.SetDeadline(time.Now().Add(handshakeTimeout))
	if err := tc.Handshake(); err != nil {
		m.HandshakeFailures.Add(1)
		logf2(logf, "gateway: handshake rad etildi: %v", err)
		_ = tc.Close()
		return
	}
	logf2(logf, "gateway: TLS %s, kalit almashinuv %v", tlsVersion(tc), Curve(tc))
	if needClient {
		pub, err := checkPeer(tc, allow)
		if err != nil {
			m.HandshakeFailures.Add(1)
			logf2(logf, "gateway: %v", err)
			_ = tc.Close()
			return
		}
		logf2(logf, "gateway: klient ulandi (%s)", identity.Fingerprint(pub))
	}
	m.ObserveHandshake(time.Since(start))
	_ = tc.SetDeadline(time.Time{})
	up, err := net.Dial("tcp", upstream)
	if err != nil {
		logf2(logf, "gateway: upstream %s ga ulanmadi: %v", upstream, err)
		_ = tc.Close()
		return
	}
	pump(tc, up, &m.BytesUpstream, &m.BytesDownstream)
}

// Connect — mahalliy oddiy listener; har ulanish uchun peer ga TLS (pinned) tunnel.
func Connect(ln net.Listener, peer string, cfg *tls.Config, logf func(string, ...any)) error {
	for {
		c, err := ln.Accept()
		if err != nil {
			return err
		}
		go func(local net.Conn) {
			d := &net.Dialer{Timeout: handshakeTimeout}
			tc, err := tls.DialWithDialer(d, "tcp", peer, cfg)
			if err != nil {
				logf2(logf, "gateway: peer %s ga ulanmadi: %v", peer, err)
				_ = local.Close()
				return
			}
			if st := tc.ConnectionState(); st.CurveID != 0 {
				logf2(logf, "gateway: tunel ochildi (kalit almashinuv: %v)", st.CurveID)
			}
			pump(local, tc, new(atomic.Int64), new(atomic.Int64))
		}(c)
	}
}

// Curve — ulangan TLS sessiyasining kalit almashinuv egri chizig'i (testlar uchun).
func Curve(c *tls.Conn) tls.CurveID {
	return c.ConnectionState().CurveID
}

func tlsVersion(c *tls.Conn) string {
	if c.ConnectionState().Version == tls.VersionTLS13 {
		return "1.3"
	}
	return "<1.3"
}

func logf2(logf func(string, ...any), format string, args ...any) {
	if logf != nil {
		logf(format, args...)
	}
}
