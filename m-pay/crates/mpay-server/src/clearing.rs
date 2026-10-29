//! Kunlik kliring va hisob-kitob (settlement, ADR-0025).
//!
//! Bir kun (sxema vaqti, UTC+5) — bitta paket, uch bosqich; har biri qayta ishga tushirilsa davom etadi:
//!
//! 1. **`BUILT`** — acquirer jurnalidan kun ichidagi **tasdiqlangan** (`00`, terminal tovar bergan)
//!    avtorizatsiyalar paketga nusxalanadi va kliring fayli yig'iladi (`mpay_common::clearing`).
//!    Kun tugagach `cutoff_grace_secs` o'tgan va kun ichida javobi kutilayotgan (`PENDING`) yozuv
//!    qolmagan bo'lishi shart. Kun acquirer jurnali saqlanish muddatida bo'lishi kerak (3 kun).
//! 2. **`ACKED`** — fayl emitentga yuboriladi; tasdiqdagi har yozuv natijasi (`ACCEPTED` yoki
//!    `REJECTED` + sabab) saqlanadi. Emitent bir paket ID'ga bitta natija beradi — qayta yuborish xavfsiz.
//! 3. **`SETTLED`** — qabul qilingan yozuvlar bo'yicha pozitsiyalar:
//!    * `MERCHANT` — har savdo nuqtasi va valyuta: yalpi, komissiya (MDR), to'lanadigan;
//!    * `ISSUER` — emitent acquirer'ga to'laydi: yalpi − interchange;
//!    * `ACQUIRER` — M-Pay daromadi: MDR − interchange.
//!
//!    Tekshiruv: `ISSUER.net = Σ MERCHANT.net + ACQUIRER.net` (har valyutada). Komissiya —
//!    savdo nuqtasi/valyuta jamisidan, butun tiyingacha yarmidan yuqoriga yaxlitlanadi. Paketda
//!    ishlatilgan tariflar saqlanadi (keyin konfiguratsiya o'zgarsa ham hisobot o'zgarmaydi).
//!
//! Rad etilgan yozuvlar hisob-kitobga kirmaydi va hisobotda ko'rsatiladi (`rejected_items`).
//! Kliring yozuvlari doimiy saqlanadi (acquirer jurnalidan farqli).

use std::collections::BTreeMap;
use std::time::Duration;

use mpay_common::clearing::{ClearingAck, ClearingFile, ClearingRecord};
use mpay_vault::db::Db;
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use sqlx::Row;

use crate::state::AppState;

/// Emitent kliring faylini qayta ishlashini kutish.
const ISSUER_TIMEOUT: Duration = Duration::from_secs(120);
/// Sandbox'dagi yagona emitent (`TODO(spec):` real tarmoqda emitentlar BIN/bank bo'yicha).
pub const ISSUER_PARTY: &str = "issuer";
/// Acquirer (M-Pay).
pub const ACQUIRER_PARTY: &str = "mpay";

#[derive(Debug, thiserror::Error)]
pub enum ClearingError {
    #[error("davr: {0}")]
    Period(String),
    #[error("paket hali tayyor emas: {0}")]
    NotReady(String),
    #[error("emitent: {0}")]
    Issuer(String),
    #[error("ma'lumotlar bazasi: {0}")]
    Db(#[from] sqlx::Error),
    #[error("kliring fayli: {0}")]
    Format(#[from] mpay_common::clearing::ClearingError),
    #[error("hisob-kitob muvozanati buzilgan (valyuta {0})")]
    Unbalanced(u16),
}

/// Hisob-kitob pozitsiyasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Position {
    /// `ISSUER`, `MERCHANT`, `ACQUIRER`.
    pub party: String,
    pub party_id: String,
    pub currency: u16,
    pub count: u64,
    pub gross_minor: i64,
    pub fee_minor: i64,
    pub net_minor: i64,
}

/// Rad etilgan yozuv.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct RejectedItem {
    pub seq: u32,
    pub terminal_id: String,
    pub merchant_id: String,
    pub stan: String,
    pub rrn: String,
    pub dpan_masked: String,
    pub amount_minor: i64,
    pub currency: u16,
    pub code: Option<String>,
    pub reason: Option<String>,
}

