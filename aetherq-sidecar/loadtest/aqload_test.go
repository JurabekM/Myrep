package main

import (
	"encoding/json"
	"math/rand/v2"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
	"unicode"
	"unicode/utf8"
)

func TestPercentileNearestRank(t *testing.T) {
	xs := []float64{1, 2, 3, 4, 5, 6, 7, 8, 9, 10}
	cases := map[float64]float64{50: 5, 90: 9, 99: 10, 100: 10, 1: 1}
	for p, want := range cases {
		if got := percentile(xs, p); got != want {
			t.Errorf("p%.0f = %v, kutilgan %v", p, got, want)
		}
	}
	s := summarize([]time.Duration{3 * time.Millisecond, time.Millisecond, 2 * time.Millisecond})
	if s.N != 3 || s.Min != 1 || s.Max != 3 || s.P50 != 2 || s.Mean != 2 {
		t.Fatalf("summarize: %+v", s)
	}
	if (summarize(nil) != Summary{}) {
		t.Fatal("bo'sh namuna nol bo'lishi kerak")
	}
}

func TestPayloadRespectsServerLimits(t *testing.T) {
	r := rand.New(rand.NewPCG(1, 2))
	sawEmpty, sawMax := false, false
	for i := 0; i < 3000; i++ {
		title, body := randTitle(r), randBody(r)
		if len(title) < 1 || len(title) > maxTitleBytes || strings.TrimSpace(title) != title {
			t.Fatalf("sarlavha chegarasi buzildi: %d B, %q", len(title), title)
		}
		if len(body) > maxBodyBytes || !utf8.ValidString(body) || !utf8.ValidString(title) {
			t.Fatalf("matn chegarasi/UTF-8 buzildi: %d B", len(body))
		}
		sawEmpty = sawEmpty || body == ""
		sawMax = sawMax || len(body) == maxBodyBytes
		// JSON orqali aylanib kelganda aynan o'zi qolishi kerak (monolit shunday qaytaradi).
		raw, _ := json.Marshal(map[string]string{"title": title, "body": body})
		if len(raw) > 64*1024 {
			t.Fatalf("so'rov tanasi monolit chegarasidan (64 KiB) katta: %d", len(raw))
		}
		var back map[string]string
		if err := json.Unmarshal(raw, &back); err != nil || back["title"] != title || back["body"] != body {
			t.Fatal("JSON aylanishida matn o'zgardi")
		}
	}
	if !sawEmpty || !sawMax {
		t.Fatalf("chegaraviy holatlar chiqmadi: bo'sh=%v, 10000B=%v", sawEmpty, sawMax)
	}
}

func TestRandTextExactLengthAndNonASCII(t *testing.T) {
	r := rand.New(rand.NewPCG(3, 4))
	nonASCII := false
	for n := 0; n < 300; n++ {
		s := randText(r, n)
		if len(s) != n || !utf8.ValidString(s) {
			t.Fatalf("randText(%d) = %d B", n, len(s))
		}
		for _, c := range s {
			if c > unicode.MaxASCII {
				nonASCII = true
			}
		}
	}
	if !nonASCII {
		t.Fatal("ko'p baytli belgilar umuman chiqmadi")
	}
}

func TestCountTimeWaitAndFirstInts(t *testing.T) {
	out := "\r\nActive Connections\r\n\r\n  Proto  Local Address          Foreign Address        State\r\n" +
		"  TCP    127.0.0.1:21000        127.0.0.1:50001        TIME_WAIT\r\n" +
		"  TCP    127.0.0.1:50002        127.0.0.1:21443        TIME_WAIT\r\n" +
		"  TCP    [::1]:60000            [::1]:21080            TIME_WAIT\r\n" +
		"  TCP    127.0.0.1:50003        127.0.0.1:21443        ESTABLISHED\r\n"
	total, eph := countTimeWait(out, 49152, 16384)
	if total != 3 || eph != 2 {
		t.Fatalf("total=%d eph=%d, kutilgan 3/2", total, eph)
	}
	if got := firstInts("Start Port      : 49152\r\nNumber of Ports : 16384\r\n", 2); len(got) != 2 || got[0] != 49152 || got[1] != 16384 {
		t.Fatalf("firstInts: %v", got)
	}
}

// hconn haqiqiy Go HTTP serveriga qarshi: keep-alive, chunked javob (katta tana), 204, Connection: close.
func TestHConnKeepAliveChunkedAndClose(t *testing.T) {
	big := strings.Repeat("ʻ", 6000) // 12 000 B — Go serveri chunked yuboradi
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/big":
			_, _ = w.Write([]byte(big))
		case "/empty":
			w.WriteHeader(http.StatusNoContent)
		default:
			_, _ = w.Write([]byte(`{"status":"ok"}`))
		}
	}))
	defer srv.Close()
	h, err := dialH(strings.TrimPrefix(srv.URL, "http://"))
	if err != nil {
		t.Fatal(err)
	}
	defer h.close()
	for i := 0; i < 3; i++ {
		st, body, err := h.do("GET", "/big", nil, false)
		if err != nil || st != 200 || string(body) != big {
			t.Fatalf("big #%d: st=%d len=%d err=%v", i, st, len(body), err)
		}
	}
	if st, body, err := h.do("GET", "/empty", nil, false); err != nil || st != 204 || len(body) != 0 {
		t.Fatalf("204: st=%d err=%v", st, err)
	}
	if st, _, err := h.do("POST", "/x", []byte(`{"a":1}`), true); err != nil || st != 200 {
		t.Fatalf("oxirgi: st=%d err=%v", st, err)
	}
	// Server "Connection: close" dan keyin ulanishni yopgan — keyingi so'rov EOF/reset bilan tugashi kerak.
	if _, _, err := h.do("GET", "/", nil, false); err == nil {
		t.Fatal("yopilgan ulanishda xato kutilgan edi")
	} else if k := errKind(err); !strings.HasPrefix(k, "read:") && !strings.HasPrefix(k, "write:") {
		t.Fatalf("xato toifasi: %s (%v)", k, err)
	}
}

func TestEchoOnceHalfClose(t *testing.T) {
	ln, err := netListen()
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	go serveEcho(ln)
	r := rand.New(rand.NewPCG(5, 6))
	for _, n := range []int{0, 1, 16384, 200000} {
		payload := make([]byte, n)
		fillRandom(r, payload)
		_, got, err := echoOnce(ln.Addr().String(), payload, chunkPlan(r, n))
		if err != nil || string(got) != string(payload) {
			t.Fatalf("%d B: qaytdi %d B, err=%v", n, len(got), err)
		}
	}
}
