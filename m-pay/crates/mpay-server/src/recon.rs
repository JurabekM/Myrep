//! Solishtirish (reconciliation, ADR-0024): acquirer jurnali ↔ emitent qaydnomasi.
//!
//! Har avtorizatsiya ikki joyda yoziladi: acquirer (`acquirer_requests` — terminal ko'rgan javob)
//! va emitent (`issuer_authorizations` — pul yechilgan-yechilmagani). Kalit — `(terminal, STAN, RRN)`.
//! Ikki tomon farq qilsa — tafovut:
//!
//! | Tur | Ma'nosi |
//! |---|---|
//! | `ISSUER_ONLY_APPROVED` | emitent yechgan (qaytarmagan), terminal tasdiq olmagan — mijozdan pul ketgan, tovar berilmagan |
//! | `ACQUIRER_ONLY_APPROVED` | terminal tasdiq olgan, emitentda yechim yo'q yoki qaytarilgan — savdo nuqtasiga pul tushmaydi |
//! | `AMOUNT_MISMATCH` | ikkalasi tasdiqlagan, summa yoki valyuta farqli |
//! | `REVERSAL_FAILED` | emitent reversal'ni rad etdi — qo'lda ko'rib chiqish |
//! | `CLEARING_REJECTED` | ikki tomon tasdiqlagan, lekin emitent kliringda rad etdi (ADR-0025) — savdo nuqtasiga to'lanmaydi |
//!
//! Izohlar (tafovut emas, vaqtinchalik): `REVERSAL_PENDING` — reversal hali yuborilmoqda,
//! `IN_FLIGHT` — avtorizatsiya hali ishlanmoqda.
//!
//! Davr chetidagi yozuvlar uchun ikki tomon `MARGIN_SECS` kengroq o'qiladi; hisobotga faqat davr
//! ichidagilar kiradi. Acquirer jurnali `dedup::RETENTION_SECS` saqlanadi — undan eski davr rad
//! etiladi. Sana — sxema vaqti bo'yicha kun (UTC+5, `pan::EXPIRY_UTC_OFFSET_SECS`).
//!
//! Hisobotda PAN yo'q — faqat maskalangan DPAN, RRN, STAN, terminal.

use std::collections::{BTreeMap, HashMap};

use mpay_issuer::IssuerRecord;
use mpay_vault::db::Db;
use serde::{Deserialize, Serialize};
use sqlx::Row;

use crate::state::AppState;

/// Davr chetlari uchun qo'shimcha oyna (s).
pub const MARGIN_SECS: i64 = 300;
/// Bitta hisobotning eng uzun davri.
pub const MAX_PERIOD_SECS: i64 = 7 * 24 * 3600;

/// Yozuv turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReconKind {
    IssuerOnlyApproved,
    AcquirerOnlyApproved,
    AmountMismatch,
    ReversalFailed,
    ClearingRejected,
    ReversalPending,
    InFlight,
}

impl ReconKind {
    /// Tafovutmi (izoh emas).
    pub fn is_discrepancy(self) -> bool {
        !matches!(self, Self::ReversalPending | Self::InFlight)
    }
}

/// Hisobot qatori.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReconItem {
    pub kind: ReconKind,
    pub terminal_id: String,
    pub merchant_id: String,
    pub stan: String,
    pub rrn: String,
    pub dpan_masked: Option<String>,
    /// Yozuv vaqti (unix): acquirer yozuvi bo'lsa — uniki, aks holda emitentniki.
    pub at: i64,
    pub acquirer_code: Option<String>,
    pub acquirer_amount_minor: Option<i64>,
    pub issuer_code: Option<String>,
    pub issuer_amount_minor: Option<i64>,
    pub issuer_reversed: bool,
    pub currency: u16,
    /// Reversal holati: `PENDING`, `DONE:REVERSED`, `FAILED:AMOUNT_MISMATCH` …
    pub reversal: Option<String>,
    /// Kliring natijasi (ADR-0025): `PENDING`, `ACCEPTED`, `REJECTED:ORIGINAL_NOT_FOUND` …
    pub clearing: Option<String>,
}

/// Valyuta bo'yicha tasdiqlangan (ikki tomon mos) avtorizatsiyalar.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ApprovedTotal {
    pub currency: u16,
    pub count: u64,
    pub amount_minor: i64,
}

