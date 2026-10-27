//! Real-time belgilar ombori: sirpanuvchi oynalar (karta, qurilma, merchant, global P2P),
//! karta profili (summa z-skori, soat gistogrammasi), qurilma–karta grafi.
//!
//! **Bir xil kod** onlayn skoringda va `shield-replay featurize` da ishlatiladi — o'qitish va
//! ishlab chiqarish belgilari farq qilmaydi (train/serve parity). Belgilar har doim **joriy hodisadan
//! oldingi** holatdan hisoblanadi, keyin hodisa omborga qo'shiladi.

use std::collections::{HashMap, HashSet, VecDeque};

use crate::graph::DeviceCardGraph;

/// Tranzaksiya belgilari nomlari (ONNX model kirishi shu tartibda).
pub const TXN_FEATURES: [&str; 27] = [
    "amount_log",
    "card_txn_count_1m",
    "card_txn_count_10m",
    "card_txn_count_1h",
    "card_txn_count_24h",
    "card_amount_sum_1h_log",
    "device_txn_count_10m",
    "device_txn_count_1h",
    "merchant_txn_count_1m",
    "merchant_distinct_cards_10m",
    "card_distinct_merchants_1h",
    "card_small_txn_count_10m",
    "amount_zscore",
    "card_history_count",
    "hour_of_day",
    "hour_rarity",
    "foreign_country",
    "device_card_count",
    "card_device_count",
    "component_size",
    "new_device_for_card",
    "secs_since_card_last_txn_log",
    "device_age_secs_log",
    "cdcvm_performed",
    "is_p2p",
    "global_p2p_count_10m",
    "amount_to_card_mean_ratio",
];

/// ID&V (provisioning) belgilari.
pub const IDV_FEATURES: [&str; 14] = [
    "device_card_count",
    "card_device_count",
    "component_size",
    "device_prov_count_24h",
    "card_prov_count_24h",
    "attestation_level",
    "device_age_secs_log",
    "existing_tokens_for_pan",
    "existing_tokens_for_device",
    // Yaxlitlik (P2.6, ADR-0021): `integrity_present` = 0 bo'lsa qolganlari 0 va qoidalar ishlamaydi.
    "integrity_present",
    "integrity_app",
    "integrity_device",
    "integrity_licensed",
    "integrity_env_risk",
];

/// "Kichik" summa chegarasi (karta testlash): 1 000,00 UZS.
pub const SMALL_AMOUNT_MINOR: u64 = 100_000;
const DAY: i64 = 86_400;

/// Tranzaksiya hodisasi (onlayn `RiskRequest` yoki replay qatoridan).
#[derive(Debug, Clone)]
pub struct TxnEvent {
    pub at: i64,
    pub device: [u8; 32],
    pub card: [u8; 32],
    pub merchant: String,
    pub country: u16,
    pub amount_minor: u64,
    pub cdcvm: bool,
    pub is_p2p: bool,
}

/// Provisioning hodisasi.
#[derive(Debug, Clone)]
pub struct ProvisionEvent {
    pub at: i64,
    pub device: [u8; 32],
    pub card: [u8; 32],
    pub attestation_level: u8,
    pub existing_tokens_for_pan: u32,
    pub existing_tokens_for_device: u32,
    pub integrity: Option<mpay_common::ports::IntegritySignals>,
}

#[derive(Debug, Default)]
struct Window {
    ev: VecDeque<(i64, u64)>,
}

impl Window {
    fn prune(&mut self, now: i64, keep: i64) {
        while self.ev.front().is_some_and(|(t, _)| *t <= now - keep) {
            self.ev.pop_front();
        }
    }
    fn count_since(&self, now: i64, secs: i64) -> u32 {
        self.ev
            .iter()
            .rev()
            .take_while(|(t, _)| *t > now - secs)
            .count() as u32
    }
    fn sum_since(&self, now: i64, secs: i64) -> u64 {
        self.ev
            .iter()
            .rev()
            .take_while(|(t, _)| *t > now - secs)
            .map(|(_, a)| *a)
            .sum()
    }
    fn count_small_since(&self, now: i64, secs: i64) -> u32 {
        self.ev
            .iter()
            .rev()
            .take_while(|(t, _)| *t > now - secs)
            .filter(|(_, a)| *a < SMALL_AMOUNT_MINOR)
            .count() as u32
    }
}

