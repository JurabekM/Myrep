package identity

import (
	"path/filepath"
	"testing"
	"time"
)

func TestMetaStateTransitions(t *testing.T) {
	now := time.Date(2026, 10, 12, 0, 0, 0, 0, time.UTC)
	m := NewMeta("srv", make([]byte, pkLen), 30, now)
	if got := m.State(now, 14); got != "ok" {
		t.Fatalf("boshida: %s", got)
	}
	// 30 kun, rotatsiya 14 kun oldin → 16-kundan keyin "rotate-soon"
	if got := m.State(now.AddDate(0, 0, 17), 14); got != "rotate-soon" {
		t.Fatalf("17-kun: %s", got)
	}
	if got := m.State(now.AddDate(0, 0, 31), 14); got != "expired" {
		t.Fatalf("31-kun: %s", got)
	}
}

func TestMetaRoundTrip(t *testing.T) {
	dir := t.TempDir()
	id, err := Generate()
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "x.meta.json")
	m := NewMeta("x", id.Pub, 90, time.Now())
	if err := SaveMeta(path, m); err != nil {
		t.Fatal(err)
	}
	got, err := LoadMeta(path)
	if err != nil {
		t.Fatal(err)
	}
	if got.Fingerprint != Fingerprint(id.Pub) || got.Name != "x" {
		t.Fatalf("meta: %+v", got)
	}
}