/// Solishtirish hisoboti.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct ReconReport {
    /// Davr `[from, to)` (unix).
    pub from: i64,
    pub to: i64,
    pub generated_at: i64,
    pub acquirer_records: usize,
    pub issuer_records: usize,
    /// Ikki tomon mos kelgan acquirer yozuvlari.
    pub matched: usize,
    /// Kliringda emitent qabul qilgan acquirer yozuvlari (kliring hali bo'lmagan kun — 0).
    pub cleared: usize,
    pub approved: Vec<ApprovedTotal>,
    pub discrepancies: Vec<ReconItem>,
    pub notes: Vec<ReconItem>,
}

impl ReconReport {
    pub fn is_clean(&self) -> bool {
        self.discrepancies.is_empty()
    }
}

/// Acquirer jurnali yozuvi.
#[derive(Debug, Clone)]
pub struct AcquirerRecord {
    pub at: i64,
    pub terminal_ref: String,
    pub merchant_id: String,
    pub stan: i64,
    pub rrn: String,
    pub amount_minor: i64,
    pub currency: u16,
    pub dpan_masked: String,
    /// `PENDING` yoki `DONE`.
    pub state: String,
    pub response_code: Option<String>,
}

/// Reversal navbati yozuvi.
#[derive(Debug, Clone)]
pub struct ReversalRecord {
    pub terminal_ref: String,
    pub stan: i64,
    pub rrn: String,
    pub state: String,
    pub result: Option<String>,
}

/// Kliring paketi yozuvi (ADR-0025).
#[derive(Debug, Clone)]
pub struct ClearingItemRecord {
    pub terminal_ref: String,
    pub stan: i64,
    pub rrn: String,
    /// `PENDING`, `ACCEPTED`, `REJECTED`.
    pub status: String,
    pub reason: Option<String>,
}

type Key = (String, String, String);

fn key(terminal: &str, stan: &str, rrn: &str) -> Key {
    (terminal.to_owned(), stan.to_owned(), rrn.to_owned())
}

fn effective_approved(r: &IssuerRecord) -> bool {
    r.response_code == "00" && r.reversed_at.is_none()
}