#[derive(Debug, Default)]
struct CardState {
    win: Window,
    merchants: VecDeque<(i64, u64)>, // (ts, merchant xeshi)
    hours: [u32; 24],
    n: u64,
    mean: f64,
    m2: f64,
    last_ts: Option<i64>,
    prov: VecDeque<i64>,
}

#[derive(Debug, Default)]
struct DeviceState {
    win: Window,
    first_seen: Option<i64>,
    prov: VecDeque<i64>,
}

#[derive(Debug, Default)]
struct MerchantState {
    ev: VecDeque<(i64, [u8; 32])>,
}

fn h64(s: &str) -> u64 {
    // FNV-1a: faqat xotiradagi kalit uchun (kriptografik emas).
    s.bytes().fold(0xcbf2_9ce4_8422_2325u64, |h, b| {
        (h ^ u64::from(b)).wrapping_mul(0x100_0000_01b3)
    })
}

fn log1p(x: f64) -> f32 {
    (x.max(0.0)).ln_1p() as f32
}

/// Belgilar ombori.
#[derive(Debug, Default)]
pub struct FeatureStore {
    cards: HashMap<[u8; 32], CardState>,
    devices: HashMap<[u8; 32], DeviceState>,
    merchants: HashMap<u64, MerchantState>,
    p2p: VecDeque<i64>,
    graph: DeviceCardGraph,
    events: u64,
}

impl FeatureStore {
    pub fn new() -> Self {
        Self::default()
    }

    /// Tranzaksiya belgilarini hisoblaydi va hodisani omborga qo'shadi.
    pub fn txn(&mut self, e: &TxnEvent) -> [f32; TXN_FEATURES.len()] {
        let now = e.at;
        let amount_uzs = e.amount_minor as f64 / 100.0;
        let device = self.graph.canonical(e.device);
        let edge = self.graph.touch(device, e.card, now);
        let mkey = h64(&e.merchant);

        let card = self.cards.entry(e.card).or_default();
        card.win.prune(now, DAY);
        while card
            .merchants
            .front()
            .is_some_and(|(t, _)| *t <= now - 3600)
        {
            card.merchants.pop_front();
        }
        let dev = self.devices.entry(device).or_default();
        dev.win.prune(now, DAY);
        let dev_first = *dev.first_seen.get_or_insert(now);
        let merch = self.merchants.entry(mkey).or_default();
        while merch.ev.front().is_some_and(|(t, _)| *t <= now - 600) {
            merch.ev.pop_front();
        }
        while self.p2p.front().is_some_and(|t| *t <= now - 600) {
            self.p2p.pop_front();
        }

        let la = (amount_uzs.max(0.01)).ln();
        let std = if card.n > 1 {
            (card.m2 / (card.n - 1) as f64).sqrt()
        } else {
            0.0
        };
        let zscore = if card.n >= 3 && std > 1e-6 {
            ((la - card.mean) / std).clamp(-10.0, 10.0)
        } else {
            0.0
        };
        let mean_amount = if card.n > 0 {
            card.mean.exp()
        } else {
            amount_uzs
        };
        let hour = ((now.rem_euclid(DAY)) / 3600) as usize;
        let hour_rarity = if card.n >= 5 {
            1.0 - card.hours[hour] as f64 / card.n as f64
        } else {
            0.5
        };
        let distinct_merchants_1h = {
            let mut s: HashSet<u64> = card.merchants.iter().map(|(_, m)| *m).collect();
            s.insert(mkey);
            s.len() as u32
        };
        let merchant_cards_10m = {
            let mut s: HashSet<[u8; 32]> = merch.ev.iter().map(|(_, c)| *c).collect();
            s.insert(e.card);
            s.len() as u32
        };
        let merchant_1m = merch
            .ev
            .iter()
            .rev()
            .take_while(|(t, _)| *t > now - 60)
            .count() as u32;

        let f = [
            log1p(amount_uzs),
            card.win.count_since(now, 60) as f32,
            card.win.count_since(now, 600) as f32,
            card.win.count_since(now, 3600) as f32,
            card.win.count_since(now, DAY) as f32,
            log1p(card.win.sum_since(now, 3600) as f64 / 100.0),
            dev.win.count_since(now, 600) as f32,
            dev.win.count_since(now, 3600) as f32,
            merchant_1m as f32,
            merchant_cards_10m as f32,
            distinct_merchants_1h as f32,
            card.win.count_small_since(now, 600) as f32,
            zscore as f32,
            card.n.min(10_000) as f32,
            hour as f32,
            hour_rarity as f32,
            f32::from(u8::from(e.country != 860)),
            edge.device_degree as f32,
            edge.card_degree as f32,
            edge.component_size as f32,
            // Kartaga oxirgi 24 soatda ikkinchi (yoki keyingi) qurilma bog'langan — ATO belgisi.
            f32::from(u8::from(
                now - edge.first_seen < DAY && edge.card_degree > 1,
            )),
            card.last_ts
                .map(|t| log1p((now - t) as f64))
                .unwrap_or(16.0),
            log1p((now - dev_first) as f64),
            f32::from(u8::from(e.cdcvm)),
            f32::from(u8::from(e.is_p2p)),
            self.p2p.len() as f32,
            (amount_uzs / mean_amount.max(1.0)).min(1000.0) as f32,
        ];

        // Holatni yangilash.
        card.win.ev.push_back((now, e.amount_minor));
        card.merchants.push_back((now, mkey));
        card.hours[hour] += 1;
        card.n += 1;
        let d = la - card.mean;
        card.mean += d / card.n as f64;
        card.m2 += d * (la - card.mean);
        card.last_ts = Some(now);
        dev.win.ev.push_back((now, e.amount_minor));
        merch.ev.push_back((now, e.card));
        if e.is_p2p {
            self.p2p.push_back(now);
        }
        self.maintenance(now);
        f
    }

