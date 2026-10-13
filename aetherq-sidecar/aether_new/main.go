// Aether_new — AETHER-Q sidecar orqasida ishlaydigan monolit dastur (yozuvlar REST API'si).
//
// Ishga tushirish:
//
//	aether_new.exe -listen 127.0.0.1:8080 -data aether_new_data.json
package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"time"
)

func main() {
	listen := flag.String("listen", "127.0.0.1:8080", "tinglash manzili (sidecar shu portga ulanadi)")
	dataFile := flag.String("data", "aether_new_data.json", "ma'lumot fayli (JSON)")
	flag.Parse()

	store, err := OpenStore(*dataFile)
	if err != nil {
		log.Fatalf("aether_new: ombor: %v", err)
	}
	srv := &http.Server{
		Addr:              *listen,
		Handler:           NewMux(store),
		ReadHeaderTimeout: 10 * time.Second,
	}
	go func() {
		quit := make(chan os.Signal, 1)
		signal.Notify(quit, os.Interrupt)
		<-quit
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		_ = srv.Shutdown(ctx)
	}()
	log.Printf("aether_new %s: http://%s (ma'lumot: %s)", version, *listen, *dataFile)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("aether_new: %v", err)
	}
}
