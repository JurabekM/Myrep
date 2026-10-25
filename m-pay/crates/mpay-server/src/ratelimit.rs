//! So'rovlarni cheklash (tahdid modeli D2): kalit bo'yicha token bucket va PQ Link handshake'lari
//! uchun global parallellik chegarasi.
//!
//! * IP bo'yicha — `/v1/pqlink/hello|finish`. Mobil operatorlar CGNAT ortida ko'p foydalanuvchini
//!   bitta IP'ga yig'adi, shuning uchun chegara yumshoq; asosiy CPU himoyasi — global semafor.
//! * API kaliti bo'yicha — operator va terminal endpointlari.
//! * Qurilma bo'yicha — muhrlangan (sealed) endpointlar.

use std::collections::HashMap;
use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use serde::{Deserialize, Serialize};
use tokio::sync::{OwnedSemaphorePermit, Semaphore};

/// `[rate_limit]` konfiguratsiyasi.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(deny_unknown_fields, default)]
pub struct RateLimitConfig {
    /// `false` — barcha cheklovlar o'chiq (faqat yuk sinovi uchun).
    pub enabled: bool,
    /// Bir vaqtda hisoblanadigan PQ Link handshake'lari; 0 — CPU soni × 2.
    pub max_concurrent_handshakes: usize,
    /// IP bo'yicha handshake so'rovlari (hello + finish), daqiqasiga.
    pub ip_handshake_per_minute: u32,
    pub ip_handshake_burst: u32,
    /// API kaliti bo'yicha so'rovlar, sekundiga.
    pub api_key_per_second: u32,
    pub api_key_burst: u32,
    /// Qurilma bo'yicha muhrlangan so'rovlar, daqiqasiga.
    pub device_per_minute: u32,
    pub device_burst: u32,
}

impl Default for RateLimitConfig {
    fn default() -> Self {
        Self {
            enabled: true,
            max_concurrent_handshakes: 0,
            ip_handshake_per_minute: 300,
            ip_handshake_burst: 60,
            api_key_per_second: 500,
            api_key_burst: 1000,
            device_per_minute: 60,
            device_burst: 30,
        }
    }
}

/// Rad etish: qancha kutish kerak.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Limited {
    pub retry_after: Duration,
}

#[derive(Debug, Clone, Copy)]
struct Bucket {
    tokens: f64,
    last: Instant,
}

/// Kalit bo'yicha token bucket. Bo'sh (to'lgan) chelaklar xarita katta bo'lganda tozalanadi.
#[derive(Debug)]
pub struct KeyedLimiter {
    rate_per_sec: f64,
    burst: f64,
    map: Mutex<HashMap<String, Bucket>>,
}

/// Xaritadagi kalitlar soni shundan oshsa — to'lgan chelaklar o'chiriladi.
const PRUNE_AT: usize = 50_000;

impl KeyedLimiter {
    pub fn new(rate_per_sec: f64, burst: u32) -> Self {
        Self {
            rate_per_sec: rate_per_sec.max(f64::MIN_POSITIVE),
            burst: f64::from(burst.max(1)),
            map: Mutex::new(HashMap::new()),
        }
    }

    pub fn per_minute(n: u32, burst: u32) -> Self {
        Self::new(f64::from(n) / 60.0, burst)
    }

    /// Bitta so'rov uchun ruxsat.
    pub fn check(&self, key: &str) -> Result<(), Limited> {
        self.check_at(key, Instant::now())
    }

    /// Vaqt tashqaridan beriladi (testlar).
    pub fn check_at(&self, key: &str, now: Instant) -> Result<(), Limited> {
        let mut map = self.map.lock().unwrap_or_else(|e| e.into_inner());
        if map.len() >= PRUNE_AT && !map.contains_key(key) {
            let (rate, burst) = (self.rate_per_sec, self.burst);
            map.retain(|_, b| {
                b.tokens + now.saturating_duration_since(b.last).as_secs_f64() * rate < burst
            });
            // Hammasi faol bo'lsa ham (ko'p manzil, CGNAT) xarita cheksiz o'smasin va har yangi kalit
            // to'liq skanerlashni chaqirmasin: eng eskilari yarmigacha chiqariladi — keyingi skanerlash
            // kamida PRUNE_AT/2 yangi kalitdan keyin (amortizatsiyalangan O(1)). Chiqarilgan kalit
            // keyingi so'rovda to'la chelak oladi — xotira/CPU himoyasi uchun ongli yumshoqlik.
            if map.len() > PRUNE_AT / 2 {
                let mut ages: Vec<(Instant, String)> =
                    map.iter().map(|(k, b)| (b.last, k.clone())).collect();
                let cut = ages.len() - PRUNE_AT / 2;
                ages.select_nth_unstable_by_key(cut, |(last, _)| *last);
                for (_, k) in &ages[..cut] {
                    map.remove(k);
                }
            }
        }
        let b = map.entry(key.to_owned()).or_insert(Bucket {
            tokens: self.burst,
            last: now,
        });
        let elapsed = now.saturating_duration_since(b.last).as_secs_f64();
        b.tokens = (b.tokens + elapsed * self.rate_per_sec).min(self.burst);
        b.last = now;
        if b.tokens >= 1.0 {
            b.tokens -= 1.0;
            Ok(())
        } else {
            let wait = (1.0 - b.tokens) / self.rate_per_sec;
            Err(Limited {
                retry_after: Duration::from_secs_f64(wait.clamp(0.001, 3600.0)),
            })
        }
    }