/// Sof solishtirish: acquirer yozuvlari `[from − M, to + M)`, emitent yozuvlari ham shu oynada.
pub fn reconcile(
    acquirer: &[AcquirerRecord],
    reversals: &[ReversalRecord],
    issuer: &[IssuerRecord],
    clearing: &[ClearingItemRecord],
    from: i64,
    to: i64,
    now: i64,
) -> ReconReport {
    let clr: HashMap<Key, &ClearingItemRecord> = clearing
        .iter()
        .map(|c| (key(&c.terminal_ref, &format!("{:06}", c.stan), &c.rrn), c))
        .collect();
    let mut cleared = 0;
    let mut iss: HashMap<Key, Vec<&IssuerRecord>> = HashMap::new();
    for r in issuer {
        iss.entry(key(&r.terminal_id, &r.stan, &r.rrn))
            .or_default()
            .push(r);
    }
    let revs: HashMap<Key, &ReversalRecord> = reversals
        .iter()
        .map(|r| (key(&r.terminal_ref, &format!("{:06}", r.stan), &r.rrn), r))
        .collect();
    let in_period = |t: i64| t >= from && t < to;

    let mut items = Vec::new();
    let mut totals: BTreeMap<u16, (u64, i64)> = BTreeMap::new();
    let mut matched = 0;
    let mut acquirer_records = 0;
    for a in acquirer {
        let stan = format!("{:06}", a.stan);
        let k = key(&a.terminal_ref, &stan, &a.rrn);
        // Chetdagi (davrdan tashqari) yozuvlar ham emitent juftini "band qiladi".
        let pair = iss.remove(&k).unwrap_or_default();
        if !in_period(a.at) {
            continue;
        }
        acquirer_records += 1;
        let approved_iss = pair.iter().copied().find(|r| effective_approved(r));
        let shown_iss = approved_iss.or_else(|| pair.first().copied());
        let rev = revs.get(&k);
        let clr_item = clr.get(&k);
        let item = |kind| ReconItem {
            kind,
            terminal_id: a.terminal_ref.clone(),
            merchant_id: a.merchant_id.clone(),
            stan: stan.clone(),
            rrn: a.rrn.clone(),
            dpan_masked: Some(a.dpan_masked.clone()),
            at: a.at,
            acquirer_code: a.response_code.clone(),
            acquirer_amount_minor: Some(a.amount_minor),
            issuer_code: shown_iss.map(|r| r.response_code.clone()),
            issuer_amount_minor: shown_iss.map(|r| r.amount_minor),
            issuer_reversed: shown_iss.is_some_and(|r| r.reversed_at.is_some()),
            currency: a.currency,
            reversal: rev.map(|r| match &r.result {
                Some(x) => format!("{}:{x}", r.state),
                None => r.state.clone(),
            }),
            clearing: clr_item.map(|c| match &c.reason {
                Some(x) if c.status == "REJECTED" => format!("{}:{x}", c.status),
                _ => c.status.clone(),
            }),
        };
        if clr_item.is_some_and(|c| c.status == "ACCEPTED") {
            cleared += 1;
        }
        if a.state == "PENDING" {
            items.push(item(ReconKind::InFlight));
            continue;
        }
        if rev.is_some_and(|r| r.state == "FAILED") {
            items.push(item(ReconKind::ReversalFailed));
            continue;
        }
        let acq_approved = a.response_code.as_deref() == Some("00");
        match (acq_approved, approved_iss) {
            (true, Some(i))
                if i.amount_minor == a.amount_minor
                    && i.currency == a.currency
                    && clr_item.is_some_and(|c| c.status == "REJECTED") =>
            {
                items.push(item(ReconKind::ClearingRejected));
            }
            (true, Some(i)) if i.amount_minor == a.amount_minor && i.currency == a.currency => {
                matched += 1;
                let t = totals.entry(a.currency).or_default();
                t.0 += 1;
                t.1 += a.amount_minor;
            }
            (true, Some(_)) => items.push(item(ReconKind::AmountMismatch)),
            (true, None) => items.push(item(ReconKind::AcquirerOnlyApproved)),
            (false, Some(_)) if rev.is_some_and(|r| r.state == "PENDING") => {
                items.push(item(ReconKind::ReversalPending));
            }
            (false, Some(_)) => items.push(item(ReconKind::IssuerOnlyApproved)),
            (false, None) => matched += 1,
        }
    }
    // Acquirer yozuvi umuman yo'q, emitent esa yechgan.
    let mut issuer_records = 0;
    for r in issuer.iter().filter(|r| in_period(r.ts)) {
        issuer_records += 1;
        let k = key(&r.terminal_id, &r.stan, &r.rrn);
        if iss.contains_key(&k) && effective_approved(r) {
            items.push(ReconItem {
                kind: ReconKind::IssuerOnlyApproved,
                terminal_id: r.terminal_id.clone(),
                merchant_id: r.merchant_id.clone(),
                stan: r.stan.clone(),
                rrn: r.rrn.clone(),
                dpan_masked: r.dpan_masked.clone(),
                at: r.ts,
                acquirer_code: None,
                acquirer_amount_minor: None,
                issuer_code: Some(r.response_code.clone()),
                issuer_amount_minor: Some(r.amount_minor),
                issuer_reversed: false,
                currency: r.currency,
                reversal: None,
                clearing: None,
            });
        }
    }
    items.sort_by(|a, b| {
        (a.at, &a.terminal_id, &a.stan, &a.rrn, a.kind).cmp(&(
            b.at,
            &b.terminal_id,
            &b.stan,
            &b.rrn,
            b.kind,
        ))
    });
    let (discrepancies, notes) = items.into_iter().partition(|i| i.kind.is_discrepancy());
    ReconReport {
        from,
        to,
        generated_at: now,
        acquirer_records,
        issuer_records,
        matched,
        cleared,
        approved: totals
            .into_iter()
            .map(|(currency, (count, amount_minor))| ApprovedTotal {
                currency,
                count,
                amount_minor,
            })
            .collect(),
        discrepancies,
        notes,
    }
}

