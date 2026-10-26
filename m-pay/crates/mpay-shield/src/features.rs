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
pub const IDV_FEATURES: [&str; 9] = [
    "device_card_count",
    "card_device_count",
    "component_size",
    "device_prov_count_24h",
    "card_prov_count_24h",
    "attestation_level",
    "device_age_secs_log",
    "existing_tokens_for_pan",
    "existing_tokens_for_device",
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
        let edge = self.graph.touch(e.device, e.card, now);
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
        let dev = self.devices.entry(e.device).or_default();
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
        let edge = self.graph.touch(e.device, e.card, now);
        let dev = self.devices.entry(e.device).or_default();
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
        ]
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
            });
        }
        assert_eq!(last[idv_index("device_card_count").unwrap()], 6.0);
        assert_eq!(last[idv_index("device_prov_count_24h").unwrap()], 5.0);
    }
}