/// Valyuta bo'yicha jami.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct CurrencyTotal {
    pub currency: u16,
    pub count: u64,
    pub amount_minor: i64,
}

/// Paket hisoboti.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct BatchReport {
    pub batch_id: String,
    /// `YYYY-MM-DD` (UTC+5).
    pub business_date: String,
    /// `BUILT`, `ACKED`, `SETTLED`.
    pub state: String,
    pub period_from: i64,
    pub period_to: i64,
    pub records: u64,
    pub accepted: Option<u64>,
    pub rejected: Option<u64>,
    /// Paketdagi barcha yozuvlar (valyuta bo'yicha).
    pub totals: Vec<CurrencyTotal>,
    pub file_sha256: String,
    pub merchant_fee_bps: Option<u32>,
    pub interchange_bps: Option<u32>,
    pub rejected_items: Vec<RejectedItem>,
    pub positions: Vec<Position>,
}

/// Komissiya: `gross × bps / 10 000`, yarmidan yuqoriga yaxlitlab.
pub fn fee(gross: i64, bps: u32) -> i64 {
    let v = (i128::from(gross) * i128::from(bps) + 5_000).div_euclid(10_000);
    v as i64
}

/// Qabul qilingan yozuvlar `(merchant, valyuta, summa)` → pozitsiyalar (sof funksiya).
pub fn settle(
    accepted: &[(String, u16, i64)],
    merchant_fee_bps: u32,
    interchange_bps: u32,
) -> Result<Vec<Position>, ClearingError> {
    let mut by_merchant: BTreeMap<(String, u16), (u64, i64)> = BTreeMap::new();
    for (m, c, a) in accepted {
        let e = by_merchant.entry((m.clone(), *c)).or_default();
        e.0 += 1;
        e.1 += a;
    }
    let mut out = Vec::new();
    // valyuta → (soni, yalpi, MDR jami, savdo nuqtalariga to'lanadigan)
    let mut per_cur: BTreeMap<u16, (u64, i64, i64, i64)> = BTreeMap::new();
    for ((m, c), (n, gross)) in &by_merchant {
        let f = fee(*gross, merchant_fee_bps);
        out.push(Position {
            party: "MERCHANT".into(),
            party_id: m.clone(),
            currency: *c,
            count: *n,
            gross_minor: *gross,
            fee_minor: f,
            net_minor: gross - f,
        });
        let t = per_cur.entry(*c).or_default();
        t.0 += n;
        t.1 += gross;
        t.2 += f;
        t.3 += gross - f;
    }
    for (c, (n, gross, mdr, merchants_net)) in per_cur {
        let ic = fee(gross, interchange_bps);
        let issuer = Position {
            party: "ISSUER".into(),
            party_id: ISSUER_PARTY.into(),
            currency: c,
            count: n,
            gross_minor: gross,
            fee_minor: ic,
            net_minor: gross - ic,
        };
        let acquirer = Position {
            party: "ACQUIRER".into(),
            party_id: ACQUIRER_PARTY.into(),
            currency: c,
            count: n,
            gross_minor: mdr,
            fee_minor: ic,
            net_minor: mdr - ic,
        };
        if issuer.net_minor != merchants_net + acquirer.net_minor {
            return Err(ClearingError::Unbalanced(c));
        }
        out.push(issuer);
        out.push(acquirer);
    }
    out.sort_by(|a, b| {
        (&a.party, &a.party_id, a.currency).cmp(&(&b.party, &b.party_id, b.currency))
    });
    Ok(out)
}

/// `YYYY-MM-DD` → paket ID (`MPAY` + `YYYYMMDD`).
pub fn batch_id(date: &str) -> String {
    format!("MPAY{}", date.replace('-', ""))
}

/// Paketni yaratadi (yoki mavjudini qaytaradi), emitentga yuboradi va hisob-kitobni hisoblaydi.
pub async fn run(state: &AppState, date: &str) -> Result<BatchReport, ClearingError> {
    let db = state.vault.db();
    let now = state.clock.unix();
    let (from, to) = crate::recon::business_day(date).map_err(ClearingError::Period)?;
    let id = batch_id(date);
    if load_state(db, &id).await?.is_none() {
        build(state, date, &id, from, to, now).await?;
    }
    if load_state(db, &id).await?.as_deref() == Some("BUILT") {
        submit(state, &id).await?;
    }
    if load_state(db, &id).await?.as_deref() == Some("ACKED") {
        settle_batch(state, &id).await?;
    }
    report(db, date)
        .await?
        .ok_or_else(|| ClearingError::Db(sqlx::Error::RowNotFound))
}

