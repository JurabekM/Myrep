//! Karta (token) bo'yicha tranzaksiyalar tarixi — hamyon ilovasi uchun.
//!
//! Emitent qaydnomasidan (`issuer_authorizations`): yangilari birinchi — `ts`, bir soniya ichida
//! karta ATC'si (har tap'da o'sadi), so'ng `auth_id`; kursor shu uchlik bo'yicha (yozuvlar tushib
//! qolmaydi va takrorlanmaydi). Holat foydalanuvchi tilida:
//! `APPROVED` (tasdiqlangan va qaytarilmagan), `REVERSED` (reversal bilan qaytarilgan, ADR-0024),
//! `DECLINED` (rad). PAN yo'q — faqat summa, savdo nuqtasi, vaqt va kodlar.
//! `TODO(spec):` real bankda tarix emitentning o'z API'sidan (format kelishiladi).

use serde::{Deserialize, Serialize};
use sqlx::Row;

use crate::issuer::Issuer;
use crate::IssuerError;

/// Bitta tranzaksiya.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TokenTxn {
    /// Emitent yozuvi ID'si (barqaror).
    pub id: String,
    pub at: i64,
    pub amount_minor: i64,
    pub currency: u16,
    pub merchant_id: String,
    pub terminal_id: String,
    pub rrn: String,
    /// `APPROVED`, `REVERSED`, `DECLINED`.
    pub status: String,
    pub response_code: String,
    pub reason: String,
    /// Kliringdan o'tgan (yakuniy, ADR-0025).
    pub cleared: bool,
}

/// Sahifa.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct TokenTxnPage {
    pub transactions: Vec<TokenTxn>,
    /// Keyingi (eskiroq) sahifa uchun kursor; `None` — oxiri.
    pub next_cursor: Option<String>,
}

/// Kursor: `<ts>.<atc>.<auth_id>` — ochiq ma'lumot (vaqt, karta hisoblagichi, yozuv ID'si), sir emas.
/// ATC'siz yozuv (format xatosi) uchun `atc = -1`.
fn parse_cursor(c: &str) -> Option<(i64, i64, String)> {
    let mut it = c.splitn(3, '.');
    let (ts, atc, id) = (it.next()?, it.next()?, it.next()?);
    let ok =
        id.starts_with("ath_") && id.len() <= 40 && id[4..].bytes().all(|b| b.is_ascii_hexdigit());
    ok.then_some(())?;
    Some((ts.parse().ok()?, atc.parse().ok()?, id.to_owned()))
}

impl Issuer {
    /// `limit` (1–100) ta yozuv, `cursor` dan eskiroqlari.
    pub async fn token_history(
        &self,
        token_id: &str,
        cursor: Option<&str>,
        limit: u32,
    ) -> Result<TokenTxnPage, IssuerError> {
        // Birinchi sahifa: `ts < i64::MAX` — hammasi.
        let (ts, atc, id) = match cursor {
            Some(c) => parse_cursor(c).ok_or(IssuerError::Format("kursor"))?,
            None => (i64::MAX, 0, String::new()),
        };
        let limit = i64::from(limit.clamp(1, 100));
        // `auth_id`: `ath_` + hex — leksik tartib barqaror (ATC takrorlangan rad yozuvlari uchun).
        let rows = sqlx::query(
            "SELECT auth_id, ts, COALESCE(atc, -1) AS atc_k, rrn, merchant_id, terminal_id, \
             amount_minor, currency, response_code, reason, reversed_at, cleared_batch \
             FROM issuer_authorizations WHERE token_id = $1 AND (ts < $2 OR (ts = $3 AND \
             (COALESCE(atc, -1) < $4 OR (COALESCE(atc, -1) = $5 AND auth_id < $6)))) \
             ORDER BY ts DESC, atc_k DESC, auth_id DESC LIMIT $7",
        )
        .bind(token_id)
        .bind(ts)
        .bind(ts)
        .bind(atc)
        .bind(atc)
        .bind(&id)
        .bind(limit + 1)
        .fetch_all(self.db.pool())
        .await?;
        let more = rows.len() as i64 > limit;
        let mut transactions = Vec::with_capacity(rows.len());
        let mut last_atc = -1;
        for r in rows.iter().take(limit as usize) {
            last_atc = r.try_get("atc_k")?;
            let code: String = r.try_get("response_code")?;
            let reversed = r.try_get::<Option<i64>, _>("reversed_at")?.is_some();
            let status = match (code.as_str(), reversed) {
                ("00", false) => "APPROVED",
                ("00", true) => "REVERSED",
                _ => "DECLINED",
            };
            transactions.push(TokenTxn {
                id: r.try_get("auth_id")?,
                at: r.try_get("ts")?,
                amount_minor: r.try_get("amount_minor")?,
                currency: r.try_get::<i64, _>("currency")? as u16,
                merchant_id: r.try_get("merchant_id")?,
                terminal_id: r.try_get("terminal_id")?,
                rrn: r.try_get("rrn")?,
                status: status.into(),
                response_code: code,
                reason: r.try_get("reason")?,
                cleared: r.try_get::<Option<String>, _>("cleared_batch")?.is_some(),
            });
        }
        let next_cursor = more
            .then(|| {
                transactions
                    .last()
                    .map(|t| format!("{}.{last_atc}.{}", t.at, t.id))
            })
            .flatten();
        Ok(TokenTxnPage {
            transactions,
            next_cursor,
        })
    }
}

#[cfg(test)]
mod tests {
    use super::parse_cursor;

    #[test]
    fn cursor_is_strict() {
        assert_eq!(
            parse_cursor("1793041200.7.ath_00ff"),
            Some((1793041200, 7, "ath_00ff".into()))
        );
        assert_eq!(parse_cursor("5.-1.ath_0a"), Some((5, -1, "ath_0a".into())));
        for bad in [
            "",
            "123",
            "1.ath_00",
            "x.1.ath_00",
            "1.x.ath_00",
            "1.1.auth_00",
            "1.1.ath_zz",
            "1.1.ath_00' OR 1=1",
        ] {
            assert_eq!(parse_cursor(bad), None, "{bad}");
        }
    }
}
