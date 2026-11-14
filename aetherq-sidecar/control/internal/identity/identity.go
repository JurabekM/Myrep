// Package identity — ML-DSA-65 (FIPS 204) identity: Rust aq-sidecar bilan bir xil fayl formati.
//
//	aq-identity v1
//	seed=<64 hex>   (maxfiy)
//	pk=<3904 hex>   (ochiq, 1952 bayt)
package identity

import (
	"crypto/mldsa"
	"crypto/rand"
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"os"
	"strings"
)

const (
	header  = "aq-identity v1"
	seedLen = 32
	pkLen   = 1952
)

// Identity — maxfiy seed va undan olingan ML-DSA-65 kalit juftligi.
type Identity struct {
	Seed [seedLen]byte
	Pub  []byte
	priv *mldsa.PrivateKey
}

// Generate — yangi tasodifiy identity.
func Generate() (*Identity, error) {
	var seed [seedLen]byte
	if _, err := rand.Read(seed[:]); err != nil {
		return nil, err
	}
	return FromSeed(seed)
}

// FromSeed — seed'dan deterministik identity (FIPS 204 KeyGen).
func FromSeed(seed [seedLen]byte) (*Identity, error) {
	k, err := mldsa.NewPrivateKey(mldsa.MLDSA65(), seed[:])
	if err != nil {
		return nil, err
	}
	pub := k.PublicKey().Bytes()
	if len(pub) != pkLen {
		return nil, fmt.Errorf("identity: ochiq kalit uzunligi %d", len(pub))
	}
	return &Identity{Seed: seed, Pub: pub, priv: k}, nil
}

// PrivateKey — imzolash uchun kalit.
func (id *Identity) PrivateKey() *mldsa.PrivateKey { return id.priv }

// Save — maxfiy identity faylini yozadi (0600).
func (id *Identity) Save(path string) error {
	text := fmt.Sprintf("%s\nseed=%s\npk=%s\n", header, hex.EncodeToString(id.Seed[:]), hex.EncodeToString(id.Pub))
	return os.WriteFile(path, []byte(text), 0o600)
}

// SavePublic — ochiq kalitni hex holda yozadi (pinning / allowlist uchun).
func (id *Identity) SavePublic(path string) error {
	return os.WriteFile(path, []byte(hex.EncodeToString(id.Pub)+"\n"), 0o644)
}

// Load — identity faylini o'qiydi va ochiq kalitni seed'dan qayta hisoblaydi.
func Load(path string) (*Identity, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var seedHex string
	for _, line := range strings.Split(string(data), "\n") {
		if v, ok := strings.CutPrefix(strings.TrimSpace(line), "seed="); ok {
			seedHex = v
		}
	}
	raw, err := hex.DecodeString(seedHex)
	if err != nil || len(raw) != seedLen {
		return nil, errors.New("identity: seed yaroqsiz")
	}
	var seed [seedLen]byte
	copy(seed[:], raw)
	return FromSeed(seed)
}

// LoadPublic — hex ochiq kalit faylini o'qiydi.
func LoadPublic(path string) ([]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	raw, err := hex.DecodeString(strings.TrimSpace(string(data)))
	if err != nil || len(raw) != pkLen {
		return nil, errors.New("identity: ochiq kalit yaroqsiz")
	}
	return raw, nil
}

// LoadAllowlist — har qatorda bitta hex ochiq kalit; '#' izoh.
func LoadAllowlist(path string) ([][]byte, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var out [][]byte
	for _, line := range strings.Split(string(data), "\n") {
		t := strings.TrimSpace(line)
		if t == "" || strings.HasPrefix(t, "#") {
			continue
		}
		raw, err := hex.DecodeString(t)
		if err != nil || len(raw) != pkLen {
			return nil, fmt.Errorf("identity: allowlist qatori yaroqsiz: %.16s...", t)
		}
		out = append(out, raw)
	}
	return out, nil
}

// Fingerprint — ochiq kalitning qisqa barmoq izi (SHA-256, 16 hex, 4 guruh).
func Fingerprint(pub []byte) string {
	sum := sha256.Sum256(pub)
	h := hex.EncodeToString(sum[:8])
	return h[0:4] + "-" + h[4:8] + "-" + h[8:12] + "-" + h[12:16]
}

// Allowed — pub allowlist'da bormi.
func Allowed(list [][]byte, pub []byte) bool {
	for _, a := range list {
		if string(a) == string(pub) {
			return true
		}
	}
	return false
}
