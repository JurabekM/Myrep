package main

import (
	"math/rand/v2"
	"strings"
	"unicode/utf8"
)

// Monolit chegaralari (aether_new/store.go bilan bir xil).
const (
	maxTitleBytes = 200
	maxBodyBytes  = 10000
)

// alphabet — JSON kodlash/dekodlash yo'lida baytlar o'zgarmasligini sinash uchun: ASCII, JSON maxsus
// belgilari, boshqaruv belgilari, o'zbek lotin va kirill harflari, ko'p baytli belgilar, U+2028/2029, emoji.
var alphabet = []rune("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789" +
	" .,;:!?-_/\\\"'{}[]<>&%$#@*+=|~`^" + "\t\n\r" +
	"ʻʼ‘’ğşçöüÄÖÜ" + "абвгдеёжзийклмнопрстуфхцчшщъыьэюяқғҳўЎҚҒҲ" +
	"€£¥©®™…—–" + "  " + "😀🔐🚀🌙✅")

// randText — aniq n baytli tasodifiy UTF-8 matn (chegaraga sig'maydigan belgi 1 baytli 'x' bilan almashadi).
func randText(r *rand.Rand, n int) string {
	var b strings.Builder
	b.Grow(n)
	for b.Len() < n {
		c := alphabet[r.IntN(len(alphabet))]
		if b.Len()+utf8.RuneLen(c) > n {
			c = 'x'
		}
		b.WriteRune(c)
	}
	return b.String()
}

// randTitle — 1..200 bayt. Chetlari harf: server sarlavhani TrimSpace qiladi, ichidagi bo'shliqlar qoladi.
func randTitle(r *rand.Rand) string {
	n := 1 + r.IntN(maxTitleBytes)
	if n == 1 {
		return "T"
	}
	return "T" + randText(r, n-2) + "z"
}

// randBody — 0..10000 bayt: 10% juda qisqa (bo'sh ham), 60% ≤4000, 20% 4000..10000, 10% aynan 10000.
func randBody(r *rand.Rand) string {
	var n int
	switch x := r.IntN(100); {
	case x < 10:
		n = r.IntN(17)
	case x < 70:
		n = r.IntN(4001)
	case x < 90:
		n = 4000 + r.IntN(6001)
	default:
		n = maxBodyBytes
	}
	return randText(r, n)
}
