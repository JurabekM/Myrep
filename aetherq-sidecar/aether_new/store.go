package main

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"sort"
	"strings"
	"sync"
	"time"
)

// Record — monolit ma'lumot yozuvi (yozuvlar ro'yxati).
type Record struct {
	ID        int64     `json:"id"`
	Title     string    `json:"title"`
	Body      string    `json:"body"`
	CreatedAt time.Time `json:"created_at"`
}

// Chegaralar (validatsiya).
const (
	maxTitle = 200
	maxBody  = 10000
)

var ErrInvalid = errors.New("noto'g'ri ma'lumot")

// Store — JSON fayl bilan saqlanadigan, xotirada tutiladigan ombor (mutex bilan).
type Store struct {
	mu      sync.Mutex
	path    string
	nextID  int64
	records map[int64]Record
}

type storeFile struct {
	NextID  int64    `json:"next_id"`
	Records []Record `json:"records"`
}

// OpenStore — faylni yuklaydi (yo'q bo'lsa bo'sh ombor).
func OpenStore(path string) (*Store, error) {
	s := &Store{path: path, nextID: 1, records: map[int64]Record{}}
	data, err := os.ReadFile(path)
	if os.IsNotExist(err) {
		return s, nil
	}
	if err != nil {
		return nil, err
	}
	var f storeFile
	if err := json.Unmarshal(data, &f); err != nil {
		return nil, fmt.Errorf("ma'lumot fayli buzilgan: %w", err)
	}
	for _, r := range f.Records {
		s.records[r.ID] = r
	}
	s.nextID = f.NextID
	if s.nextID < 1 {
		s.nextID = 1
	}
	return s, nil
}

// List — barcha yozuvlar, ID bo'yicha.
func (s *Store) List() []Record {
	s.mu.Lock()
	defer s.mu.Unlock()
	out := make([]Record, 0, len(s.records))
	for _, r := range s.records {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].ID < out[j].ID })
	return out
}

// Get — ID bo'yicha yozuv.
func (s *Store) Get(id int64) (Record, bool) {
	s.mu.Lock()
	defer s.mu.Unlock()
	r, ok := s.records[id]
	return r, ok
}

// Create — yangi yozuv (validatsiya bilan), diskka saqlaydi.
func (s *Store) Create(title, body string, now time.Time) (Record, error) {
	title = strings.TrimSpace(title)
	if title == "" || len(title) > maxTitle || len(body) > maxBody {
		return Record{}, ErrInvalid
	}
	s.mu.Lock()
	defer s.mu.Unlock()
	r := Record{ID: s.nextID, Title: title, Body: body, CreatedAt: now.UTC()}
	s.nextID++
	s.records[r.ID] = r
	if err := s.saveLocked(); err != nil {
		delete(s.records, r.ID)
		s.nextID--
		return Record{}, err
	}
	return r, nil
}

// Delete — yozuvni o'chiradi. Topilmasa false.
func (s *Store) Delete(id int64) (bool, error) {
	s.mu.Lock()
	defer s.mu.Unlock()
	if _, ok := s.records[id]; !ok {
		return false, nil
	}
	delete(s.records, id)
	return true, s.saveLocked()
}

// saveLocked — atomik yozish (vaqtinchalik fayl + rename). Mutex ushlangan bo'lishi kerak.
func (s *Store) saveLocked() error {
	if s.path == "" {
		return nil
	}
	f := storeFile{NextID: s.nextID, Records: make([]Record, 0, len(s.records))}
	for _, r := range s.records {
		f.Records = append(f.Records, r)
	}
	sort.Slice(f.Records, func(i, j int) bool { return f.Records[i].ID < f.Records[j].ID })
	data, err := json.MarshalIndent(f, "", "  ")
	if err != nil {
		return err
	}
	tmp := s.path + ".tmp"
	if err := os.WriteFile(tmp, data, 0o600); err != nil {
		return err
	}
	return os.Rename(tmp, s.path)
}
