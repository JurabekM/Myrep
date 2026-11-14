// aqctl — AETHER-Q control plane (identity, muddat/rotatsiya, allowlist, holat) va standart PQ-TLS gateway.
//
//	aqctl identity new  --out NAME [--days 90]   NAME.key, NAME.key.pub, NAME.meta.json
//	aqctl identity show --file FILE              ochiq kalit va barmoq izi
//	aqctl identity rotate --name OLD --out NEW [--days 90] [--allow FILE]
//	aqctl schedule --dir DIR [--warn-days 14]    rotatsiya jadvali (JSON)
//	aqctl allowlist build  --out FILE PUB...     ochiq kalitlardan allowlist
//	aqctl allowlist retire --allow FILE --pub F  kalitni allowlist'dan olib tashlash
//	aqctl status --dir DIR [--allow FILE]        identity'lar, muddat, allowlist holati
//	aqctl gateway serve   --listen A --upstream A --identity F [--require-client-auth] [--allow F] [--metrics A]
//	aqctl gateway connect --listen A --peer A --server-pub F|HEX [--identity F]
package main

import (
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"net"
	"net/http"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"time"

	"aqctl/internal/gateway"
	"aqctl/internal/identity"
)

func usage() int {
	fmt.Fprintln(os.Stderr, `aqctl — AETHER-Q control plane va standart PQ-TLS gateway

buyruqlar:
  identity new  --out NAME [--days 90]
  identity show --file FILE
  identity rotate --name OLD --out NEW [--days 90] [--allow FILE]
  schedule --dir DIR [--warn-days 14]
  allowlist build  --out FILE PUB...
  allowlist retire --allow FILE --pub FILE
  status --dir DIR [--allow FILE]
  gateway serve   --listen ADDR --upstream ADDR --identity FILE [--require-client-auth] [--allow FILE] [--metrics ADDR]
  gateway connect --listen ADDR --peer ADDR --server-pub FILE|HEX [--identity FILE]`)
	return 2
}

func fail(err error) int {
	fmt.Fprintln(os.Stderr, "aqctl:", err)
	return 1
}

func logf(format string, args ...any) {
	fmt.Fprintf(os.Stderr, "aqctl: "+format+"\n", args...)
}

func main() {
	os.Exit(run(os.Args[1:]))
}

func run(args []string) int {
	if len(args) < 1 {
		return usage()
	}
	if args[0] == "status" {
		return cmdStatus(args[1:])
	}
	if args[0] == "schedule" {
		return cmdSchedule(args[1:])
	}
	if len(args) < 2 {
		return usage()
	}
	switch args[0] + " " + args[1] {
	case "identity new":
		return cmdIdentityNew(args[2:])
	case "identity show":
		return cmdIdentityShow(args[2:])
	case "identity rotate":
		return cmdIdentityRotate(args[2:])
	case "allowlist build":
		return cmdAllowlistBuild(args[2:])
	case "allowlist retire":
		return cmdAllowlistRetire(args[2:])
	case "gateway serve":
		return cmdGatewayServe(args[2:])
	case "gateway connect":
		return cmdGatewayConnect(args[2:])
	}
	return usage()
}

// writeIdentity — kalit juftligini (key, pub, meta) diskka yozadi.
func writeIdentity(name string, id *identity.Identity, days int) error {
	if err := id.Save(name + ".key"); err != nil {
		return err
	}
	if err := id.SavePublic(name + ".key.pub"); err != nil {
		return err
	}
	return identity.SaveMeta(name+".meta.json", identity.NewMeta(filepath.Base(name), id.Pub, days, time.Now()))
}

func cmdIdentityNew(args []string) int {
	fs := flag.NewFlagSet("identity new", flag.ContinueOnError)
	out := fs.String("out", "", "identity nomi (NAME.key, NAME.key.pub, NAME.meta.json yoziladi)")
	days := fs.Int("days", 90, "amal qilish muddati (kun)")
	if fs.Parse(args) != nil || *out == "" {
		return usage()
	}
	id, err := identity.Generate()
	if err != nil {
		return fail(err)
	}
	if err := writeIdentity(*out, id, *days); err != nil {
		return fail(err)
	}
	fmt.Println(hex.EncodeToString(id.Pub))
	logf("identity yozildi: %s.key (maxfiy), %s.key.pub, %s.meta.json; barmoq izi %s, %d kun", *out, *out, *out, identity.Fingerprint(id.Pub), *days)
	return 0
}

