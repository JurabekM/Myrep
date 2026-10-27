//! Avtomatik reversal (`0400`/`0401`, ADR-0024): natijasi noma'lum avtorizatsiyalarni bekor qilish.
//!
//! Natija noma'lum bo'ladigan uch holat — emitent pul yechgan bo'lishi mumkin, terminal esa `96`
//! ko'radi:
//!
//! * `ISSUER_TIMEOUT` — emitent `[acquirer] issuer_timeout_ms` ichida javob bermadi;
//! * `ISSUER_RESPONSE_UNREADABLE` — `0110` ni o'qib bo'lmadi;
//! * `OUTCOME_UNKNOWN` — jarayon so'rov o'rtasida to'xtagan (yozuv `STALE_PENDING_SECS` dan uzoq
//!   `PENDING`); terminal qayta yuborganda yoki ishchining navbatdagi aylanishida aniqlanadi.
//!
//! Har holatda bitta tranzaksiyada: takroriy so'rov yozuvi `96` bilan yopiladi (qayta yuborish ATC
//! replay bo'lardi) va `acquirer_reversals` ga navbat yozuvi qo'shiladi (kalit — takroriy so'rov
//! kaliti, ikkinchi marta qo'shilmaydi). Ishchi navbatni har instansiyada o'qiydi; yozuv shartli
//! `UPDATE` bilan band qilinadi, shuning uchun bitta reversal'ni bir vaqtda ikki instansiya
//! yubormaydi. Birinchi xabar `0400`, keyingilari `0401`. Emitent javobi:
//!
//! * `00` (qaytarildi, avval qaytarilgan yoki rad etilgan edi) va `25` (emitent `0100` ni ko'rmagan)
//!   → `DONE`;
//! * boshqa kod → `FAILED` — avtomatik hal bo'lmaydi, qo'lda ko'rib chiqiladi
//!   (`mpay_reversals{state="failed"}`, solishtirish hisoboti);
//! * emitentga yetib bo'lmadi yoki javob yo'q → eksponensial kutish bilan qayta urinish
//!   (`[acquirer] reversal_max_backoff_secs` gacha), muddatsiz.
//!
//! Navbat yozuvida PAN yo'q: `0400` asl yozuvni RRN, STAN va terminal bo'yicha ko'rsatadi
//! (maydon 90 — asl MTI, STAN va uzatish vaqti).

use std::sync::Arc;
use std::time::Duration;

use mpay_common::api::AuthorizationResponse;
use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_vault::db::Db;
use sqlx::Row;

use crate::config::AcquirerConfig;
use crate::state::AppState;

/// Emitent javob bermadi.
pub const CAUSE_TIMEOUT: &str = "ISSUER_TIMEOUT";
/// `0110` ni o'qib bo'lmadi.
pub const CAUSE_UNREADABLE: &str = "ISSUER_RESPONSE_UNREADABLE";
/// Ishlov tugamagan (jarayon to'xtagan).
pub const CAUSE_UNKNOWN: &str = "OUTCOME_UNKNOWN";

/// Yakunlangan reversal'lar saqlanish muddati (solishtirish va tekshiruv uchun).
const DONE_RETENTION_SECS: i64 = 35 * 24 * 3600;
/// Bitta aylanishda ko'rib chiqiladigan yozuvlar.
const BATCH: i64 = 32;

/// Takroriy so'rov kaliti (`acquirer_requests` va `acquirer_reversals` uchun umumiy).
#[derive(Debug, Clone)]
pub struct RowKey {
    pub terminal_id: String,
    pub stan: i64,
    pub txn_date: String,
}

impl From<&crate::dedup::RequestKey> for RowKey {
    fn from(k: &crate::dedup::RequestKey) -> Self {
        Self {
            terminal_id: k.terminal_id.clone(),
            stan: i64::from(k.stan),
            txn_date: k.txn_date.clone(),
        }
    }
}

fn unknown_response(
    stan: i64,
    dpan_masked: String,
    amount: i64,
    currency: i64,
    cause: &str,
) -> AuthorizationResponse {
    AuthorizationResponse {
        approved: false,
        response_code: "96".into(),
        reason: cause.into(),
        stan: stan as u32,
        rrn: String::new(),
        dpan_masked,
        amount_minor: amount.max(0) as u64,
        currency: currency as u16,
        issuer_auth_data: None,
        risk_score: None,
    }
}