/// Acquirer jurnali `[from, to)` (jurnal ustunlari bor yozuvlar).
pub async fn acquirer_records(
    db: &Db,
    from: i64,
    to: i64,
) -> Result<Vec<AcquirerRecord>, sqlx::Error> {
    let rows = sqlx::query(
        "SELECT created_at, terminal_ref, merchant_id, stan, rrn, amount_minor, currency, \
         dpan_masked, state, response_code FROM acquirer_requests \
         WHERE created_at >= $1 AND created_at < $2 AND rrn IS NOT NULL \
         ORDER BY created_at, terminal_id, stan",
    )
    .bind(from)
    .bind(to)
    .fetch_all(db.pool())
    .await?;
    rows.iter()
        .map(|r| {
            Ok(AcquirerRecord {
                at: r.try_get("created_at")?,
                terminal_ref: r
                    .try_get::<Option<String>, _>("terminal_ref")?
                    .unwrap_or_default(),
                merchant_id: r
                    .try_get::<Option<String>, _>("merchant_id")?
                    .unwrap_or_default(),
                stan: r.try_get("stan")?,
                rrn: r.try_get("rrn")?,
                amount_minor: r.try_get::<Option<i64>, _>("amount_minor")?.unwrap_or(0),
                currency: r.try_get::<Option<i64>, _>("currency")?.unwrap_or(0) as u16,
                dpan_masked: r
                    .try_get::<Option<String>, _>("dpan_masked")?
                    .unwrap_or_default(),
                state: r.try_get("state")?,
                response_code: r.try_get("response_code")?,
            })
        })
        .collect()
}

/// Reversal navbati (shu davrdagi yozuvlar).
pub async fn reversal_records(
    db: &Db,
    from: i64,
    to: i64,
) -> Result<Vec<ReversalRecord>, sqlx::Error> {
    let rows = sqlx::query(
        "SELECT terminal_ref, stan, rrn, state, result FROM acquirer_reversals \
         WHERE created_at >= $1 AND created_at < $2 ORDER BY created_at, terminal_id, stan",
    )
    .bind(from)
    .bind(to)
    .fetch_all(db.pool())
    .await?;
    rows.iter()
        .map(|r| {
            Ok(ReversalRecord {
                terminal_ref: r.try_get("terminal_ref")?,
                stan: r.try_get("stan")?,
                rrn: r.try_get("rrn")?,
                state: r.try_get("state")?,
                result: r.try_get("result")?,
            })
        })
        .collect()
}

/// Kliring yozuvlari (avtorizatsiya vaqti `[from, to)`).
pub async fn clearing_records(
    db: &Db,
    from: i64,
    to: i64,
) -> Result<Vec<ClearingItemRecord>, sqlx::Error> {
    let rows = sqlx::query(
        "SELECT terminal_ref, stan, rrn, status, reason FROM clearing_items \
         WHERE txn_at >= $1 AND txn_at < $2 ORDER BY txn_at, batch_id, seq",
    )
    .bind(from)
    .bind(to)
    .fetch_all(db.pool())
    .await?;
    rows.iter()
        .map(|r| {
            Ok(ClearingItemRecord {
                terminal_ref: r.try_get("terminal_ref")?,
                stan: r.try_get("stan")?,
                rrn: r.try_get("rrn")?,
                status: r.try_get("status")?,
                reason: r.try_get("reason")?,
            })
        })
        .collect()
}

