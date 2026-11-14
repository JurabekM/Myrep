package main

import (
	"fmt"
	"slices"
	"sort"
	"strings"
)

func f2(x float64) string { return fmt.Sprintf("%.2f", x) }

func errText(m map[string]int) string {
	if len(m) == 0 {
		return "0"
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := make([]string, 0, len(keys))
	for _, k := range keys {
		parts = append(parts, fmt.Sprintf("%s ×%d", k, m[k]))
	}
	return strings.Join(parts, ", ")
}

func cpuText(m map[string]float64, unit string) string {
	if len(m) == 0 {
		return "—"
	}
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	parts := make([]string, 0, len(keys))
	for _, k := range keys {
		parts = append(parts, fmt.Sprintf("%s %.2f %s", strings.TrimPrefix(strings.TrimPrefix(k, "aq_"), "gw_"), m[k], unit))
	}
	return strings.Join(parts, "; ")
}

// renderMarkdown — inson uchun hisobot (o'zbekcha). Barcha raqamlar o'lchangan (MEASURED).
func renderMarkdown(rep *Report) string {
	var b strings.Builder
	w := func(format string, a ...any) { fmt.Fprintf(&b, format, a...) }
	cfg, env := rep.Config, rep.Env

	w("# AETHER-Q sidecar — yuk sinovi hisoboti\n\n")
	mode := "to'liq"
	if cfg.Quick {
		mode = "**tez tekshiruv (-quick)** — hajmlar kichik, qabul mezoni sifatida hisoblanmaydi"
	}
	w("Boshlandi: %s · davomiyligi: %s · rejim: %s\n\n", rep.Started.Format("2006-01-02 15:04:05"),
		rep.Finished.Sub(rep.Started).Round(1e9), mode)
	w("Barcha raqamlar **MEASURED** — shu mashinada, loopback (127.0.0.1) orqali o'lchangan. Yuk generatori, sidecar'lar, ")
	w("gateway va monolit bitta kompyuterda bir xil %d mantiqiy CPU'ni bo'lishadi. Bu tarmoq kechikishi emas: ", env.LogicalCPUs)
	w("bu protokol, shifrlash va dasturiy yo'lning CPU narxi.\n\n")

	w("## Natija\n\n| Mezon | Holat | Tafsilot |\n|---|---|---|\n")
	for _, c := range rep.Criteria {
		st := "✅ PASS"
		if !c.Pass {
			st = "❌ FAIL"
		}
		w("| %s | %s | %s |\n", c.Name, st, c.Detail)
	}

	w("\n## Muhit\n\n| | |\n|---|---|\n")
	w("| CPU | %s (%d mantiqiy) |\n| OS | %s |\n| Go (yuk generatori) | %s |\n", env.CPU, env.LogicalCPUs, env.OS, env.GoVersion)
	w("| Vaqtinchalik portlar | %d dan, %d ta |\n| Taymer qadami (o'lchangan) | %.1f µs |\n", env.DynStart, env.DynCount, env.TimerStepUS)
	w("| Seed | %d |\n", cfg.Seed)
	w("\nSinalgan ikkilik fayllar (qaysi binar o'lchanganini isbotlash uchun):\n\n| Fayl | O'zgartirilgan | Hajm | SHA-256 |\n|---|---|---|---|\n")
	for _, bi := range env.Binaries {
		w("| `%s` | %s | %.1f MiB | `%s…` |\n", bi.Path, bi.Modified.Format("2006-01-02 15:04:05"), float64(bi.Size)/(1<<20), bi.SHA256[:16])
	}
	w("\nZanjirlarda mutual autentifikatsiya va allowlist yoqilgan: AETHER-Q (`--require-client-auth --allow`), ")
	w("standart rejim (`gateway serve --require-client-auth --allow`, klient sertifikati bilan).\n")

	if len(rep.Integrity) > 0 {
		w("\n## A. Bayt yaxlitligi (echo)\n\n")
		w("Har oqim: tasodifiy baytlar 1 B … 64 KiB bo'laklarda yoziladi, so'ng yozish tomoni yopiladi (half-close); ")
		w("echo qaytargan baytlar yuborilgani bilan **aynan** solishtiriladi. O'lchamlar: 0, 1, 2, 100, 1000, 16383, 16384, ")
		w("16385, 32768, 65535, 65536, 65537 B, 1 MiB, 1 MiB+1, 8 MiB va %d ta tasodifiy (≤ 512 KiB); %d parallel.\n\n", cfg.IntRandom, cfg.IntConc)
		w("| Zanjir | Oqim | To'g'ri | Farq | Xato | Hajm | ≥1 MiB oqim p50 / max |\n|---|---|---|---|---|---|---|\n")
		for _, r := range rep.Integrity {
			w("| %s | %d | %d | %d | %s | %.1f MiB | %s / %s ms |\n", r.Label, r.Streams, r.OK, r.Mismatch, errText(r.Errors),
				float64(r.Bytes)/(1<<20), f2(r.Big.P50), f2(r.Big.Max))
		}
	}

	if len(rep.HTTP) > 0 {
		h0 := rep.HTTP[0]
		w("\n## B. %d so'rov har zanjirda\n\n", h0.Requests)
		w("%d ulanish × %d so'rov (keep-alive, oxirgisida `Connection: close`), %d parallel ishchi. Aylana: ", h0.Conns, h0.PerConn, h0.Conc)
		w("`POST` (tasodifiy sarlavha ≤ 200 B va matn 0 … 10 000 B: o'zbek lotin/kirill, emoji, JSON maxsus belgilari) → ")
		w("`GET` (aynan shu matn qaytishi shart) → `DELETE` → `/healthz`. Javob mazmuni har safar tekshiriladi.\n\n")
		w("| Zanjir | OK / so'rov | Mos emas | Xato | so'rov/s | 1-so'rov (ulanish+tunel) p50 / p99 | keyingi so'rov p50 / p99 | CPU (s) |\n")
		w("|---|---|---|---|---|---|---|---|\n")
		for _, r := range rep.HTTP {
			errs := map[string]int{}
			for k, v := range r.Errors {
				if !strings.HasPrefix(k, "mismatch") {
					errs[k] = v
				}
			}
			w("| %s | %d / %d | %d | %s | %.0f | %s / %s ms | %s / %s ms | %s |\n", r.Label, r.OK, r.Requests, r.Mismatch,
				errText(errs), r.RPS, f2(r.First.P50), f2(r.First.P99), f2(r.Rest.P50), f2(r.Rest.P99), cpuText(r.CPU, "s"))
		}
	}

	if len(rep.Handshake) > 0 {
		var direct Summary
		for _, r := range rep.Handshake {
			if r.Path == "direct" {
				direct = r.Latency
			}
		}
		w("\n## C. Ketma-ket yangi ulanishlar\n\n")
		w("Har ulanish: TCP → zanjir (tunel handshake) → `GET /healthz` → javobning oxirgi bayti (server yopadi). ")
		w("Bittadan, ketma-ket. Qo'shimcha narx = zanjir p50 − to'g'ridan-to'g'ri p50.\n\n")
		w("| Zanjir | OK / n | p50 | p90 | p99 | p99.9 | max | qo'shimcha p50 | ulanish/s | CPU ms/ulanish |\n")
		w("|---|---|---|---|---|---|---|---|---|---|\n")
		for _, r := range rep.Handshake {
			over := "—"
			if r.Path != "direct" && direct.N > 0 {
				over = "+" + f2(r.Latency.P50-direct.P50) + " ms"
			}
			w("| %s | %d / %d | %s | %s | %s | %s | %s | %s | %.0f | %s |\n", r.Label, r.OK, r.Conns, f2(r.Latency.P50),
				f2(r.Latency.P90), f2(r.Latency.P99), f2(r.Latency.P999), f2(r.Latency.Max), over, r.ConnPerS, cpuText(r.CPUms, "ms"))
		}
		w("\nVaqt — ms. CPU ms/ulanish Windows jarayon hisobchisidan (donadorligi ~15,6 ms), shuning uchun faqat yuzlab ulanish bo'yicha o'rtacha sifatida ishonchli.\n")
	}

	if len(rep.Sweep) > 0 {
		w("\n## D. Parallellik\n\n")
		w("Har ulanish yangi tunel (eng og'ir holat: har so'rovda handshake). Daraja = bir vaqtda ochiq ulanishlar.\n\n")
		w("| Zanjir | Parallel | OK / n | ulanish/s | p50 | p99 | max | Xato | CPU ms/ulanish |\n|---|---|---|---|---|---|---|---|---|\n")
		for _, r := range rep.Sweep {
			w("| %s | %d | %d / %d | %.0f | %s | %s | %s | %s | %s |\n", r.Label, r.Conc, r.OK, r.Conns, r.ConnPerS,
				f2(r.Latency.P50), f2(r.Latency.P99), f2(r.Latency.Max), errText(r.Errors), cpuText(r.CPUms, "ms"))
		}
	}

	if len(rep.Resources) > 0 {
		w("\n## E. Resurslar (boshlang'ich → oxir)\n\n")
		w("Boshlang'ich — tayyorlik so'rovlaridan keyin; oxir — barcha bosqichlardan so'ng tinchlanish kutilgach. ")
		w("Oqish mezoni faqat Rust sidecar'lar uchun (thread-per-connection): thread soni boshlang'ichdan +2 dan oshmasligi kerak. ")
		w("Go jarayonlarida OS thread'lar runtime tomonidan qayta ishlatiladi — faqat ma'lumot uchun.\n\n")
		w("| Jarayon | Thread | Handle | Working set, MiB (boshl. → cho'qqi → oxir) | CPU jami, s | Oqish |\n|---|---|---|---|---|---|\n")
		for _, r := range rep.Resources {
			leak := "—"
			if r.Kind == "sidecar" {
				leak = "yo'q"
				if r.Leak {
					leak = "**BOR**"
				}
			}
			w("| %s | %d → %d | %d → %d | %.1f → %.1f → %.1f | %.2f | %s |\n", r.Label, r.Base.Threads, r.End.Threads,
				r.Base.Handles, r.End.Handles, r.Base.WorkingSetMB, r.End.PeakWSMB, r.End.WorkingSetMB, r.End.CPUSeconds, leak)
		}
	}

	w("\n## F. Log, resumption va gateway metrikasi\n\n")
	labels := make([]string, 0, len(rep.LogErrors))
	for l := range rep.LogErrors {
		labels = append(labels, l)
	}
	slices.Sort(labels)
	w("| Jarayon | Xato qatorlari | Namuna |\n|---|---|---|\n")
	for _, l := range labels {
		le := rep.LogErrors[l]
		ex := le.Example
		if ex == "" {
			ex = "—"
		}
		w("| %s | %d | %s |\n", l, le.Count, strings.ReplaceAll(ex, "|", "/"))
	}
	rs := rep.Resumption
	w("\nResumption (`aq_connect_resume` log'i): %d tunel ochildi, %d tasi resumption bilan. To'liq zanjirda (`aq_connect_full`): %d tunel, %d resumption.\n",
		rs.Opened, rs.Resumed, rs.FullOpened, rs.FullResumed)
	if len(rep.GwEnd) > 0 {
		w("\nGateway `/metrics` (sinov davomidagi o'sish): ulanishlar %.0f, handshake xatolari %.0f, upstream %.1f MiB, downstream %.1f MiB; oxirida faol tunellar %.0f.\n",
			rep.GwDelta["aqgw_connections_total"], rep.GwDelta["aqgw_handshake_failures_total"],
			rep.GwDelta[`aqgw_bytes_total{direction="upstream"}`]/(1<<20), rep.GwDelta[`aqgw_bytes_total{direction="downstream"}`]/(1<<20),
			rep.GwEnd["aqgw_active_connections"])
	}

	first := map[string]string{}
	add := func(prefix string, m map[string]string) {
		for k, v := range m {
			key := prefix + " · " + k
			if _, ok := first[key]; !ok {
				first[key] = v
			}
		}
	}
	for _, r := range rep.Integrity {
		add("A "+r.Path, r.FirstErr)
	}
	for _, r := range rep.HTTP {
		add("B "+r.Path, r.FirstErr)
	}
	for _, r := range rep.Handshake {
		add("C "+r.Path, r.FirstErr)
	}
	for _, r := range rep.Sweep {
		add(fmt.Sprintf("D %s ×%d", r.Path, r.Conc), r.FirstErr)
	}
	if len(first) > 0 {
		keys := make([]string, 0, len(first))
		for k := range first {
			keys = append(keys, k)
		}
		sort.Strings(keys)
		w("\n## Xatolar tafsiloti (har toifaning birinchi namunasi)\n\n| Joy · toifa | Matn |\n|---|---|\n")
		for _, k := range keys {
			w("| %s | %s |\n", k, strings.ReplaceAll(first[k], "|", "/"))
		}
	}

	if len(rep.PortWaits) > 0 {
		w("\n## Port kutishlari\n\nWindows'da yopilgan TCP ulanish ~2 daqiqa TIME_WAIT holatida vaqtinchalik portni band qiladi. ")
		w("Port tugashi sinovni buzmasligi uchun generator kerak bo'lganda kutdi:\n\n| Bosqichdan oldin | Kerak | TIME_WAIT | Kutildi |\n|---|---|---|---|\n")
		for _, p := range rep.PortWaits {
			w("| %s | %d | %d | %.0f s |\n", p.Before, p.Need, p.TWStart, p.Seconds)
		}
	}

	w("\n## Usul va cheklovlar\n\n")
	w("- Yuk generatori yopiq tsiklda ishlaydi (har ishchi javobni kutib, keyingisini yuboradi); rejalashtirilgan tezlik yo'q, shuning uchun Windows taymer donadorligi kechikishni buzmaydi.\n")
	w("- Persentillar nearest-rank usulida (interpolyatsiyasiz). p99.9 faqat n ≥ 1000 bo'lganda ma'noli.\n")
	w("- Hamma narsa bitta mashinada: generator ham CPU'ni egallaydi, shuning uchun parallellik natijalari server sig'imining pastki chegarasi.\n")
	w("- Bu sinov tarmoq sharoitini (kechikish, paket yo'qolishi) modellashtirmaydi va xavfsizlik auditi o'rnini bosmaydi.\n")
	return b.String()
}
