//! Kliring faylini qabul qilish (ADR-0025): har yozuv asl avtorizatsiyaga moslanadi va paketga
//! bog'lanadi; natija — tasdiq (ack) fayli.
//!
//! Emulyator avtorizatsiyada pulni darhol yechadi (bitta xabarli model), shuning uchun kliring
//! balansni o'zgartirmaydi — u tranzaksiyani **yakuniy** qiladi va hisob-kitobga (settlement)
//! asos bo'ladi. `TODO(spec):` haqiqiy sxemada avtorizatsiya — blok (hold), kliring — yechim (post).
//!
//! | Holat | Kod | Sabab |
//! |---|---|---|
//! | tasdiqlangan, qaytarilmagan, kliringga kirmagan | `00` | `ACCEPTED` |
//! | topilmadi / bir nechta mos | `25` | `ORIGINAL_NOT_FOUND` / `AMBIGUOUS_ORIGINAL` |
//! | summa yoki valyuta farqli | `13` | `AMOUNT_MISMATCH` |
//! | asl rad etilgan / qaytarilgan (reversal) | `12` | `NOT_APPROVED` / `REVERSED` |
//! | boshqa paketda kliringdan o'tgan | `94` | `ALREADY_CLEARED` |
//!
//! Bir paket ID — bitta natija: o'sha fayl qayta kelsa saqlangan tasdiq qaytadi; o'sha ID boshqa
//! mazmun bilan — xato (paket butunlay rad etiladi).

use mpay_common::clearing::{AckRecord, ClearingAck, ClearingFile, ClearingRecord};
use sha2::{Digest, Sha256};
use sqlx::Row;

use crate::issuer::Issuer;
use crate::IssuerError;

/// Bitta yozuv natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum Outcome {
    Accepted,
    NotFound,
    Ambiguous,
    AmountMismatch,
    NotApproved,
    Reversed,
    AlreadyCleared,
}

impl Outcome {
    fn code(self) -> &'static str {
        match self {
            Self::Accepted => "00",
            Self::NotFound | Self::Ambiguous => "25",
            Self::AmountMismatch => "13",
            Self::NotApproved | Self::Reversed => "12",
            Self::AlreadyCleared => "94",
        }
    }

    fn reason(self) -> &'static str {
        match self {
            Self::Accepted => "ACCEPTED",
            Self::NotFound => "ORIGINAL_NOT_FOUND",
            Self::Ambiguous => "AMBIGUOUS_ORIGINAL",
            Self::AmountMismatch => "AMOUNT_MISMATCH",
            Self::NotApproved => "NOT_APPROVED",
            Self::Reversed => "REVERSED",
            Self::AlreadyCleared => "ALREADY_CLEARED",
        }
    }
}

impl Issuer {
    /// Kliring fayli → tasdiq (ack) fayli.
    pub async fn process_clearing(
        &self,
        file: &[u8],
    ) -> Result<(Vec<u8>, ClearingAck), IssuerError> {
        let f = ClearingFile::parse(file)?;
        let sha = hex::encode(Sha256::digest(file));
        let mut tx = self.db.begin_write().await?;
        if let Some(r) =
            sqlx::query("SELECT file_sha256, ack FROM issuer_clearing_batches WHERE batch_id = $1")
                .bind(&f.batch_id)
                .fetch_optional(&mut *tx)
                .await?
        {
            if r.try_get::<String, _>("file_sha256")? != sha {
                return Err(IssuerError::Format(
                    "kliring paketi ID'si boshqa mazmun bilan",
                ));
            }
            let ack: String = r.try_get("ack")?;
            let parsed = ClearingAck::parse(ack.as_bytes())?;
            return Ok((ack.into_bytes(), parsed));
        }
        let mut records = Vec::with_capacity(f.records.len());
        for rec in &f.records {
            let o = clear_one(&mut tx, rec, &f.batch_id).await?;
            records.push(AckRecord {
                seq: rec.seq,
                code: o.code().into(),
                reason: o.reason().into(),
            });
        }
        let now = self.clock.unix();
        let ack = ClearingAck {
            batch_id: f.batch_id.clone(),
            received_at: now,
            records,
        };
        let bytes = ack.encode()?;
        let text = String::from_utf8(bytes.clone()).map_err(|_| IssuerError::Format("ack"))?;
        sqlx::query(
            "INSERT INTO issuer_clearing_batches (batch_id, business_date, file_sha256, received_at, \
             records, accepted, ack) VALUES ($1, $2, $3, $4, $5, $6, $7)",
        )
        .bind(&f.batch_id)
        .bind(&f.business_date)
        .bind(&sha)
        .bind(now)
        .bind(f.records.len() as i64)
        .bind(ack.accepted() as i64)
        .bind(text)
        .execute(&mut *tx)
        .await?;
        tx.commit().await?;
        tracing::info!(
            batch = %f.batch_id,
            records = f.records.len(),
            accepted = ack.accepted(),
            "issuer: kliring paketi"
        );
        Ok((bytes, ack))
    }
}

async fn clear_one(
    tx: &mut sqlx::AnyConnection,
    r: &ClearingRecord,
    batch: &str,
) -> Result<Outcome, IssuerError> {
    let rows = sqlx::query(
        "SELECT auth_id, amount_minor, currency, response_code, reversed_at, cleared_batch \
         FROM issuer_authorizations \
         WHERE rrn = $1 AND stan = $2 AND terminal_id = $3 AND merchant_id = $4",
    )
    .bind(&r.rrn)
    .bind(format!("{:06}", r.stan))
    .bind(&r.terminal_id)
    .bind(&r.merchant_id)
    .fetch_all(&mut *tx)
    .await?;
    let row = match rows.as_slice() {
        [] => return Ok(Outcome::NotFound),
        [row] => row,
        _ => return Ok(Outcome::Ambiguous),
    };
    if row.try_get::<i64, _>("amount_minor")? != r.amount_minor as i64
        || row.try_get::<i64, _>("currency")? != i64::from(r.currency)
    {
        return Ok(Outcome::AmountMismatch);
    }
    if row.try_get::<String, _>("response_code")? != "00" {
        return Ok(Outcome::NotApproved);
    }
    if row.try_get::<Option<i64>, _>("reversed_at")?.is_some() {
        return Ok(Outcome::Reversed);
    }
    if row.try_get::<Option<String>, _>("cleared_batch")?.is_some() {
        return Ok(Outcome::AlreadyCleared);
    }
    let n = sqlx::query(
        "UPDATE issuer_authorizations SET cleared_batch = $1 \
         WHERE auth_id = $2 AND cleared_batch IS NULL AND reversed_at IS NULL",
    )
    .bind(batch)
    .bind(row.try_get::<String, _>("auth_id")?)
    .execute(&mut *tx)
    .await?
    .rows_affected();
    Ok(if n == 1 {
        Outcome::Accepted
    } else {
        Outcome::AlreadyCleared
    })
}
