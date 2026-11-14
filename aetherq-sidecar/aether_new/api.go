package main

import (
	"encoding/json"
	"errors"
	"net/http"
	"strconv"
	"time"
)

const version = "1.0.0"

// NewMux — HTTP API marshrutlari.
//
//	GET    /healthz
//	GET    /api/v1/records
//	POST   /api/v1/records        {"title": "...", "body": "..."}
//	GET    /api/v1/records/{id}
//	DELETE /api/v1/records/{id}
func NewMux(s *Store) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, map[string]string{"status": "ok", "version": version})
	})
	mux.HandleFunc("GET /api/v1/records", func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, s.List())
	})
	mux.HandleFunc("POST /api/v1/records", func(w http.ResponseWriter, r *http.Request) {
		r.Body = http.MaxBytesReader(w, r.Body, 64*1024)
		var in struct {
			Title string `json:"title"`
			Body  string `json:"body"`
		}
		if err := json.NewDecoder(r.Body).Decode(&in); err != nil {
			writeError(w, http.StatusBadRequest, "JSON noto'g'ri")
			return
		}
		rec, err := s.Create(in.Title, in.Body, time.Now())
		if errors.Is(err, ErrInvalid) {
			writeError(w, http.StatusUnprocessableEntity, "title majburiy (≤200), body (≤10000)")
			return
		}
		if err != nil {
			writeError(w, http.StatusInternalServerError, "saqlashda xato")
			return
		}
		writeJSON(w, http.StatusCreated, rec)
	})
	mux.HandleFunc("GET /api/v1/records/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(r.PathValue("id"))
		if !ok {
			writeError(w, http.StatusBadRequest, "ID noto'g'ri")
			return
		}
		rec, found := s.Get(id)
		if !found {
			writeError(w, http.StatusNotFound, "topilmadi")
			return
		}
		writeJSON(w, http.StatusOK, rec)
	})
	mux.HandleFunc("DELETE /api/v1/records/{id}", func(w http.ResponseWriter, r *http.Request) {
		id, ok := parseID(r.PathValue("id"))
		if !ok {
			writeError(w, http.StatusBadRequest, "ID noto'g'ri")
			return
		}
		found, err := s.Delete(id)
		if err != nil {
			writeError(w, http.StatusInternalServerError, "saqlashda xato")
			return
		}
		if !found {
			writeError(w, http.StatusNotFound, "topilmadi")
			return
		}
		w.WriteHeader(http.StatusNoContent)
	})
	return mux
}

func parseID(s string) (int64, bool) {
	id, err := strconv.ParseInt(s, 10, 64)
	return id, err == nil && id > 0
}

func writeJSON(w http.ResponseWriter, code int, v any) {
	w.Header().Set("Content-Type", "application/json; charset=utf-8")
	w.WriteHeader(code)
	_ = json.NewEncoder(w).Encode(v)
}

func writeError(w http.ResponseWriter, code int, msg string) {
	writeJSON(w, code, map[string]string{"error": msg})
}