/// Solishtirish xatosi.
#[derive(Debug, thiserror::Error)]
pub enum ReconError {
    #[error("davr: {0}")]
    Period(String),
    #[error("ma'lumotlar bazasi: {0}")]
    Db(#[from] sqlx::Error),
    #[error("emitent: {0}")]
    Issuer(#[from] mpay_issuer::IssuerError),
}

/// Davrni tekshiradi va hisobotni tuzadi (emitent qaydnomasi — jarayon ichidagi emulyatordan).
pub async fn run(state: &AppState, from: i64, to: i64) -> Result<ReconReport, ReconError> {
    let now = state.clock.unix();
    if to <= from || to - from > MAX_PERIOD_SECS {
        return Err(ReconError::Period(format!(
            "from < to va davr ≤ {} kun",
            MAX_PERIOD_SECS / 86_400
        )));
    }
    if from - MARGIN_SECS < now - crate::dedup::RETENTION_SECS {
        return Err(ReconError::Period(format!(
            "acquirer jurnali {} kun saqlanadi — davr undan eski",
            crate::dedup::RETENTION_SECS / 86_400
        )));
    }
    let db = state.vault.db();
    let (lo, hi) = (from - MARGIN_SECS, to + MARGIN_SECS);
    let acq = acquirer_records(db, lo, hi).await?;
    let revs = reversal_records(db, lo, hi).await?;
    // `TODO(spec):` real bankda emitent qaydnomasi — bankning kunlik fayli (format kelishiladi).
    let iss = state.issuer.report(lo, hi).await?;
    let clr = clearing_records(db, lo, hi).await?;
    Ok(reconcile(&acq, &revs, &iss, &clr, from, to, now))
}

/// `YYYY-MM-DD` — sxema vaqti bo'yicha kun (UTC+5) → `[from, to)`.
pub fn business_day(date: &str) -> Result<(i64, i64), String> {
    let fmt = time::macros::format_description!("[year]-[month]-[day]");
    let d = time::Date::parse(date, fmt).map_err(|_| "sana: YYYY-MM-DD".to_owned())?;
    let from = d
        .midnight()
        .assume_offset(mpay_common::pan::expiry_offset())
        .unix_timestamp();
    Ok((from, from + 86_400))
}

/// Davr: `date` (sxema vaqti bo'yicha kun) yoki `from` + `to` (unix); hech biri — bugun.
pub fn period(
    date: Option<&str>,
    from: Option<i64>,
    to: Option<i64>,
    now: time::OffsetDateTime,
) -> Result<(i64, i64), String> {
    match (date, from, to) {
        (Some(d), None, None) => business_day(d),
        (None, Some(f), Some(t)) => Ok((f, t)),
        (None, None, None) => business_day(&today(now)),
        _ => Err("date yoki from + to".into()),
    }
}

/// Joriy kun (sxema vaqti) `YYYY-MM-DD`.
pub fn today(now: time::OffsetDateTime) -> String {
    let d = now.to_offset(mpay_common::pan::expiry_offset()).date();
    format!("{:04}-{:02}-{:02}", d.year(), u8::from(d.month()), d.day())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn acq(stan: i64, code: &str, amount: i64, at: i64) -> AcquirerRecord {
        AcquirerRecord {
            at,
            terminal_ref: "TERM0001".into(),
            merchant_id: "SHOP0000000001".into(),
            stan,
            rrn: format!("63001400{stan:04}"),
            amount_minor: amount,
            currency: 860,
            dpan_masked: "990077******0001".into(),
            state: "DONE".into(),
            response_code: Some(code.into()),
        }
    }

    fn iss(stan: i64, code: &str, amount: i64, at: i64) -> IssuerRecord {
        IssuerRecord {
            ts: at,
            stan: format!("{stan:06}"),
            rrn: format!("63001400{stan:04}"),
            terminal_id: "TERM0001".into(),
            merchant_id: "SHOP0000000001".into(),
            dpan_masked: Some("990077******0001".into()),
            amount_minor: amount,
            currency: 860,
            response_code: code.into(),
            reversed_at: None,
        }
    }

    fn rev(stan: i64, state: &str, result: Option<&str>) -> ReversalRecord {
        ReversalRecord {
            terminal_ref: "TERM0001".into(),
            stan,
            rrn: format!("63001400{stan:04}"),
            state: state.into(),
            result: result.map(Into::into),
        }
    }

    #[test]
    fn classifies_every_case() {
        let (from, to) = (1_000, 2_000);
        let mut reversed = iss(6, "00", 600, 1_106);
        reversed.reversed_at = Some(1_200);
        let mut in_flight = acq(9, "", 900, 1_109);
        in_flight.state = "PENDING".into();
        in_flight.response_code = None;
        let a = vec![
            acq(1, "00", 100, 1_101), // mos: tasdiq
            acq(2, "51", 200, 1_102), // mos: rad
            acq(3, "96", 300, 1_103), // emitent yechgan, reversal yo'q
            acq(4, "00", 400, 1_104), // emitentda yo'q
            acq(5, "00", 500, 1_105), // summa farqli
            acq(6, "96", 600, 1_106), // qaytarilgan — mos
            acq(7, "96", 700, 1_107), // reversal yuborilmoqda
            acq(8, "96", 800, 1_108), // reversal rad etildi
            in_flight,
            acq(20, "00", 50, 990), // davrdan oldin (chet): hisobotga kirmaydi, jufti band
        ];
        let i = vec![
            iss(1, "00", 100, 1_101),
            iss(2, "51", 200, 1_102),
            iss(3, "00", 300, 1_103),
            iss(5, "00", 501, 1_105),
            reversed,
            iss(7, "00", 700, 1_107),
            iss(8, "00", 800, 1_108),
            iss(20, "00", 50, 1_001), // juft acquirer chetda — tafovut emas
            iss(30, "00", 3_000, 1_130), // acquirer yozuvi yo'q
            iss(31, "05", 3_100, 1_131), // rad, acquirer yo'q — tafovut emas
            iss(40, "00", 4_000, 2_100), // davrdan keyin — hisobotga kirmaydi
        ];
        let r = vec![
            rev(6, "DONE", Some("REVERSED")),
            rev(7, "PENDING", None),
            rev(8, "FAILED", Some("AMOUNT_MISMATCH")),
        ];
        let clr = vec![
            ClearingItemRecord {
                terminal_ref: "TERM0001".into(),
                stan: 1,
                rrn: "630014000001".into(),
                status: "ACCEPTED".into(),
                reason: Some("ACCEPTED".into()),
            },
            ClearingItemRecord {
                terminal_ref: "TERM0001".into(),
                stan: 10,
                rrn: "630014000010".into(),
                status: "REJECTED".into(),
                reason: Some("ORIGINAL_NOT_FOUND".into()),
            },
        ];
        let mut a = a;
        let mut i = i;
        a.push(acq(10, "00", 1_000, 1_110)); // ikki tomon mos, kliringda rad
        i.push(iss(10, "00", 1_000, 1_110));
        let rep = reconcile(&a, &r, &i, &clr, from, to, 5_000);
        let kinds: Vec<(String, ReconKind)> = rep
            .discrepancies
            .iter()
            .map(|x| (x.stan.clone(), x.kind))
            .collect();
        assert_eq!(
            kinds,
            vec![
                ("000003".into(), ReconKind::IssuerOnlyApproved),
                ("000004".into(), ReconKind::AcquirerOnlyApproved),
                ("000005".into(), ReconKind::AmountMismatch),
                ("000008".into(), ReconKind::ReversalFailed),
                ("000010".into(), ReconKind::ClearingRejected),
                ("000030".into(), ReconKind::IssuerOnlyApproved),
            ]
        );
        let notes: Vec<(String, ReconKind)> =
            rep.notes.iter().map(|x| (x.stan.clone(), x.kind)).collect();
        assert_eq!(
            notes,
            vec![
                ("000007".into(), ReconKind::ReversalPending),
                ("000009".into(), ReconKind::InFlight),
            ]
        );
        assert_eq!(rep.matched, 3, "1 (tasdiq), 2 (rad), 6 (qaytarilgan)");
        assert_eq!(rep.acquirer_records, 10);
        assert_eq!(rep.issuer_records, 11);
        assert_eq!(rep.cleared, 1);
        assert_eq!(
            rep.discrepancies[4].clearing.as_deref(),
            Some("REJECTED:ORIGINAL_NOT_FOUND")
        );
        assert_eq!(
            rep.approved,
            vec![ApprovedTotal {
                currency: 860,
                count: 1,
                amount_minor: 100
            }]
        );
        assert!(!rep.is_clean());
        let mm = &rep.discrepancies[2];
        assert_eq!(
            (mm.acquirer_amount_minor, mm.issuer_amount_minor),
            (Some(500), Some(501))
        );
        assert_eq!(
            rep.discrepancies[3].reversal.as_deref(),
            Some("FAILED:AMOUNT_MISMATCH")
        );
        // Hisobotda ochiq PAN yo'q.
        let json = serde_json::to_string(&rep).unwrap();
        assert!(!json.contains("9900770000"));
    }

    #[test]
    fn empty_period_is_clean() {
        let rep = reconcile(&[], &[], &[], &[], 0, 10, 10);
        assert!(rep.is_clean());
        assert_eq!(rep.matched, 0);
    }

    #[test]
    fn business_day_is_uzbekistan_midnight() {
        let (from, to) = business_day("2026-10-27").unwrap();
        // 2026-10-27 00:00 Toshkent = 2026-10-26 19:00 UTC.
        assert_eq!(
            from,
            time::macros::datetime!(2026-10-26 19:00 UTC).unix_timestamp()
        );
        assert_eq!(to - from, 86_400);
        assert!(business_day("27.10.2026").is_err());
        assert_eq!(
            today(time::macros::datetime!(2026-10-26 19:30 UTC)),
            "2026-10-27"
        );
    }
}
