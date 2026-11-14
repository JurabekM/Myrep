package identity

import (
	"encoding/json"
	"os"
	"time"
)

// Meta — identity'ning amal qilish muddati (rotatsiya jadvali uchun). Fayl: NAME.meta.json.
type Meta struct {
	Name        string    `json:"name"`
	Fingerprint string    `json:"fingerprint"`
	Created     time.Time `json:"created"`
	NotAfter    time.Time `json:"not_after"`
}

// NewMeta — yangi identity uchun metadata (days kun amal qiladi).
func NewMeta(name string, pub []byte, days int, now time.Time) Meta {
	return Meta{
		Name:        name,
		Fingerprint: Fingerprint(pub),
		Created:     now.UTC(),
		NotAfter:    now.UTC().AddDate(0, 0, days),
	}
}

// SaveMeta — metadata faylini yozadi.
func SaveMeta(path string, m Meta) error {
	data, err := json.MarshalIndent(m, "", "  ")
	if err != nil {
		return err
	}
	return os.WriteFile(path, append(data, '\n'), 0o644)
}

// LoadMeta — metadata faylini o'qiydi.
func LoadMeta(path string) (Meta, error) {
	var m Meta
	data, err := os.ReadFile(path)
	if err != nil {
		return m, err
	}
	err = json.Unmarshal(data, &m)
	return m, err
}

// RotateAt — rotatsiya kerak bo'ladigan vaqt (muddatdan warnDays oldin).
func (m Meta) RotateAt(warnDays int) time.Time {
	return m.NotAfter.AddDate(0, 0, -warnDays)
}

// State — holat: "ok", "rotate-soon" yoki "expired".
func (m Meta) State(now time.Time, warnDays int) string {
	switch {
	case !now.Before(m.NotAfter):
		return "expired"
	case !now.Before(m.RotateAt(warnDays)):
		return "rotate-soon"
	default:
		return "ok"
	}
}