    /// Kuzatilayotgan kalitlar soni.
    pub fn tracked(&self) -> usize {
        self.map.lock().map(|m| m.len()).unwrap_or(0)
    }
}

/// Server bo'yicha barcha cheklovchilar.
#[derive(Debug)]
pub struct RateLimits {
    enabled: bool,
    handshakes: Arc<Semaphore>,
    ip: KeyedLimiter,
    api_key: KeyedLimiter,
    device: KeyedLimiter,
}

impl RateLimits {
    pub fn new(cfg: &RateLimitConfig) -> Self {
        let n = if cfg.max_concurrent_handshakes == 0 {
            std::thread::available_parallelism().map_or(4, |n| n.get() * 2)
        } else {
            cfg.max_concurrent_handshakes
        };
        Self {
            enabled: cfg.enabled,
            handshakes: Arc::new(Semaphore::new(n)),
            ip: KeyedLimiter::per_minute(cfg.ip_handshake_per_minute, cfg.ip_handshake_burst),
            api_key: KeyedLimiter::new(f64::from(cfg.api_key_per_second), cfg.api_key_burst),
            device: KeyedLimiter::per_minute(cfg.device_per_minute, cfg.device_burst),
        }
    }

    /// Cheklovsiz (testlar va `enabled = false`).
    pub fn disabled() -> Self {
        Self::new(&RateLimitConfig {
            enabled: false,
            ..RateLimitConfig::default()
        })
    }

    pub fn ip(&self, ip: &str) -> Result<(), Limited> {
        if self.enabled {
            self.ip.check(ip)
        } else {
            Ok(())
        }
    }

    pub fn api_key(&self, id: &str) -> Result<(), Limited> {
        if self.enabled {
            self.api_key.check(id)
        } else {
            Ok(())
        }
    }

    pub fn device(&self, id: &str) -> Result<(), Limited> {
        if self.enabled {
            self.device.check(id)
        } else {
            Ok(())
        }
    }

    /// Handshake hisoblash uchun ruxsat; band bo'lsa darhol rad (navbat yo'q — kutish ham resurs).
    pub fn handshake_permit(&self) -> Result<Option<OwnedSemaphorePermit>, Limited> {
        if !self.enabled {
            return Ok(None);
        }
        self.handshakes
            .clone()
            .try_acquire_owned()
            .map(Some)
            .map_err(|_| Limited {
                retry_after: Duration::from_secs(1),
            })
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn bucket_allows_burst_then_refills() {
        let l = KeyedLimiter::new(2.0, 3);
        let t0 = Instant::now();
        for _ in 0..3 {
            assert!(l.check_at("a", t0).is_ok());
        }
        let e = l.check_at("a", t0).unwrap_err();
        assert!(e.retry_after <= Duration::from_millis(500), "{e:?}");
        // Boshqa kalit ta'sirlanmaydi.
        assert!(l.check_at("b", t0).is_ok());
        // 0,5 s da bitta token tiklanadi.
        assert!(l.check_at("a", t0 + Duration::from_millis(500)).is_ok());
        assert!(l.check_at("a", t0 + Duration::from_millis(500)).is_err());
        // Uzoq kutishda burst'dan oshmaydi.
        let later = t0 + Duration::from_secs(60);
        for _ in 0..3 {
            assert!(l.check_at("a", later).is_ok());
        }
        assert!(l.check_at("a", later).is_err());
    }

    #[test]
    fn idle_buckets_pruned() {
        let l = KeyedLimiter::new(1000.0, 1);
        let t0 = Instant::now();
        for i in 0..PRUNE_AT {
            let _ = l.check_at(&i.to_string(), t0);
        }
        assert_eq!(l.tracked(), PRUNE_AT);
        // 1 s keyin hammasi to'lgan — yangi kalit qo'shilganda tozalanadi.
        let _ = l.check_at("new", t0 + Duration::from_secs(1));
        assert_eq!(l.tracked(), 1);
    }

    #[test]
    fn active_keys_bounded_by_evicting_oldest() {
        // Sekin to'ladigan chelak: hamma kalit faol (to'lmagan) qoladi — retain hech narsani o'chirmaydi.
        let l = KeyedLimiter::new(0.001, 1);
        let t0 = Instant::now();
        for i in 0..PRUNE_AT {
            let _ = l.check_at(&i.to_string(), t0 + Duration::from_micros(i as u64));
        }
        let later = t0 + Duration::from_secs(1);
        let _ = l.check_at("new", later);
        // Eskilarning yarmi chiqarildi, yangi kalit qo'shildi; eng yangi faol kalit saqlangan.
        assert_eq!(l.tracked(), PRUNE_AT / 2 + 1);
        assert!(l.check_at(&(PRUNE_AT - 1).to_string(), later).is_err());
    }

    #[test]
    fn handshake_semaphore_and_disable() {
        let r = RateLimits::new(&RateLimitConfig {
            max_concurrent_handshakes: 1,
            ..RateLimitConfig::default()
        });
        let p = r.handshake_permit().unwrap();
        assert!(p.is_some());
        assert!(r.handshake_permit().is_err());
        drop(p);
        assert!(r.handshake_permit().is_ok());

        let off = RateLimits::disabled();
        for _ in 0..10_000 {
            assert!(off.ip("1.2.3.4").is_ok());
        }
        assert!(off.handshake_permit().unwrap().is_none());
    }
}