async fn load_state(db: &Db, id: &str) -> Result<Option<String>, sqlx::Error> {
    sqlx::query_scalar("SELECT state FROM clearing_batches WHERE batch_id = $1")
        .bind(id)
        .fetch_optional(db.pool())
        .await
}

async fn build(
    state: &AppState,
    date: &str,
    id: &str,
    from: i64,
    to: i64,
    now: i64,
) -> Result<(), ClearingError> {
    let db = state.vault.db();
    if now < to + state.clearing.cutoff_grace_secs {
        return Err(ClearingError::NotReady(format!(
            "kun tugagach {} s kutiladi",
            state.clearing.cutoff_grace_secs
        )));
    }
    if from < now - crate::dedup::RETENTION_SECS {
        return Err(ClearingError::Period(format!(
            "acquirer jurnali {} kun saqlanadi — kun undan eski",
            crate::dedup::RETENTION_SECS / 86_400
        )));
    }
    let pending: i64 = sqlx::query_scalar(
        "SELECT COUNT(*) FROM acquirer_requests \
         WHERE created_at >= $1 AND created_at < $2 AND state = 'PENDING'",
    )
    .bind(from)
    .bind(to)
    .fetch_one(db.pool())
    .await?;
    if pending > 0 {
        return Err(ClearingError::NotReady(format!(
            "{pending} ta avtorizatsiya javobi hali noma'lum"
        )));
    }
    let rows = sqlx::query(
        "SELECT created_at, terminal_ref, merchant_id, stan, rrn, amount_minor, currency, dpan_masked \
         FROM acquirer_requests \
         WHERE created_at >= $1 AND created_at < $2 AND response_code = '00' AND rrn IS NOT NULL \
         ORDER BY created_at, terminal_id, stan",
    )
    .bind(from)
    .bind(to)
    .fetch_all(db.pool())
    .await?;
    let mut records = Vec::with_capacity(rows.len());
    for (i, r) in rows.iter().enumerate() {
        records.push(ClearingRecord {
            seq: i as u32 + 1,
            terminal_id: r.try_get("terminal_ref")?,
            merchant_id: r.try_get("merchant_id")?,
            stan: r.try_get::<i64, _>("stan")? as u32,
            rrn: r.try_get("rrn")?,
            amount_minor: r.try_get::<i64, _>("amount_minor")?.max(0) as u64,
            currency: r.try_get::<i64, _>("currency")? as u16,
            txn_at: r.try_get("created_at")?,
            dpan_masked: r.try_get("dpan_masked")?,
        });
    }
    let file = ClearingFile {
        batch_id: id.to_owned(),
        business_date: date.replace('-', ""),
        created_at: now,
        records,
    };
    let bytes = file.encode()?;
    let sha = hex::encode(Sha256::digest(&bytes));
    let text = String::from_utf8(bytes).map_err(|_| {
        ClearingError::Format(mpay_common::clearing::ClearingError::Format {
            line: 0,
            msg: "ASCII emas",
        })
    })?;
    let mut tx = db.begin_write().await?;
    let inserted = sqlx::query(
        "INSERT INTO clearing_batches (batch_id, business_date, state, period_from, period_to, records, \
         file, file_sha256, created_at, updated_at) \
         VALUES ($1, $2, 'BUILT', $3, $4, $5, $6, $7, $8, $9) ON CONFLICT DO NOTHING",
    )
    .bind(id)
    .bind(date)
    .bind(from)
    .bind(to)
    .bind(file.records.len() as i64)
    .bind(&text)
    .bind(&sha)
    .bind(now)
    .bind(now)
    .execute(&mut *tx)
    .await?
    .rows_affected();
    if inserted == 0 {
        // Parallel ishga tushirish paketni allaqachon yaratgan.
        return Ok(());
    }
    for r in &file.records {
        sqlx::query(
            "INSERT INTO clearing_items (batch_id, seq, terminal_ref, merchant_id, stan, rrn, \
             amount_minor, currency, txn_at, dpan_masked, status) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 'PENDING')",
        )
        .bind(id)
        .bind(i64::from(r.seq))
        .bind(&r.terminal_id)
        .bind(&r.merchant_id)
        .bind(i64::from(r.stan))
        .bind(&r.rrn)
        .bind(r.amount_minor as i64)
        .bind(i64::from(r.currency))
        .bind(r.txn_at)
        .bind(&r.dpan_masked)
        .execute(&mut *tx)
        .await?;
    }
    tx.commit().await?;
    tracing::info!(
        batch = id,
        records = file.records.len(),
        "kliring: paket yaratildi"
    );
    Ok(())
}