func cmdIdentityShow(args []string) int {
	fs := flag.NewFlagSet("identity show", flag.ContinueOnError)
	file := fs.String("file", "", "identity (.key) yoki ochiq kalit (.pub) fayli")
	if fs.Parse(args) != nil || *file == "" {
		return usage()
	}
	var pub []byte
	if strings.HasSuffix(*file, ".pub") {
		p, err := identity.LoadPublic(*file)
		if err != nil {
			return fail(err)
		}
		pub = p
	} else {
		id, err := identity.Load(*file)
		if err != nil {
			return fail(err)
		}
		pub = id.Pub
	}
	fmt.Printf("barmoq izi: %s\nochiq kalit: %s\n", identity.Fingerprint(pub), hex.EncodeToString(pub))
	return 0
}

// cmdIdentityRotate — yangi identity yaratadi. --allow berilsa, allowlist'ga eski va yangi kalit
// birga qo'shiladi (overlap davri: klientlar yangisiga o'tguncha ikkalasi ham ishlaydi).
func cmdIdentityRotate(args []string) int {
	fs := flag.NewFlagSet("identity rotate", flag.ContinueOnError)
	oldName := fs.String("name", "", "eski identity nomi (NAME.key)")
	out := fs.String("out", "", "yangi identity nomi")
	days := fs.Int("days", 90, "yangi kalit muddati (kun)")
	allowFile := fs.String("allow", "", "allowlist (overlap uchun eski+yangi kalit yoziladi)")
	if fs.Parse(args) != nil || *oldName == "" || *out == "" {
		return usage()
	}
	old, err := identity.Load(*oldName + ".key")
	if err != nil {
		return fail(err)
	}
	fresh, err := identity.Generate()
	if err != nil {
		return fail(err)
	}
	if err := writeIdentity(*out, fresh, *days); err != nil {
		return fail(err)
	}
	if *allowFile != "" {
		list, err := identity.LoadAllowlist(*allowFile)
		if err != nil && !os.IsNotExist(err) {
			return fail(err)
		}
		if !identity.Allowed(list, old.Pub) {
			list = append(list, old.Pub)
		}
		list = append(list, fresh.Pub)
		if err := writeAllowlist(*allowFile, list); err != nil {
			return fail(err)
		}
		logf("overlap: %s allowlist'ga eski (%s) va yangi (%s) kalit qo'shildi", *allowFile, identity.Fingerprint(old.Pub), identity.Fingerprint(fresh.Pub))
	}
	logf("rotatsiya: %s → %s (yangi barmoq izi %s)", *oldName, *out, identity.Fingerprint(fresh.Pub))
	logf("keyingi qadam: yangi .key ni server'ga o'rnating, klientlarni yangi server kaliti bilan yangilang; keyin allowlist retire bilan eskisini olib tashlang")
	return 0
}

func writeAllowlist(path string, keys [][]byte) error {
	var lines []string
	for _, k := range keys {
		lines = append(lines, "# "+identity.Fingerprint(k), hex.EncodeToString(k))
	}
	return os.WriteFile(path, []byte(strings.Join(lines, "\n")+"\n"), 0o644)
}

func cmdAllowlistBuild(args []string) int {
	fs := flag.NewFlagSet("allowlist build", flag.ContinueOnError)
	out := fs.String("out", "", "allowlist fayli")
	if fs.Parse(args) != nil || *out == "" || fs.NArg() == 0 {
		return usage()
	}
	var keys [][]byte
	for _, f := range fs.Args() {
		pub, err := identity.LoadPublic(f)
		if err != nil {
			return fail(fmt.Errorf("%s: %w", f, err))
		}
		keys = append(keys, pub)
	}
	if err := writeAllowlist(*out, keys); err != nil {
		return fail(err)
	}
	logf("allowlist yozildi: %s (%d kalit)", *out, len(keys))
	return 0
}