/// Natijasi noma'lum yozuvni `96` bilan yopadi va reversal'ni navbatga qo'yadi (bitta tranzaksiyada).
/// Yozuv allaqachon yopilgan bo'lsa (parallel ishchi yoki qayta yuborish) — saqlangan javob.
pub async fn settle_unknown(
    db: &Db,
    k: &RowKey,
    cause: &str,
    cfg: &AcquirerConfig,
    now: i64,
) -> Result<AuthorizationResponse, sqlx::Error> {
    let mut tx = db.begin_write().await?;
    let row = sqlx::query(
        "SELECT state, response, terminal_ref, merchant_id, rrn, transmitted, amount_minor, \
         currency, dpan_masked FROM acquirer_requests \
         WHERE terminal_id = $1 AND stan = $2 AND txn_date = $3",
    )
    .bind(&k.terminal_id)
    .bind(k.stan)
    .bind(&k.txn_date)
    .fetch_optional(&mut *tx)
    .await?
    .ok_or(sqlx::Error::RowNotFound)?;
    let state: String = row.try_get("state")?;
    if let ("DONE", Some(json)) = (
        state.as_str(),
        row.try_get::<Option<String>, _>("response")?,
    ) {
        return serde_json::from_str(&json).map_err(|e| sqlx::Error::Decode(Box::new(e)));
    }
    let rrn: Option<String> = row.try_get("rrn")?;
    let amount: i64 = row.try_get::<Option<i64>, _>("amount_minor")?.unwrap_or(0);
    let currency: i64 = row.try_get::<Option<i64>, _>("currency")?.unwrap_or(0);
    let dpan: String = row
        .try_get::<Option<String>, _>("dpan_masked")?
        .unwrap_or_default();
    let resp = unknown_response(k.stan, dpan.clone(), amount, currency, cause);
    match rrn {
        Some(rrn) => {
            sqlx::query(
                "INSERT INTO acquirer_reversals (terminal_id, stan, txn_date, terminal_ref, merchant_id, \
                 rrn, transmitted, amount_minor, currency, dpan_masked, cause, state, attempts, \
                 next_attempt_at, created_at, updated_at) \
                 VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, 'PENDING', 0, $12, $13, $14) \
                 ON CONFLICT DO NOTHING",
            )
            .bind(&k.terminal_id)
            .bind(k.stan)
            .bind(&k.txn_date)
            .bind(row.try_get::<Option<String>, _>("terminal_ref")?.unwrap_or_default())
            .bind(row.try_get::<Option<String>, _>("merchant_id")?.unwrap_or_default())
            .bind(&rrn)
            .bind(row.try_get::<Option<String>, _>("transmitted")?.unwrap_or_default())
            .bind(amount)
            .bind(currency)
            .bind(&dpan)
            .bind(cause)
            .bind(now + cfg.reversal_delay_secs)
            .bind(now)
            .bind(now)
            .execute(&mut *tx)
            .await?;
            crate::metrics::reversal_enqueued(cause);
            tracing::warn!(stan = k.stan, rrn = %rrn, dpan = %dpan, cause, "acquirer: natija noma'lum — 96, reversal navbatda");
        }
        // Jurnal ustunlari qo'shilishidan oldingi yozuv — reversal uchun ma'lumot yo'q.
        None => {
            tracing::error!(
                stan = k.stan,
                cause,
                "acquirer: natija noma'lum, reversal uchun jurnal yo'q — solishtirishda tekshiring"
            );
        }
    }
    let json = serde_json::to_string(&resp).map_err(|e| sqlx::Error::Encode(Box::new(e)))?;
    sqlx::query(
        "UPDATE acquirer_requests SET state = 'DONE', response = $1, response_code = '96' \
         WHERE terminal_id = $2 AND stan = $3 AND txn_date = $4 AND state = 'PENDING'",
    )
    .bind(json)
    .bind(&k.terminal_id)
    .bind(k.stan)
    .bind(&k.txn_date)
    .execute(&mut *tx)
    .await?;
    tx.commit().await?;
    Ok(resp)
}

