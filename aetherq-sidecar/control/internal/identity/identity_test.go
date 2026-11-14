package identity

import (
	"bytes"
	"crypto/mldsa"
	"encoding/hex"
	"encoding/json"
	"os"
	"path/filepath"
	"testing"
)

// KAT: kat/aq51_wire_kat.json (Python referensi tomonidan yaratilgan).
func loadKAT(t *testing.T) map[string]any {
	t.Helper()
	data, err := os.ReadFile(filepath.Join("..", "..", "..", "kat", "aq51_wire_kat.json"))
	if err != nil {
		t.Fatalf("KAT o'qilmadi: %v", err)
	}
	var v struct {
		Vectors map[string]any `json:"vectors"`
	}
	if err := json.Unmarshal(data, &v); err != nil {
		t.Fatal(err)
	}
	return v.Vectors
}

func mustHex(t *testing.T, s string) []byte {
	t.Helper()
	b, err := hex.DecodeString(s)
	if err != nil {
		t.Fatal(err)
	}
	return b
}

// Python seed → pk va Python imzosini Go tekshiradi (uchinchi implementatsiya).
func TestMLDSAMatchesPythonKAT(t *testing.T) {
	v := loadKAT(t)["mldsa65"].(map[string]any)
	var seed [32]byte
	copy(seed[:], mustHex(t, v["seed"].(string)))
	id, err := FromSeed(seed)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(id.Pub, mustHex(t, v["pk"].(string))) {
		t.Fatal("ML-DSA ochiq kalit: Go ≠ Python")
	}
	msg := mustHex(t, v["msg"].(string))
	sig := mustHex(t, v["sig"].(string))
	pk := id.PrivateKey().PublicKey()
	if err := mldsa.Verify(pk, msg, sig, &mldsa.Options{}); err != nil {
		t.Fatalf("Python imzosi Go'da tekshirilmadi: %v", err)
	}
	bad := append([]byte{}, msg...)
	bad[0] ^= 1
	if mldsa.Verify(pk, bad, sig, &mldsa.Options{}) == nil {
		t.Fatal("buzilgan xabar qabul qilindi")
	}
}

// Rust aq-sidecar formatidagi fayl Go'da o'qiladi va seed'dan bir xil kalit chiqadi.
func TestSaveLoadRoundTripRustFormat(t *testing.T) {
	dir := t.TempDir()
	id, err := Generate()
	if err != nil {
		t.Fatal(err)
	}
	path := filepath.Join(dir, "x.key")
	if err := id.Save(path); err != nil {
		t.Fatal(err)
	}
	got, err := Load(path)
	if err != nil {
		t.Fatal(err)
	}
	if !bytes.Equal(got.Pub, id.Pub) {
		t.Fatal("qayta yuklash ochiq kalitni o'zgartirdi")
	}
	pubPath := filepath.Join(dir, "x.pub")
	if err := id.SavePublic(pubPath); err != nil {
		t.Fatal(err)
	}
	pub, err := LoadPublic(pubPath)
	if err != nil || !bytes.Equal(pub, id.Pub) {
		t.Fatalf("ochiq kalit: %v", err)
	}
}

func TestAllowlistParsing(t *testing.T) {
	dir := t.TempDir()
	a, _ := Generate()
	b, _ := Generate()
	content := "# izoh\n" + hex.EncodeToString(a.Pub) + "\n\n" + hex.EncodeToString(b.Pub) + "\n"
	path := filepath.Join(dir, "allow.txt")
	if err := os.WriteFile(path, []byte(content), 0o600); err != nil {
		t.Fatal(err)
	}
	list, err := LoadAllowlist(path)
	if err != nil {
		t.Fatal(err)
	}
	if len(list) != 2 || !Allowed(list, a.Pub) || !Allowed(list, b.Pub) {
		t.Fatal("allowlist noto'g'ri")
	}
	c, _ := Generate()
	if Allowed(list, c.Pub) {
		t.Fatal("allowlist'da yo'q kalit ruxsat oldi")
	}
}

func TestFingerprintShape(t *testing.T) {
	id, _ := Generate()
	fp := Fingerprint(id.Pub)
	if len(fp) != 19 || fp[4] != '-' || fp[9] != '-' || fp[14] != '-' {
		t.Fatalf("barmoq izi formati: %q", fp)
	}
}