func cmdAllowlistRetire(args []string) int {
	fs := flag.NewFlagSet("allowlist retire", flag.ContinueOnError)
	allowFile := fs.String("allow", "", "allowlist fayli")
	pubFile := fs.String("pub", "", "olib tashlanadigan ochiq kalit fayli")
	if fs.Parse(args) != nil || *allowFile == "" || *pubFile == "" {
		return usage()
	}
	pub, err := identity.LoadPublic(*pubFile)
	if err != nil {
		return fail(err)
	}
	list, err := identity.LoadAllowlist(*allowFile)
	if err != nil {
		return fail(err)
	}
	var kept [][]byte
	removed := 0
	for _, k := range list {
		if string(k) == string(pub) {
			removed++
			continue
		}
		kept = append(kept, k)
	}
	if err := writeAllowlist(*allowFile, kept); err != nil {
		return fail(err)
	}
	logf("allowlist: %d ta yozuv olib tashlandi (%s)", removed, identity.Fingerprint(pub))
	return 0
}

// scheduleEntry — bitta identity'ning rotatsiya holati.
type scheduleEntry struct {
	Name        string    `json:"name"`
	Fingerprint string    `json:"fingerprint"`
	Created     time.Time `json:"created"`
	NotAfter    time.Time `json:"not_after"`
	RotateAt    time.Time `json:"rotate_at"`
	DaysLeft    int       `json:"days_left"`
	State       string    `json:"state"`
}

func collectSchedule(dir string, warnDays int, now time.Time) ([]scheduleEntry, error) {
	matches, err := filepath.Glob(filepath.Join(dir, "*.meta.json"))
	if err != nil {
		return nil, err
	}
	sort.Strings(matches)
	var out []scheduleEntry
	for _, m := range matches {
		meta, err := identity.LoadMeta(m)
		if err != nil {
			return nil, fmt.Errorf("%s: %w", m, err)
		}
		days := int(meta.NotAfter.Sub(now).Hours() / 24)
		out = append(out, scheduleEntry{
			Name:        meta.Name,
			Fingerprint: meta.Fingerprint,
			Created:     meta.Created,
			NotAfter:    meta.NotAfter,
			RotateAt:    meta.RotateAt(warnDays),
			DaysLeft:    days,
			State:       meta.State(now, warnDays),
		})
	}
	return out, nil
}

// cmd schedule — rotatsiya jadvali (JSON).
func cmdSchedule(args []string) int {
	fs := flag.NewFlagSet("schedule", flag.ContinueOnError)
	dir := fs.String("dir", "", "identity papkasi")
	warn := fs.Int("warn-days", 14, "muddatdan necha kun oldin rotatsiya")
	if fs.Parse(args) != nil || *dir == "" {
		return usage()
	}
	entries, err := collectSchedule(*dir, *warn, time.Now())
	if err != nil {
		return fail(err)
	}
	if entries == nil {
		entries = []scheduleEntry{}
	}
	enc := json.NewEncoder(os.Stdout)
	enc.SetIndent("", "  ")
	if err := enc.Encode(entries); err != nil {
		return fail(err)
	}
	return 0
}

func cmdStatus(args []string) int {
	fs := flag.NewFlagSet("status", flag.ContinueOnError)
	dir := fs.String("dir", "", "identity papkasi")
	allowFile := fs.String("allow", "", "allowlist fayli (ixtiyoriy)")
	if fs.Parse(args) != nil || *dir == "" {
		return usage()
	}
	var allow [][]byte
	if *allowFile != "" {
		a, err := identity.LoadAllowlist(*allowFile)
		if err != nil {
			return fail(err)
		}
		allow = a
	}
	matches, _ := filepath.Glob(filepath.Join(*dir, "*.key"))
	sort.Strings(matches)
	if len(matches) == 0 {
		fmt.Println("identity topilmadi:", *dir)
		return 0
	}
	now := time.Now()
	fmt.Printf("%-18s %-20s %-10s %-10s %s\n", "IDENTITY", "BARMOQ IZI", "ALLOWLIST", "MUDDAT", "HOLAT")
	for _, m := range matches {
		id, err := identity.Load(m)
		if err != nil {
			fmt.Printf("%-18s XATO: %v\n", filepath.Base(m), err)
			continue
		}
		listState := "-"
		if *allowFile != "" {
			listState = "yo'q"
			if identity.Allowed(allow, id.Pub) {
				listState = "bor"
			}
		}
		muddat, holat := "-", "-"
		metaPath := strings.TrimSuffix(m, ".key") + ".meta.json"
		if meta, err := identity.LoadMeta(metaPath); err == nil {
			muddat = fmt.Sprintf("%d kun", int(meta.NotAfter.Sub(now).Hours()/24))
			holat = meta.State(now, 14)
		}
		fmt.Printf("%-18s %-20s %-10s %-10s %s\n", filepath.Base(m), identity.Fingerprint(id.Pub), listState, muddat, holat)
	}
	return 0
}