/// Qotib qolgan `PENDING` yozuvlarni (jarayon to'xtagan, terminal qayta yubormagan) yopadi.
pub async fn sweep_stale(db: &Db, cfg: &AcquirerConfig, now: i64) -> Result<usize, sqlx::Error> {
    let rows = sqlx::query(
        "SELECT terminal_id, stan, txn_date FROM acquirer_requests \
         WHERE state = 'PENDING' AND created_at < $1 ORDER BY created_at, terminal_id, stan LIMIT $2",
    )
    .bind(now - crate::dedup::STALE_PENDING_SECS)
    .bind(BATCH)
    .fetch_all(db.pool())
    .await?;
    for r in &rows {
        let k = RowKey {
            terminal_id: r.try_get("terminal_id")?,
            stan: r.try_get("stan")?,
            txn_date: r.try_get("txn_date")?,
        };
        settle_unknown(db, &k, CAUSE_UNKNOWN, cfg, now).await?;
    }
    Ok(rows.len())
}

/// Navbatdagi yozuv.
struct Due {
    key: RowKey,
    terminal_ref: String,
    merchant_id: String,
    rrn: String,
    transmitted: String,
    amount: i64,
    currency: i64,
    attempts: i64,
}

/// `0400` (birinchi urinish) yoki `0401` (takror).
fn build_0400(d: &Due, now: time::OffsetDateTime) -> Result<IsoMessage, String> {
    let iso = |e: mpay_common::iso8583::Iso8583Error| e.to_string();
    let mti = if d.attempts == 0 {
        Mti::REVERSAL_REQUEST
    } else {
        Mti::REVERSAL_REPEAT
    };
    let mut m = IsoMessage::new(mti);
    m.set_str(3, "000000").map_err(iso)?;
    m.set_num(4, d.amount.max(0) as u64).map_err(iso)?;
    m.set_str(7, &crate::acquirer::transmission_time(now))
        .map_err(iso)?;
    m.set_num(11, d.key.stan.max(0) as u64).map_err(iso)?;
    m.set_str(37, &d.rrn).map_err(iso)?;
    m.set_str(41, &format!("{:<8}", d.terminal_ref))
        .map_err(iso)?;
    m.set_str(42, &format!("{:<15}", d.merchant_id))
        .map_err(iso)?;
    m.set_num(49, d.currency.max(0) as u64).map_err(iso)?;
    // Asl ma'lumot: MTI ‖ STAN ‖ maydon 7 ‖ acquirer va forwarding ID (sandbox'da nol).
    // `TODO(spec):` haqiqiy sxemada muassasa identifikatorlari.
    m.set_str(
        90,
        &format!(
            "0100{:06}{:0>10}{:011}{:011}",
            d.key.stan, d.transmitted, 0, 0
        ),
    )
    .map_err(iso)?;
    Ok(m)
}

/// Qayta urinish oralig'i: 5 s, 10 s, 20 s … `max` gacha.
pub fn backoff_secs(attempts: i64, max: i64) -> i64 {
    let shift = attempts.clamp(1, 20) - 1;
    (5_i64 << shift).min(max)
}

/// Bir aylanish natijasi.
#[derive(Debug, Default, Clone, Copy, PartialEq, Eq)]
pub struct RunStats {
    pub done: usize,
    pub failed: usize,
    pub retry: usize,
}