async fn submit(state: &AppState, id: &str) -> Result<(), ClearingError> {
    let db = state.vault.db();
    let (file, records): (String, i64) =
        sqlx::query_as("SELECT file, records FROM clearing_batches WHERE batch_id = $1")
            .bind(id)
            .fetch_one(db.pool())
            .await?;
    let (ack_bytes, ack) = tokio::time::timeout(
        ISSUER_TIMEOUT,
        state.issuer.process_clearing(file.as_bytes()),
    )
    .await
    .map_err(|_| ClearingError::Issuer("javob bermadi".into()))?
    .map_err(|e| ClearingError::Issuer(e.to_string()))?;
    // Emitent tasdig'i — o'z formatida qayta tekshiriladi (jarayon ichidagi natijaga ishonilmaydi).
    let parsed = ClearingAck::parse(&ack_bytes)?;
    if parsed != ack || parsed.batch_id != id || parsed.records.len() as i64 != records {
        return Err(ClearingError::Issuer("tasdiq paketga mos emas".into()));
    }
    let text = String::from_utf8(ack_bytes).map_err(|_| ClearingError::Issuer("ack".into()))?;
    let accepted = parsed.accepted() as i64;
    let mut tx = db.begin_write().await?;
    let n = sqlx::query(
        "UPDATE clearing_batches SET state = 'ACKED', ack = $1, accepted = $2, rejected = $3, \
         updated_at = $4 WHERE batch_id = $5 AND state = 'BUILT'",
    )
    .bind(&text)
    .bind(accepted)
    .bind(records - accepted)
    .bind(state.clock.unix())
    .bind(id)
    .execute(&mut *tx)
    .await?
    .rows_affected();
    if n == 0 {
        return Ok(());
    }
    for r in &parsed.records {
        sqlx::query(
            "UPDATE clearing_items SET status = $1, code = $2, reason = $3 WHERE batch_id = $4 AND seq = $5",
        )
        .bind(if r.accepted() { "ACCEPTED" } else { "REJECTED" })
        .bind(&r.code)
        .bind(&r.reason)
        .bind(id)
        .bind(i64::from(r.seq))
        .execute(&mut *tx)
        .await?;
    }
    tx.commit().await?;
    if accepted < records {
        tracing::warn!(
            batch = id,
            rejected = records - accepted,
            "kliring: emitent yozuvlarni rad etdi"
        );
    } else {
        tracing::info!(batch = id, accepted, "kliring: emitent qabul qildi");
    }
    Ok(())
}

async fn settle_batch(state: &AppState, id: &str) -> Result<(), ClearingError> {
    let db = state.vault.db();
    let rows = sqlx::query(
        "SELECT merchant_id, currency, amount_minor FROM clearing_items \
         WHERE batch_id = $1 AND status = 'ACCEPTED' ORDER BY seq",
    )
    .bind(id)
    .fetch_all(db.pool())
    .await?;
    let accepted = rows
        .iter()
        .map(|r| {
            Ok((
                r.try_get::<String, _>("merchant_id")?,
                r.try_get::<i64, _>("currency")? as u16,
                r.try_get::<i64, _>("amount_minor")?,
            ))
        })
        .collect::<Result<Vec<_>, sqlx::Error>>()?;
    let cfg = &state.clearing;
    let positions = settle(&accepted, cfg.merchant_fee_bps, cfg.interchange_bps)?;
    let mut tx = db.begin_write().await?;
    let n = sqlx::query(
        "UPDATE clearing_batches SET state = 'SETTLED', merchant_fee_bps = $1, interchange_bps = $2, \
         updated_at = $3 WHERE batch_id = $4 AND state = 'ACKED'",
    )
    .bind(i64::from(cfg.merchant_fee_bps))
    .bind(i64::from(cfg.interchange_bps))
    .bind(state.clock.unix())
    .bind(id)
    .execute(&mut *tx)
    .await?
    .rows_affected();
    if n == 0 {
        return Ok(());
    }
    for p in &positions {
        sqlx::query(
            "INSERT INTO settlement_positions (batch_id, party, party_id, currency, count, gross_minor, \
             fee_minor, net_minor) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)",
        )
        .bind(id)
        .bind(&p.party)
        .bind(&p.party_id)
        .bind(i64::from(p.currency))
        .bind(p.count as i64)
        .bind(p.gross_minor)
        .bind(p.fee_minor)
        .bind(p.net_minor)
        .execute(&mut *tx)
        .await?;
    }
    tx.commit().await?;
    tracing::info!(
        batch = id,
        positions = positions.len(),
        "kliring: hisob-kitob tayyor"
    );
    Ok(())
}