func cmdGatewayServe(args []string) int {
	fs := flag.NewFlagSet("gateway serve", flag.ContinueOnError)
	listen := fs.String("listen", "", "tinglash manzili")
	upstream := fs.String("upstream", "", "monolit manzili")
	idp := fs.String("identity", "", "server identity (.key)")
	require := fs.Bool("require-client-auth", false, "klient ML-DSA sertifikati talab qilinadi")
	allowFile := fs.String("allow", "", "allowlist fayli")
	metricsAddr := fs.String("metrics", "", "Prometheus /metrics manzili (masalan 127.0.0.1:9100)")
	if fs.Parse(args) != nil || *listen == "" || *upstream == "" || *idp == "" {
		return usage()
	}
	id, err := identity.Load(*idp)
	if err != nil {
		return fail(err)
	}
	var allow [][]byte
	if *allowFile != "" {
		if allow, err = identity.LoadAllowlist(*allowFile); err != nil {
			return fail(err)
		}
	}
	cfg, err := gateway.ServerConfig(id, *require)
	if err != nil {
		return fail(err)
	}
	m := &gateway.Metrics{}
	if *metricsAddr != "" {
		mux := http.NewServeMux()
		mux.Handle("/metrics", m.Handler())
		go func() {
			if err := http.ListenAndServe(*metricsAddr, mux); err != nil {
				logf("metrics: %v", err)
			}
		}()
		logf("metrics: http://%s/metrics", *metricsAddr)
	}
	ln, err := net.Listen("tcp", *listen)
	if err != nil {
		return fail(err)
	}
	logf("gateway serve %s → upstream %s (server %s, standart PQ-TLS)", *listen, *upstream, identity.Fingerprint(id.Pub))
	return fail(gateway.Serve(ln, cfg, allow, *upstream, logf, m))
}

func cmdGatewayConnect(args []string) int {
	fs := flag.NewFlagSet("gateway connect", flag.ContinueOnError)
	listen := fs.String("listen", "", "mahalliy tinglash manzili")
	peer := fs.String("peer", "", "peer gateway manzili")
	spk := fs.String("server-pub", "", "server ochiq kaliti: fayl yoki hex")
	idp := fs.String("identity", "", "klient identity (ixtiyoriy, mutual TLS)")
	if fs.Parse(args) != nil || *listen == "" || *peer == "" || *spk == "" {
		return usage()
	}
	var pin []byte
	if _, err := os.Stat(*spk); err == nil {
		p, err := identity.LoadPublic(*spk)
		if err != nil {
			return fail(err)
		}
		pin = p
	} else {
		raw, err := hex.DecodeString(*spk)
		if err != nil {
			return fail(fmt.Errorf("server-pub: fayl ham, hex ham emas"))
		}
		pin = raw
	}
	var self *identity.Identity
	if *idp != "" {
		id, err := identity.Load(*idp)
		if err != nil {
			return fail(err)
		}
		self = id
	}
	cfg, err := gateway.ClientConfig(self, pin)
	if err != nil {
		return fail(err)
	}
	ln, err := net.Listen("tcp", *listen)
	if err != nil {
		return fail(err)
	}
	logf("gateway connect %s → peer %s (server %s)", *listen, *peer, identity.Fingerprint(pin))
	return fail(gateway.Connect(ln, *peer, cfg, logf))
}
