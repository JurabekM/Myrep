package main

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"path/filepath"
	"testing"
)

func newTestServer(t *testing.T, path string) (*httptest.Server, *Store) {
	t.Helper()
	st, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	ts := httptest.NewServer(NewMux(st))
	t.Cleanup(ts.Close)
	return ts, st
}

func do(t *testing.T, method, url string, body any) (*http.Response, []byte) {
	t.Helper()
	var rd *bytes.Reader
	if body != nil {
		b, _ := json.Marshal(body)
		rd = bytes.NewReader(b)
	} else {
		rd = bytes.NewReader(nil)
	}
	req, _ := http.NewRequest(method, url, rd)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	var buf bytes.Buffer
	_, _ = buf.ReadFrom(resp.Body)
	return resp, buf.Bytes()
}

func TestHealthz(t *testing.T) {
	ts, _ := newTestServer(t, "")
	resp, body := do(t, "GET", ts.URL+"/healthz", nil)
	if resp.StatusCode != 200 || !bytes.Contains(body, []byte(`"status":"ok"`)) {
		t.Fatalf("healthz: %d %s", resp.StatusCode, body)
	}
}

func TestRecordsCRUD(t *testing.T) {
	ts, _ := newTestServer(t, filepath.Join(t.TempDir(), "d.json"))
	resp, body := do(t, "POST", ts.URL+"/api/v1/records", map[string]string{"title": "Birinchi", "body": "matn"})
	if resp.StatusCode != http.StatusCreated {
		t.Fatalf("create: %d %s", resp.StatusCode, body)
	}
	var rec Record
	if err := json.Unmarshal(body, &rec); err != nil || rec.ID != 1 || rec.Title != "Birinchi" {
		t.Fatalf("create javobi: %v %+v", err, rec)
	}
	resp, body = do(t, "GET", ts.URL+"/api/v1/records/1", nil)
	if resp.StatusCode != 200 {
		t.Fatalf("get: %d %s", resp.StatusCode, body)
	}
	resp, body = do(t, "GET", ts.URL+"/api/v1/records", nil)
	if resp.StatusCode != 200 || !bytes.Contains(body, []byte("Birinchi")) {
		t.Fatalf("list: %d %s", resp.StatusCode, body)
	}
	resp, _ = do(t, "DELETE", ts.URL+"/api/v1/records/1", nil)
	if resp.StatusCode != http.StatusNoContent {
		t.Fatalf("delete: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", ts.URL+"/api/v1/records/1", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("o'chirilgandan keyin 404 kutilgan edi: %d", resp.StatusCode)
	}
}

func TestValidationAndErrors(t *testing.T) {
	ts, _ := newTestServer(t, "")
	resp, _ := do(t, "POST", ts.URL+"/api/v1/records", map[string]string{"title": "   "})
	if resp.StatusCode != http.StatusUnprocessableEntity {
		t.Fatalf("bo'sh title: %d", resp.StatusCode)
	}
	resp, _ = do(t, "GET", ts.URL+"/api/v1/records/abc", nil)
	if resp.StatusCode != http.StatusBadRequest {
		t.Fatalf("noto'g'ri ID: %d", resp.StatusCode)
	}
	resp, _ = do(t, "DELETE", ts.URL+"/api/v1/records/99", nil)
	if resp.StatusCode != http.StatusNotFound {
		t.Fatalf("yo'q yozuv: %d", resp.StatusCode)
	}
}

// Ma'lumot fayl orqali qayta ochilganda saqlanib qoladi (JSON ombor).
func TestPersistenceAcrossRestart(t *testing.T) {
	path := filepath.Join(t.TempDir(), "d.json")
	st, _ := OpenStore(path)
	if _, err := st.Create("saqlansin", "x", nowForTest()); err != nil {
		t.Fatal(err)
	}
	st2, err := OpenStore(path)
	if err != nil {
		t.Fatal(err)
	}
	got := st2.List()
	if len(got) != 1 || got[0].Title != "saqlansin" {
		t.Fatalf("qayta ochilgandan keyin: %+v", got)
	}
	r, _ := st2.Create("keyingi", "", nowForTest())
	if r.ID != 2 {
		t.Fatalf("ID davomiyligi: %d", r.ID)
	}
}