    /// Provisioning belgilarini hisoblaydi va qurilma–karta qirrasini qo'shadi.
    pub fn provision(&mut self, e: &ProvisionEvent) -> [f32; IDV_FEATURES.len()] {
        let now = e.at;
        let device = self.graph.canonical(e.device);
        let edge = self.graph.touch(device, e.card, now);
        let dev = self.devices.entry(device).or_default();
        let dev_first = *dev.first_seen.get_or_insert(now);
        while dev.prov.front().is_some_and(|t| *t <= now - DAY) {
            dev.prov.pop_front();
        }
        let dev_prov = dev.prov.len() as f32;
        dev.prov.push_back(now);
        let card = self.cards.entry(e.card).or_default();
        while card.prov.front().is_some_and(|t| *t <= now - DAY) {
            card.prov.pop_front();
        }
        let card_prov = card.prov.len() as f32;
        card.prov.push_back(now);
        self.maintenance(now);
        [
            edge.device_degree as f32,
            edge.card_degree as f32,
            edge.component_size as f32,
            dev_prov,
            card_prov,
            f32::from(e.attestation_level),
            log1p((now - dev_first) as f64),
            e.existing_tokens_for_pan as f32,
            e.existing_tokens_for_device as f32,
            f32::from(u8::from(e.integrity.is_some())),
            f32::from(e.integrity.map_or(0, |i| i.app)),
            f32::from(e.integrity.map_or(0, |i| i.device)),
            f32::from(e.integrity.map_or(0, |i| i.licensed)),
            f32::from(e.integrity.map_or(0, |i| i.env_risk)),
        ]
    }

    /// Qurilma kaliti almashtirildi: `new` — `old` ning davomi (graf, qurilma oynalari va yoshi
    /// umumiy). `false` — `new` allaqachon o'z tarixiga ega (bog'lanmadi).
    pub fn device_rekeyed(&mut self, old: [u8; 32], new: [u8; 32]) -> bool {
        if self.devices.contains_key(&new) {
            return false;
        }
        self.graph.link_device(old, new)
    }

    /// Har 10 000 hodisada 7 kundan beri harakatsiz kalitlarni (graf'dan tashqari) tozalaydi.
    fn maintenance(&mut self, now: i64) {
        self.events += 1;
        if !self.events.is_multiple_of(10_000) {
            return;
        }
        let idle = now - 7 * DAY;
        self.cards.retain(|_, c| {
            c.last_ts.is_none_or(|t| t > idle) || c.prov.back().is_some_and(|t| *t > idle)
        });
        self.devices.retain(|_, d| {
            d.win.ev.back().is_some_and(|(t, _)| *t > idle)
                || d.prov.back().is_some_and(|t| *t > idle)
        });
        self.merchants
            .retain(|_, m| m.ev.back().is_some_and(|(t, _)| *t > now - 600));
    }

