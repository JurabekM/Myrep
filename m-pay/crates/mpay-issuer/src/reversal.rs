//! Reversal (`0400`/`0401` → `0410`, ADR-0024) va solishtirish uchun avtorizatsiyalar hisoboti.
//!
//! Acquirer avtorizatsiya natijasini bilmasa (javob kelmadi, o'qib bo'lmadi, jarayon to'xtadi)
//! `0400` yuboradi; javob kelmasa — `0401` (takror). Emitent asl avtorizatsiyani
//! `(terminal, STAN, RRN, merchant)` bo'yicha topadi, summa va valyuta mos kelishi shart:
//!
//! * tasdiqlangan va hali qaytarilmagan — yechilgan summa o'sha hisobga qaytadi, `reversed_at`
//!   yoziladi (bitta tranzaksiyada; shartli `UPDATE` — ikki marta qaytarilmaydi) → `00 REVERSED`;
//! * avval qaytarilgan → `00 ALREADY_REVERSED`; rad etilgan asl → `00 NOTHING_TO_REVERSE`;
//! * topilmadi → `25` (emitent `0100` ni ko'rmagan — acquirer uchun yakuniy natija);
//! * bir nechta mos yozuv → `25 AMBIGUOUS_ORIGINAL` (avtomatik qaytarilmaydi, solishtirishda chiqadi);
//! * summa/valyuta mos emas → `13`; majburiy maydon yoki maydon 90 noto'g'ri → `30`;
//! * kliringdan o'tgan (ADR-0025) → `12 ALREADY_CLEARED` (yakuniy: faqat qaytarish/refund).
//!
//! Har reversal xabari `issuer_reversals` ga yoziladi. Maydon 2 (PAN) reversal'da yo'q — acquirer
//! karta raqamini saqlamaydi; asl yozuv RRN/STAN/terminal bo'yicha topiladi (M-Pay Test Scheme
//! profili; `TODO(spec):` haqiqiy sxemaning reversal formati).

use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_crypto::rng;
use serde::{Deserialize, Serialize};
use sqlx::Row;

use crate::codes::ReversalReason;
use crate::issuer::Issuer;
use crate::IssuerError;

/// Reversal natijasi (acquirer jurnali va log uchun; maxfiy ma'lumotsiz).
#[derive(Debug, Clone, Serialize)]
pub struct ReversalOutcome {
    pub reason: ReversalReason,
    /// Topilgan asl avtorizatsiya.
    pub auth_id: Option<String>,
    pub amount_minor: u64,
    pub currency: u16,
}

impl ReversalOutcome {
    /// Maydon 39.
    pub fn code(&self) -> &'static str {
        self.reason.code()
    }
}

/// Emitent qaydnomasidagi avtorizatsiya (solishtirish uchun; PAN yo'q, faqat maskalangan DPAN).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct IssuerRecord {
    pub ts: i64,
    pub stan: String,
    pub rrn: String,
    pub terminal_id: String,
    pub merchant_id: String,
    pub dpan_masked: Option<String>,
    pub amount_minor: i64,
    pub currency: u16,
    pub response_code: String,
    /// Reversal bilan qaytarilgan vaqt.
    pub reversed_at: Option<i64>,
}

struct ParsedReversal {
    stan: String,
    rrn: String,
    terminal_id: String,
    merchant_id: String,
    amount: u64,
    currency: u16,
}

fn parse(req: &IsoMessage) -> Option<ParsedReversal> {
    for f in [3u8, 4, 7, 11, 37, 41, 42, 49, 90] {
        req.require(f).ok()?;
    }
    let stan = req.require_str(11).ok()?.to_owned();
    // Maydon 90: asl MTI ‖ asl STAN ‖ … — faqat avtorizatsiyani va o'sha STAN'ni qaytarish mumkin.
    let orig = req.require_str(90).ok()?;
    if &orig[..4] != "0100" || orig[4..10] != stan {
        return None;
    }
    Some(ParsedReversal {
        stan,
        rrn: req.require_str(37).ok()?.to_owned(),
        terminal_id: req.require_str(41).ok()?.trim_end().to_owned(),
        merchant_id: req.require_str(42).ok()?.trim_end().to_owned(),
        amount: req.require_num(4).ok()?,
        currency: req.require_num(49).ok()? as u16,
    })
}

impl Issuer {
    /// Ikkilik ISO 8583 `0400`/`0401` → `0410`.
    pub async fn process_reversal_bytes(
        &self,
        request: &[u8],
    ) -> Result<(Vec<u8>, ReversalOutcome), IssuerError> {
        let msg = IsoMessage::unpack(request)?;
        let (resp, out) = self.reverse(&msg).await?;
        Ok((resp.pack(), out))
    }