/// Vaqti kelgan reversal'larni emitentga yuboradi.
pub async fn run_due(state: &AppState, now: i64) -> Result<RunStats, sqlx::Error> {
    let db = state.vault.db();
    let cfg = &state.acquirer;
    let rows = sqlx::query(
        "SELECT terminal_id, stan, txn_date, terminal_ref, merchant_id, rrn, transmitted, \
         amount_minor, currency, attempts, next_attempt_at FROM acquirer_reversals \
         WHERE state = 'PENDING' AND next_attempt_at <= $1 \
         ORDER BY next_attempt_at, terminal_id, stan LIMIT $2",
    )
    .bind(now)
    .bind(BATCH)
    .fetch_all(db.pool())
    .await?;
    let timeout = Duration::from_millis(cfg.issuer_timeout_ms);
    let mut stats = RunStats::default();
    for r in &rows {
        let d = Due {
            key: RowKey {
                terminal_id: r.try_get("terminal_id")?,
                stan: r.try_get("stan")?,
                txn_date: r.try_get("txn_date")?,
            },
            terminal_ref: r.try_get("terminal_ref")?,
            merchant_id: r.try_get("merchant_id")?,
            rrn: r.try_get("rrn")?,
            transmitted: r.try_get("transmitted")?,
            amount: r.try_get("amount_minor")?,
            currency: r.try_get("currency")?,
            attempts: r.try_get("attempts")?,
        };
        let attempts = d.attempts + 1;
        // Band qilish: boshqa instansiya shu yozuvni olgan bo'lsa `attempts` o'zgargan.
        let lease = now + cfg.issuer_timeout_ms.div_ceil(1000) as i64 + 60;
        let claimed = sqlx::query(
            "UPDATE acquirer_reversals SET attempts = $1, next_attempt_at = $2, updated_at = $3 \
             WHERE terminal_id = $4 AND stan = $5 AND txn_date = $6 AND state = 'PENDING' AND attempts = $7",
        )
        .bind(attempts)
        .bind(lease)
        .bind(now)
        .bind(&d.key.terminal_id)
        .bind(d.key.stan)
        .bind(&d.key.txn_date)
        .bind(d.attempts)
        .execute(db.pool())
        .await?
        .rows_affected();
        if claimed != 1 {
            continue;
        }
        let msg = match build_0400(&d, state.clock.now()) {
            Ok(m) => m,
            Err(e) => {
                tracing::error!(error = %e, stan = d.key.stan, "reversal: 0400 yig'ib bo'lmadi");
                finish(db, &d.key, "FAILED", None, "BUILD_ERROR", now).await?;
                crate::metrics::reversal_result("failed");
                stats.failed += 1;
                continue;
            }
        };
        let sent =
            tokio::time::timeout(timeout, state.issuer.process_reversal_bytes(&msg.pack())).await;
        let outcome = match sent {
            Ok(Ok((bytes, out))) => IsoMessage::unpack(&bytes)
                .ok()
                .filter(|m| m.mti == Mti::REVERSAL_RESPONSE)
                .and_then(|m| m.require_str(39).ok().map(str::to_owned))
                .map(|code| (code, out.reason.as_str())),
            Ok(Err(e)) => {
                tracing::warn!(error = %e, stan = d.key.stan, attempts, "reversal: emitent qayta ishlay olmadi");
                None
            }
            Err(_) => {
                tracing::warn!(
                    stan = d.key.stan,
                    attempts,
                    "reversal: emitent javob bermadi"
                );
                None
            }
        };
        match outcome {
            Some((code, reason)) => {
                let done = code == "00" || code == "25";
                finish(
                    db,
                    &d.key,
                    if done { "DONE" } else { "FAILED" },
                    Some(&code),
                    reason,
                    now,
                )
                .await?;
                if done {
                    stats.done += 1;
                    crate::metrics::reversal_result("done");
                    tracing::info!(stan = d.key.stan, rrn = %d.rrn, code = %code, reason, attempts, "reversal: yakunlandi");
                } else {
                    stats.failed += 1;
                    crate::metrics::reversal_result("failed");
                    tracing::error!(stan = d.key.stan, rrn = %d.rrn, code = %code, reason, "reversal: emitent rad etdi — qo'lda ko'rib chiqish");
                }
            }
            None => {
                stats.retry += 1;
                crate::metrics::reversal_result("retry");
                sqlx::query(
                    "UPDATE acquirer_reversals SET next_attempt_at = $1, updated_at = $2 \
                     WHERE terminal_id = $3 AND stan = $4 AND txn_date = $5 AND state = 'PENDING'",
                )
                .bind(now + backoff_secs(attempts, cfg.reversal_max_backoff_secs))
                .bind(now)
                .bind(&d.key.terminal_id)
                .bind(d.key.stan)
                .bind(&d.key.txn_date)
                .execute(db.pool())
                .await?;
            }
        }
    }
    Ok(stats)
}

async fn finish(
    db: &Db,
    k: &RowKey,
    state: &str,
    code: Option<&str>,
    result: &str,
    now: i64,
) -> Result<(), sqlx::Error> {
    sqlx::query(
        "UPDATE acquirer_reversals SET state = $1, response_code = $2, result = $3, updated_at = $4 \
         WHERE terminal_id = $5 AND stan = $6 AND txn_date = $7",
    )
    .bind(state)
    .bind(code)
    .bind(result)
    .bind(now)
    .bind(&k.terminal_id)
    .bind(k.stan)
    .bind(&k.txn_date)
    .execute(db.pool())
    .await?;
    Ok(())
}

