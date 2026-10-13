package identity

import (
	"os"
	"path/filepath"
	"testing"
)

// Go native fuzzing: fayl parserlari panic qilmasligi shart (xato qaytarishi mumkin).
// Ishga tushirish: go test -run=^$ -fuzz=FuzzLoadAllowlist -fuzztime=60s ./internal/identity/

func FuzzLoadAllowlist(f *testing.F) {
	f.Add([]byte("# izoh\n"))
	f.Add([]byte("zz\n"))
	f.Fuzz(func(t *testing.T, data []byte) {
		p := filepath.Join(t.TempDir(), "allow.txt")
		if err := os.WriteFile(p, data, 0o600); err != nil {
			t.Skip()
		}
		_, _ = LoadAllowlist(p)
	})
}

func FuzzLoadIdentity(f *testing.F) {
	f.Add([]byte("aq-identity v1\nseed=00\n"))
	f.Fuzz(func(t *testing.T, data []byte) {
		p := filepath.Join(t.TempDir(), "x.key")
		if err := os.WriteFile(p, data, 0o600); err != nil {
			t.Skip()
		}
		_, _ = Load(p)
	})
}

func FuzzLoadMeta(f *testing.F) {
	f.Add([]byte(`{"name":"x","not_after":"2026-01-01T00:00:00Z"}`))
	f.Fuzz(func(t *testing.T, data []byte) {
		p := filepath.Join(t.TempDir(), "x.meta.json")
		if err := os.WriteFile(p, data, 0o600); err != nil {
			t.Skip()
		}
		_, _ = LoadMeta(p)
	})
}