    /// Snapshot (ADR-0026): to'liq holat — keyingi hodisalarda belgilar tiklangan va asl omborda bir xil.
    pub fn snapshot(&self) -> Vec<u8> {
        use crate::snapshot::W;
        fn pairs(w: &mut W, q: &VecDeque<(i64, u64)>) {
            w.len(q.len());
            for (t, v) in q {
                w.i64(*t);
                w.u64(*v);
            }
        }
        fn times(w: &mut W, q: &VecDeque<i64>) {
            w.len(q.len());
            for t in q {
                w.i64(*t);
            }
        }
        crate::snapshot::seal(|w| {
            w.u64(self.events);
            let mut cards: Vec<_> = self.cards.iter().collect();
            cards.sort_unstable_by_key(|(k, _)| **k);
            w.len(cards.len());
            for (k, c) in cards {
                w.a32(k);
                pairs(w, &c.win.ev);
                pairs(w, &c.merchants);
                for h in c.hours {
                    w.u32(h);
                }
                w.u64(c.n);
                w.f64(c.mean);
                w.f64(c.m2);
                w.opt_i64(c.last_ts);
                times(w, &c.prov);
            }
            let mut devices: Vec<_> = self.devices.iter().collect();
            devices.sort_unstable_by_key(|(k, _)| **k);
            w.len(devices.len());
            for (k, d) in devices {
                w.a32(k);
                pairs(w, &d.win.ev);
                w.opt_i64(d.first_seen);
                times(w, &d.prov);
            }
            let mut merchants: Vec<_> = self.merchants.iter().collect();
            merchants.sort_unstable_by_key(|(k, _)| **k);
            w.len(merchants.len());
            for (k, m) in merchants {
                w.u64(*k);
                w.len(m.ev.len());
                for (t, card) in &m.ev {
                    w.i64(*t);
                    w.a32(card);
                }
            }
            times(w, &self.p2p);
            self.graph.encode(w);
        })
    }

    /// Snapshot'dan tiklaydi (xesh, tuzilma va graf tekshiriladi).
    pub fn restore(data: &[u8]) -> Result<Self, crate::snapshot::SnapshotError> {
        use crate::snapshot::{SnapshotError::Format, R};
        fn pairs(r: &mut R<'_>) -> crate::snapshot::Result<VecDeque<(i64, u64)>> {
            let n = r.len(16)?;
            (0..n).map(|_| Ok((r.i64()?, r.u64()?))).collect()
        }
        fn times(r: &mut R<'_>) -> crate::snapshot::Result<VecDeque<i64>> {
            let n = r.len(8)?;
            (0..n).map(|_| r.i64()).collect()
        }
        crate::snapshot::open(data, |r| {
            let mut s = Self {
                events: r.u64()?,
                ..Self::default()
            };
            let n = r.len(32 + 8 + 8 + 24 * 4 + 8 + 8 + 8 + 1 + 8)?;
            for _ in 0..n {
                let k = r.a32()?;
                let win = Window { ev: pairs(r)? };
                let merchants = pairs(r)?;
                let mut hours = [0u32; 24];
                for h in &mut hours {
                    *h = r.u32()?;
                }
                let c = CardState {
                    win,
                    merchants,
                    hours,
                    n: r.u64()?,
                    mean: r.f64()?,
                    m2: r.f64()?,
                    last_ts: r.opt_i64()?,
                    prov: times(r)?,
                };
                if s.cards.insert(k, c).is_some() {
                    return Err(Format("takroriy karta"));
                }
            }
            let n = r.len(32 + 8 + 1 + 8)?;
            for _ in 0..n {
                let k = r.a32()?;
                let d = DeviceState {
                    win: Window { ev: pairs(r)? },
                    first_seen: r.opt_i64()?,
                    prov: times(r)?,
                };
                if s.devices.insert(k, d).is_some() {
                    return Err(Format("takroriy qurilma"));
                }
            }
            let n = r.len(8 + 8)?;
            for _ in 0..n {
                let k = r.u64()?;
                let m = r.len(40)?;
                let ev = (0..m)
                    .map(|_| Ok((r.i64()?, r.a32()?)))
                    .collect::<crate::snapshot::Result<VecDeque<_>>>()?;
                if s.merchants.insert(k, MerchantState { ev }).is_some() {
                    return Err(Format("takroriy savdo nuqtasi"));
                }
            }
            s.p2p = times(r)?;
            s.graph = DeviceCardGraph::decode(r)?;
            Ok(s)
        })
    }