/// Navbat holati (metrikalar uchun): `PENDING` soni, `FAILED` soni, eng eski `PENDING` yoshi (s).
pub async fn queue_stats(db: &Db, now: i64) -> Result<(i64, i64, i64), sqlx::Error> {
    let r = sqlx::query(
        "SELECT \
         COALESCE(SUM(CASE WHEN state = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending, \
         COALESCE(SUM(CASE WHEN state = 'FAILED' THEN 1 ELSE 0 END), 0) AS failed, \
         MIN(CASE WHEN state = 'PENDING' THEN created_at END) AS oldest \
         FROM acquirer_reversals WHERE state <> 'DONE'",
    )
    .fetch_one(db.pool())
    .await?;
    let pending: i64 = r.try_get("pending")?;
    let failed: i64 = r.try_get("failed")?;
    let oldest: Option<i64> = r.try_get("oldest")?;
    Ok((pending, failed, oldest.map_or(0, |t| (now - t).max(0))))
}

/// Fon ishchisi: qotgan `PENDING` lar → navbat → emitent; eski `DONE` yozuvlarni tozalaydi.
pub fn spawn_worker(state: Arc<AppState>) -> tokio::task::AbortHandle {
    tokio::spawn(async move {
        let mut t =
            tokio::time::interval(Duration::from_millis(state.acquirer.reversal_interval_ms));
        t.set_missed_tick_behavior(tokio::time::MissedTickBehavior::Delay);
        let mut last_cleanup = 0_i64;
        loop {
            t.tick().await;
            let now = state.clock.unix();
            let db = state.vault.db();
            if let Err(e) = sweep_stale(db, &state.acquirer, now).await {
                tracing::error!(error = %e, "reversal: qotgan yozuvlarni yopib bo'lmadi");
            }
            if let Err(e) = run_due(&state, now).await {
                tracing::error!(error = %e, "reversal: navbat");
            }
            if now - last_cleanup >= 3600 {
                last_cleanup = now;
                if let Err(e) = sqlx::query(
                    "DELETE FROM acquirer_reversals WHERE state = 'DONE' AND created_at < $1",
                )
                .bind(now - DONE_RETENTION_SECS)
                .execute(db.pool())
                .await
                {
                    tracing::warn!(error = %e, "reversal: eski yozuvlar");
                }
            }
        }
    })
    .abort_handle()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn backoff_grows_and_is_capped() {
        assert_eq!(backoff_secs(1, 600), 5);
        assert_eq!(backoff_secs(2, 600), 10);
        assert_eq!(backoff_secs(4, 600), 40);
        assert_eq!(backoff_secs(8, 600), 600);
        assert_eq!(backoff_secs(1_000, 600), 600);
        assert_eq!(backoff_secs(0, 600), 5);
    }

    #[test]
    fn first_attempt_is_0400_then_0401_with_original_data() {
        let mut d = Due {
            key: RowKey {
                terminal_id: "terminal-1/TERM0001".into(),
                stan: 42,
                txn_date: "261027".into(),
            },
            terminal_ref: "TERM0001".into(),
            merchant_id: "SHOP0000000001".into(),
            rrn: "630014000042".into(),
            transmitted: "1027140501".into(),
            amount: 12_500,
            currency: 860,
            attempts: 0,
        };
        let now = time::macros::datetime!(2026-10-27 14:06:00 UTC);
        let m = build_0400(&d, now).unwrap();
        assert_eq!(m.mti, Mti::REVERSAL_REQUEST);
        assert_eq!(m.require_str(11).unwrap(), "000042");
        assert_eq!(m.require_str(7).unwrap(), "1027140600");
        assert_eq!(m.require_str(41).unwrap(), "TERM0001");
        assert_eq!(m.require_str(42).unwrap(), "SHOP0000000001 ");
        assert_eq!(
            m.require_str(90).unwrap(),
            format!("01000000421027140501{:022}", 0)
        );
        assert!(m.get(2).is_none(), "reversal'da PAN yo'q");
        d.attempts = 1;
        assert_eq!(build_0400(&d, now).unwrap().mti, Mti::REVERSAL_REPEAT);
    }
}