/// Paket hisoboti (`None` — o'sha kun uchun paket yo'q).
pub async fn report(db: &Db, date: &str) -> Result<Option<BatchReport>, sqlx::Error> {
    let Some(b) = sqlx::query(
        "SELECT batch_id, business_date, state, period_from, period_to, records, file_sha256, \
         accepted, rejected, merchant_fee_bps, interchange_bps FROM clearing_batches \
         WHERE business_date = $1",
    )
    .bind(date)
    .fetch_optional(db.pool())
    .await?
    else {
        return Ok(None);
    };
    let id: String = b.try_get("batch_id")?;
    let items = sqlx::query(
        "SELECT seq, terminal_ref, merchant_id, stan, rrn, dpan_masked, amount_minor, currency, \
         status, code, reason FROM clearing_items WHERE batch_id = $1 ORDER BY seq",
    )
    .bind(&id)
    .fetch_all(db.pool())
    .await?;
    let mut totals: BTreeMap<u16, (u64, i64)> = BTreeMap::new();
    let mut rejected_items = Vec::new();
    for r in &items {
        let currency = r.try_get::<i64, _>("currency")? as u16;
        let amount: i64 = r.try_get("amount_minor")?;
        let t = totals.entry(currency).or_default();
        t.0 += 1;
        t.1 += amount;
        if r.try_get::<String, _>("status")? == "REJECTED" {
            rejected_items.push(RejectedItem {
                seq: r.try_get::<i64, _>("seq")? as u32,
                terminal_id: r.try_get("terminal_ref")?,
                merchant_id: r.try_get("merchant_id")?,
                stan: format!("{:06}", r.try_get::<i64, _>("stan")?),
                rrn: r.try_get("rrn")?,
                dpan_masked: r.try_get("dpan_masked")?,
                amount_minor: amount,
                currency,
                code: r.try_get("code")?,
                reason: r.try_get("reason")?,
            });
        }
    }
    let positions = sqlx::query(
        "SELECT party, party_id, currency, count, gross_minor, fee_minor, net_minor \
         FROM settlement_positions WHERE batch_id = $1 ORDER BY party, party_id, currency",
    )
    .bind(&id)
    .fetch_all(db.pool())
    .await?
    .iter()
    .map(|r| {
        Ok(Position {
            party: r.try_get("party")?,
            party_id: r.try_get("party_id")?,
            currency: r.try_get::<i64, _>("currency")? as u16,
            count: r.try_get::<i64, _>("count")? as u64,
            gross_minor: r.try_get("gross_minor")?,
            fee_minor: r.try_get("fee_minor")?,
            net_minor: r.try_get("net_minor")?,
        })
    })
    .collect::<Result<Vec<_>, sqlx::Error>>()?;
    let opt_u = |c: &str| -> Result<Option<u64>, sqlx::Error> {
        Ok(b.try_get::<Option<i64>, _>(c)?.map(|v| v as u64))
    };
    Ok(Some(BatchReport {
        batch_id: id,
        business_date: b.try_get("business_date")?,
        state: b.try_get("state")?,
        period_from: b.try_get("period_from")?,
        period_to: b.try_get("period_to")?,
        records: b.try_get::<i64, _>("records")? as u64,
        accepted: opt_u("accepted")?,
        rejected: opt_u("rejected")?,
        totals: totals
            .into_iter()
            .map(|(currency, (count, amount_minor))| CurrencyTotal {
                currency,
                count,
                amount_minor,
            })
            .collect(),
        file_sha256: b.try_get("file_sha256")?,
        merchant_fee_bps: opt_u("merchant_fee_bps")?.map(|v| v as u32),
        interchange_bps: opt_u("interchange_bps")?.map(|v| v as u32),
        rejected_items,
        positions,
    }))
}

