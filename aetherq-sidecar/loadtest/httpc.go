package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"net"
	"net/http"
	"syscall"
	"time"
)

// ioTimeout — bitta so'rov (yozish + javobni to'liq o'qish) uchun chegara. Oshsa — "timeout" xatosi.
const ioTimeout = 30 * time.Second

// opError — xato qaysi bosqichda bo'lganini saqlaydi (dial / write / read / read-body).
type opError struct {
	stage string
	err   error
}

func (e *opError) Error() string { return e.stage + ": " + e.err.Error() }
func (e *opError) Unwrap() error { return e.err }

// wsaNames — Windows soket xatolari (WSA kodlari) va Unix errno'lari uchun qisqa nomlar.
var wsaNames = map[uintptr]string{
	10048: "addrinuse", // WSAEADDRINUSE — vaqtinchalik portlar tugagan bo'lishi mumkin
	10053: "aborted",
	10054: "reset",
	10055: "nobufs", // WSAENOBUFS — port/bufer tugashi
	10060: "timeout",
	10061: "refused",
}

// errKind — xatoni hisobot uchun qisqa toifaga ajratadi: "<bosqich>:<tur>".
func errKind(err error) string {
	stage := "other"
	var oe *opError
	if errors.As(err, &oe) {
		stage = oe.stage
	}
	var ne net.Error
	var errno syscall.Errno
	switch {
	case errors.Is(err, io.EOF), errors.Is(err, io.ErrUnexpectedEOF):
		return stage + ":eof"
	case errors.As(err, &ne) && ne.Timeout():
		return stage + ":timeout"
	case errors.As(err, &errno):
		if n, ok := wsaNames[uintptr(errno)]; ok {
			return stage + ":" + n
		}
		switch errno {
		case syscall.ECONNRESET:
			return stage + ":reset"
		case syscall.ECONNREFUSED:
			return stage + ":refused"
		case syscall.EADDRINUSE:
			return stage + ":addrinuse"
		}
		return fmt.Sprintf("%s:errno-%d", stage, uintptr(errno))
	}
	return stage + ":other"
}

// hconn — bitta TCP ulanish ustida ketma-ket HTTP/1.1 so'rovlar (keep-alive).
type hconn struct {
	c    net.Conn
	br   *bufio.Reader
	bw   *bufio.Writer
	host string
}

func dialH(addr string) (*hconn, error) {
	c, err := net.DialTimeout("tcp", addr, 10*time.Second)
	if err != nil {
		return nil, &opError{"dial", err}
	}
	return &hconn{c: c, br: bufio.NewReaderSize(c, 32<<10), bw: bufio.NewWriterSize(c, 32<<10), host: addr}, nil
}

func (h *hconn) close() { _ = h.c.Close() }

// do — so'rovni yuborib, javobni to'liq o'qiydi. last=true: "Connection: close" (ulanishni server yopadi).
func (h *hconn) do(method, path string, body []byte, last bool) (int, []byte, error) {
	_ = h.c.SetDeadline(time.Now().Add(ioTimeout))
	fmt.Fprintf(h.bw, "%s %s HTTP/1.1\r\nHost: %s\r\nUser-Agent: aqload\r\n", method, path, h.host)
	if body != nil {
		fmt.Fprintf(h.bw, "Content-Type: application/json\r\nContent-Length: %d\r\n", len(body))
	}
	if last {
		_, _ = h.bw.WriteString("Connection: close\r\n")
	}
	_, _ = h.bw.WriteString("\r\n")
	_, _ = h.bw.Write(body)
	if err := h.bw.Flush(); err != nil {
		return 0, nil, &opError{"write", err}
	}
	resp, err := http.ReadResponse(h.br, nil)
	if err != nil {
		return 0, nil, &opError{"read", err}
	}
	data, err := io.ReadAll(resp.Body)
	_ = resp.Body.Close()
	if err != nil {
		return resp.StatusCode, nil, &opError{"read-body", err}
	}
	return resp.StatusCode, data, nil
}