    /// Diagnostika.
    pub fn stats(&self) -> (usize, usize, usize, usize) {
        (
            self.cards.len(),
            self.devices.len(),
            self.merchants.len(),
            self.graph.nodes(),
        )
    }
}

/// Belgi indeksini nom bo'yicha topadi.
pub fn txn_index(name: &str) -> Option<usize> {
    TXN_FEATURES.iter().position(|n| *n == name)
}

pub fn idv_index(name: &str) -> Option<usize> {
    IDV_FEATURES.iter().position(|n| *n == name)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn tx(at: i64, card: u8, dev: u8, merchant: &str, amount: u64) -> TxnEvent {
        TxnEvent {
            at,
            device: [dev; 32],
            card: [card; 32],
            merchant: merchant.into(),
            country: 860,
            amount_minor: amount,
            cdcvm: false,
            is_p2p: merchant.starts_with("P2P"),
        }
    }

    fn f(v: &[f32], name: &str) -> f32 {
        v[txn_index(name).unwrap()]
    }

    #[test]
    fn velocity_windows_exclude_current_and_expire() {
        let mut s = FeatureStore::new();
        let t0 = 1_800_000_000;
        for i in 0..5 {
            s.txn(&tx(t0 + i * 10, 1, 1, "SHOP", 50_000));
        }
        let v = s.txn(&tx(t0 + 50, 1, 1, "SHOP", 50_000));
        assert_eq!(f(&v, "card_txn_count_1m"), 5.0);
        assert_eq!(f(&v, "card_small_txn_count_10m"), 5.0);
        let v = s.txn(&tx(t0 + 50 + 3600 * 2, 1, 1, "SHOP", 50_000));
        assert_eq!(f(&v, "card_txn_count_1m"), 0.0);
        assert_eq!(f(&v, "card_txn_count_24h"), 6.0);
        let v = s.txn(&tx(t0 + 2 * DAY, 1, 1, "SHOP", 50_000));
        assert_eq!(f(&v, "card_txn_count_24h"), 0.0);
    }

    #[test]
    fn card_testing_and_graph_signals() {
        let mut s = FeatureStore::new();
        let t0 = 1_800_000_000;
        for c in 0..8u8 {
            s.txn(&tx(t0 + i64::from(c), 100 + c, 7, "SHOPX", 100));
        }
        let v = s.txn(&tx(t0 + 9, 120, 7, "SHOPX", 100));
        assert_eq!(f(&v, "merchant_distinct_cards_10m"), 9.0);
        assert_eq!(f(&v, "device_card_count"), 9.0);
        assert_eq!(f(&v, "component_size"), 10.0);
        assert_eq!(f(&v, "merchant_txn_count_1m"), 8.0);
    }

    #[test]
    fn zscore_after_history() {
        let mut s = FeatureStore::new();
        let t0 = 1_800_000_000;
        for i in 0..20 {
            s.txn(&tx(
                t0 + i * 3600,
                1,
                1,
                "SHOP",
                1_000_000 + (i as u64 % 3) * 100_000,
            ));
        }
        let v = s.txn(&tx(t0 + 21 * 3600, 1, 1, "SHOP", 500_000_000));
        assert!(f(&v, "amount_zscore") > 5.0);
        assert!(f(&v, "amount_to_card_mean_ratio") > 100.0);
    }

    /// Har xil hodisalar bilan to'ldirilgan ombor (kartalar, qurilmalar, P2P, graf, taxallus).
    fn busy_store() -> FeatureStore {
        let mut s = FeatureStore::new();
        let t0 = 1_800_000_000;
        for i in 0..40i64 {
            let card = (i % 7) as u8;
            let dev = (i % 3) as u8;
            let merchant = if i % 5 == 0 { "P2P-1" } else { "SHOP" };
            s.txn(&tx(
                t0 + i * 97,
                card,
                dev,
                merchant,
                10_000 + i as u64 * 1_000,
            ));
        }
        s.provision(&ProvisionEvent {
            at: t0 + 5_000,
            device: [9; 32],
            card: [1; 32],
            attestation_level: 2,
            existing_tokens_for_pan: 1,
            existing_tokens_for_device: 0,
            integrity: None,
        });
        assert!(s.device_rekeyed([1; 32], [42; 32]));
        s
    }

    #[test]
    fn snapshot_restores_identical_future_features() {
        let mut a = busy_store();
        let bytes = a.snapshot();
        let mut b = FeatureStore::restore(&bytes).unwrap();
        // Deterministik: tiklangan omborning snapshot'i — o'sha baytlar.
        assert_eq!(b.snapshot(), bytes);
        assert_eq!(a.stats(), b.stats());
        // Keyingi hodisalarda ikkalasi bir xil belgilar beradi (taxallus orqali ham).
        let t = 1_800_010_000;
        for (i, e) in [
            tx(t, 1, 42, "SHOP", 55_000),
            tx(t + 5, 3, 2, "P2P-1", 70_000),
            tx(t + 9, 200, 0, "SHOPX", 100),
        ]
        .iter()
        .enumerate()
        {
            assert_eq!(a.txn(e), b.txn(e), "hodisa {i}");
        }
        let p = ProvisionEvent {
            at: t + 20,
            device: [42; 32],
            card: [5; 32],
            attestation_level: 2,
            existing_tokens_for_pan: 0,
            existing_tokens_for_device: 2,
            integrity: None,
        };
        assert_eq!(a.provision(&p), b.provision(&p));
        assert_eq!(a.snapshot(), b.snapshot());
    }

    #[test]
    fn corrupted_snapshot_is_rejected() {
        use crate::snapshot::SnapshotError;
        let bytes = busy_store().snapshot();
        let mut t = bytes.clone();
        t[bytes.len() / 2] ^= 1;
        assert_eq!(
            FeatureStore::restore(&t).unwrap_err(),
            SnapshotError::Checksum
        );
        assert!(FeatureStore::restore(&bytes[..bytes.len() - 1]).is_err());
        assert!(FeatureStore::restore(b"MPSHSNP1").is_err());
        assert!(FeatureStore::restore(&[]).is_err());
        // Bo'sh ombor ham tiklanadi.
        let empty = FeatureStore::new().snapshot();
        assert_eq!(FeatureStore::restore(&empty).unwrap().stats(), (0, 0, 0, 0));
    }

    #[test]
    fn union_find_cycle_in_snapshot_is_rejected() {
        // Xesh to'g'ri, lekin graf ichida aylana (qo'lda yig'ilgan) — tiklash `find` da osilib qolmasin.
        let bytes = crate::snapshot::seal(|w| {
            w.u64(0);
            for _ in 0..3 {
                w.len(0); // kartalar, qurilmalar, savdo nuqtalari
            }
            w.len(0); // p2p
            w.len(2);
            for (i, parent) in [(1u8, 1u64), (2, 0)] {
                w.u8(0);
                w.a32(&[i; 32]);
                w.u64(parent);
                w.u32(1);
                w.u32(0);
            }
            w.len(0);
            w.len(0);
        });
        assert!(matches!(
            FeatureStore::restore(&bytes),
            Err(crate::snapshot::SnapshotError::Format(_))
        ));
    }

    proptest::proptest! {
        #[test]
        fn restore_never_panics(data in proptest::collection::vec(proptest::prelude::any::<u8>(), 0..600)) {
            let _ = FeatureStore::restore(&data);
            // Xeshi to'g'ri, mazmuni tasodifiy tana.
            let sealed = crate::snapshot::seal(|w| for b in &data { w.u8(*b) });
            let _ = FeatureStore::restore(&sealed);
        }
    }

    #[test]
    fn provisioning_device_farm() {
        let mut s = FeatureStore::new();
        let mut last = [0.0; IDV_FEATURES.len()];
        for c in 0..6u8 {
            last = s.provision(&ProvisionEvent {
                at: 1_800_000_000 + i64::from(c),
                device: [9; 32],
                card: [c; 32],
                attestation_level: 2,
                existing_tokens_for_pan: 0,
                existing_tokens_for_device: u32::from(c),
                integrity: None,
            });
        }
        assert_eq!(last[idv_index("device_card_count").unwrap()], 6.0);
        assert_eq!(last[idv_index("device_prov_count_24h").unwrap()], 5.0);
    }
}