/// Kliring fayli va emitent tasdig'i (matn).
pub async fn files(db: &Db, date: &str) -> Result<Option<(String, Option<String>)>, sqlx::Error> {
    sqlx::query_as("SELECT file, ack FROM clearing_batches WHERE business_date = $1")
        .bind(date)
        .fetch_optional(db.pool())
        .await
}

/// Savdo nuqtalariga to'lov ro'yxati (CSV). `TODO(spec):` savdo nuqtasi reyestri va bank rekvizitlari.
pub fn payouts_csv(r: &BatchReport) -> String {
    let mut out =
        String::from("batch_id,merchant_id,currency,count,gross_minor,fee_minor,net_minor\n");
    for p in r.positions.iter().filter(|p| p.party == "MERCHANT") {
        out.push_str(&format!(
            "{},{},{},{},{},{},{}\n",
            r.batch_id, p.party_id, p.currency, p.count, p.gross_minor, p.fee_minor, p.net_minor
        ));
    }
    out
}

/// Kecha (sxema vaqti) `YYYY-MM-DD` — kliringning standart kuni.
pub fn yesterday(now: time::OffsetDateTime) -> String {
    crate::recon::today(now - time::Duration::days(1))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn fee_rounds_half_up() {
        assert_eq!(fee(10_000, 150), 150);
        assert_eq!(fee(333, 150), 5); // 4,995 → 5
        assert_eq!(fee(100, 150), 2); // 1,5 → 2
        assert_eq!(fee(99, 150), 1); // 1,485 → 1
        assert_eq!(fee(0, 150), 0);
        assert_eq!(fee(999_999_999_999_999, 10_000), 999_999_999_999_999);
    }

    #[test]
    fn positions_balance_per_currency() {
        let acc = vec![
            ("SHOP2".to_owned(), 860, 100_000),
            ("SHOP1".to_owned(), 860, 333),
            ("SHOP1".to_owned(), 860, 1_000_000),
            ("SHOP1".to_owned(), 840, 2_500),
        ];
        let p = settle(&acc, 150, 100).unwrap();
        let get = |party: &str, id: &str, c: u16| {
            p.iter()
                .find(|x| x.party == party && x.party_id == id && x.currency == c)
                .unwrap()
                .clone()
        };
        let s1 = get("MERCHANT", "SHOP1", 860);
        assert_eq!(
            (s1.count, s1.gross_minor, s1.fee_minor, s1.net_minor),
            (2, 1_000_333, 15_005, 985_328)
        );
        let s2 = get("MERCHANT", "SHOP2", 860);
        assert_eq!((s2.fee_minor, s2.net_minor), (1_500, 98_500));
        let iss = get("ISSUER", ISSUER_PARTY, 860);
        assert_eq!(
            (iss.count, iss.gross_minor, iss.fee_minor),
            (3, 1_100_333, 11_003)
        );
        let acq = get("ACQUIRER", ACQUIRER_PARTY, 860);
        assert_eq!((acq.gross_minor, acq.net_minor), (16_505, 16_505 - 11_003));
        assert_eq!(iss.net_minor, s1.net_minor + s2.net_minor + acq.net_minor);
        // Boshqa valyuta alohida.
        let usd = get("ISSUER", ISSUER_PARTY, 840);
        assert_eq!((usd.count, usd.gross_minor, usd.fee_minor), (1, 2_500, 25));
        assert!(settle(&[], 150, 100).unwrap().is_empty());
    }

    #[test]
    fn batch_id_from_date() {
        assert_eq!(batch_id("2026-10-27"), "MPAY20261027");
        assert_eq!(
            yesterday(time::macros::datetime!(2026-10-27 05:00 UTC)),
            "2026-10-26"
        );
    }
}
