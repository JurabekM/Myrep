package gateway

import (
	"fmt"
	"io"
	"net/http"
	"sync/atomic"
	"time"
)

// Metrics — standart rejim (gateway) hisoblagichlari. Prometheus matn formatida chiqadi.
type Metrics struct {
	ConnectionsTotal  atomic.Int64
	HandshakeFailures atomic.Int64
	ActiveConnections atomic.Int64
	BytesUpstream     atomic.Int64 // klient → monolit
	BytesDownstream   atomic.Int64 // monolit → klient
	handshakeNanos    atomic.Int64
	handshakeCount    atomic.Int64
}

// ObserveHandshake — bitta muvaffaqiyatli handshake davomiyligini qayd etadi.
func (m *Metrics) ObserveHandshake(d time.Duration) {
	m.handshakeNanos.Add(d.Nanoseconds())
	m.handshakeCount.Add(1)
}

// Handler — /metrics endpoint.
func (m *Metrics) Handler() http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.Header().Set("Content-Type", "text/plain; version=0.0.4")
		fmt.Fprintf(w, "# HELP aqgw_connections_total Qabul qilingan ulanishlar\n")
		fmt.Fprintf(w, "# TYPE aqgw_connections_total counter\n")
		fmt.Fprintf(w, "aqgw_connections_total %d\n", m.ConnectionsTotal.Load())
		fmt.Fprintf(w, "# HELP aqgw_handshake_failures_total Muvaffaqiyatsiz handshake/allowlist\n")
		fmt.Fprintf(w, "# TYPE aqgw_handshake_failures_total counter\n")
		fmt.Fprintf(w, "aqgw_handshake_failures_total %d\n", m.HandshakeFailures.Load())
		fmt.Fprintf(w, "# HELP aqgw_active_connections Faol tunellar\n")
		fmt.Fprintf(w, "# TYPE aqgw_active_connections gauge\n")
		fmt.Fprintf(w, "aqgw_active_connections %d\n", m.ActiveConnections.Load())
		fmt.Fprintf(w, "# HELP aqgw_bytes_total Uzatilgan baytlar\n")
		fmt.Fprintf(w, "# TYPE aqgw_bytes_total counter\n")
		fmt.Fprintf(w, "aqgw_bytes_total{direction=\"upstream\"} %d\n", m.BytesUpstream.Load())
		fmt.Fprintf(w, "aqgw_bytes_total{direction=\"downstream\"} %d\n", m.BytesDownstream.Load())
		fmt.Fprintf(w, "# HELP aqgw_handshake_seconds Handshake davomiyligi\n")
		fmt.Fprintf(w, "# TYPE aqgw_handshake_seconds summary\n")
		fmt.Fprintf(w, "aqgw_handshake_seconds_sum %g\n", float64(m.handshakeNanos.Load())/1e9)
		fmt.Fprintf(w, "aqgw_handshake_seconds_count %d\n", m.handshakeCount.Load())
	})
}

// countWriter — yozilgan baytlarni hisoblaydi.
type countWriter struct {
	w io.Writer
	n *atomic.Int64
}

func (c countWriter) Write(p []byte) (int, error) {
	n, err := c.w.Write(p)
	c.n.Add(int64(n))
	return n, err
}