    /// Reversal'ni qayta ishlaydi.
    pub async fn reverse(
        &self,
        req: &IsoMessage,
    ) -> Result<(IsoMessage, ReversalOutcome), IssuerError> {
        if req.mti != Mti::REVERSAL_REQUEST && req.mti != Mti::REVERSAL_REPEAT {
            return Err(IssuerError::Format("MTI 0400/0401 kutilgan"));
        }
        let mut resp = IsoMessage::new(Mti::REVERSAL_RESPONSE);
        for f in [3u8, 4, 7, 11, 37, 41, 42, 49, 90] {
            if let Some(v) = req.get(f) {
                resp.set(f, v.to_vec())?;
            }
        }
        let now = self.clock.unix();
        let p = parse(req);
        let mut tx = self.db.begin_write().await?;
        let out = match &p {
            None => ReversalOutcome {
                reason: ReversalReason::FormatError,
                auth_id: None,
                amount_minor: 0,
                currency: 0,
            },
            Some(p) => apply(&mut tx, p, now).await?,
        };
        let mti = std::str::from_utf8(&req.mti.0).unwrap_or("????");
        sqlx::query(
            "INSERT INTO issuer_reversals (reversal_id, ts, mti, auth_id, stan, rrn, terminal_id, \
             merchant_id, amount_minor, currency, response_code, reason) \
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)",
        )
        .bind(format!("rev_{}", hex::encode(rng::array::<8>()?)))
        .bind(now)
        .bind(mti)
        .bind(out.auth_id.as_deref())
        .bind(p.as_ref().map(|p| p.stan.as_str()).unwrap_or(""))
        .bind(p.as_ref().map(|p| p.rrn.as_str()).unwrap_or(""))
        .bind(p.as_ref().map(|p| p.terminal_id.as_str()).unwrap_or(""))
        .bind(p.as_ref().map(|p| p.merchant_id.as_str()).unwrap_or(""))
        .bind(out.amount_minor as i64)
        .bind(i64::from(out.currency))
        .bind(out.code())
        .bind(out.reason.as_str())
        .execute(&mut *tx)
        .await?;
        tx.commit().await?;
        resp.set_str(39, out.code())?;
        tracing::info!(
            mti,
            code = out.code(),
            reason = out.reason.as_str(),
            stan = ?p.as_ref().map(|p| p.stan.as_str()),
            rrn = ?p.as_ref().map(|p| p.rrn.as_str()),
            "issuer: reversal"
        );
        Ok((resp, out))
    }

    /// `[from, to)` oralig'idagi avtorizatsiyalar (yozilgan vaqt bo'yicha) — solishtirish uchun.
    pub async fn report(&self, from: i64, to: i64) -> Result<Vec<IssuerRecord>, IssuerError> {
        let rows = sqlx::query(
            "SELECT ts, stan, rrn, terminal_id, merchant_id, dpan_masked, amount_minor, currency, \
             response_code, reversed_at FROM issuer_authorizations \
             WHERE ts >= $1 AND ts < $2 ORDER BY ts, auth_id",
        )
        .bind(from)
        .bind(to)
        .fetch_all(self.db.pool())
        .await?;
        rows.iter()
            .map(|r| {
                Ok(IssuerRecord {
                    ts: r.try_get("ts")?,
                    stan: r.try_get("stan")?,
                    rrn: r.try_get("rrn")?,
                    terminal_id: r.try_get("terminal_id")?,
                    merchant_id: r.try_get("merchant_id")?,
                    dpan_masked: r.try_get("dpan_masked")?,
                    amount_minor: r.try_get("amount_minor")?,
                    currency: r.try_get::<i64, _>("currency")? as u16,
                    response_code: r.try_get("response_code")?,
                    reversed_at: r.try_get("reversed_at")?,
                })
            })
            .collect()
    }
}

async fn apply(
    tx: &mut sqlx::AnyConnection,
    p: &ParsedReversal,
    now: i64,
) -> Result<ReversalOutcome, IssuerError> {
    let mut out = ReversalOutcome {
        reason: ReversalReason::OriginalNotFound,
        auth_id: None,
        amount_minor: p.amount,
        currency: p.currency,
    };
    let rows = sqlx::query(
        "SELECT auth_id, amount_minor, currency, response_code, account_id, reversed_at, \
         cleared_batch FROM issuer_authorizations \
         WHERE rrn = $1 AND stan = $2 AND terminal_id = $3 AND merchant_id = $4 \
         ORDER BY ts, auth_id",
    )
    .bind(&p.rrn)
    .bind(&p.stan)
    .bind(&p.terminal_id)
    .bind(&p.merchant_id)
    .fetch_all(&mut *tx)
    .await?;
    let row = match rows.as_slice() {
        [] => return Ok(out),
        [r] => r,
        _ => {
            out.reason = ReversalReason::AmbiguousOriginal;
            return Ok(out);
        }
    };
    let auth_id: String = row.try_get("auth_id")?;
    out.auth_id = Some(auth_id.clone());
    let amount: i64 = row.try_get("amount_minor")?;
    let currency: i64 = row.try_get("currency")?;
    if amount != p.amount as i64 || currency != i64::from(p.currency) {
        out.reason = ReversalReason::AmountMismatch;
        return Ok(out);
    }
    if row.try_get::<Option<i64>, _>("reversed_at")?.is_some() {
        out.reason = ReversalReason::AlreadyReversed;
        return Ok(out);
    }
    if row.try_get::<Option<String>, _>("cleared_batch")?.is_some() {
        out.reason = ReversalReason::AlreadyCleared;
        return Ok(out);
    }
    if row.try_get::<String, _>("response_code")? != "00" {
        out.reason = ReversalReason::NothingToReverse;
        return Ok(out);
    }
    let Some(account_id) = row.try_get::<Option<String>, _>("account_id")? else {
        out.reason = ReversalReason::AccountUnknown;
        return Ok(out);
    };
    // Shartli belgi — parallel `0400`/`0401` dan faqat bittasi pulni qaytaradi.
    let marked = sqlx::query(
        "UPDATE issuer_authorizations SET reversed_at = $1 WHERE auth_id = $2 AND reversed_at IS NULL",
    )
    .bind(now)
    .bind(&auth_id)
    .execute(&mut *tx)
    .await?
    .rows_affected();
    if marked != 1 {
        out.reason = ReversalReason::AlreadyReversed;
        return Ok(out);
    }
    sqlx::query(
        "UPDATE issuer_accounts SET balance_minor = balance_minor + $1, updated_at = $2 \
         WHERE account_id = $3",
    )
    .bind(amount)
    .bind(now)
    .bind(&account_id)
    .execute(&mut *tx)
    .await?;
    out.reason = ReversalReason::Reversed;
    Ok(out)
}
