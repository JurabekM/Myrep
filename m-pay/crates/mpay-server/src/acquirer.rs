//! Acquirer shlyuzi roli: terminal JSON so'rovi → ISO 8583 `0100` (ikkilik) → emitent →
//! `0110` → terminal JSON javobi. Paketlash/ochish har doim haqiqiy baytlar orqali o'tadi.

use mpay_common::api::{AuthorizationRequest, AuthorizationResponse};
use mpay_common::emv::{self, tag, Track2};
use mpay_common::iso8583::{IsoMessage, Mti};
use mpay_common::tlv::{self, Tlv};
use mpay_common::PanKind;
use time::OffsetDateTime;

use crate::error::ApiError;

/// Maydon 55 ga o'tadigan teglar (EMV odatiy to'plami, M-Pay Test Scheme).
const FIELD55_TAGS: &[u32] = &[
    tag::ARQC,
    tag::CID,
    tag::IAD,
    tag::UN,
    tag::ATC,
    tag::TVR,
    tag::TXN_DATE,
    tag::TXN_TYPE,
    tag::AMOUNT,
    tag::CURRENCY,
    tag::AIP,
    tag::TERMINAL_COUNTRY,
    tag::AMOUNT_OTHER,
];

const MAX_ICC_LEN: usize = 1024;

fn ans_field(v: &str, len: usize, name: &str) -> Result<String, ApiError> {
    if v.is_empty() || v.len() > len || !v.bytes().all(|b| (0x21..=0x7E).contains(&b)) {
        return Err(ApiError::bad_request(format!(
            "{name}: 1–{len} ta bosiladigan ASCII belgi"
        )));
    }
    Ok(format!("{v:<len$}"))
}

/// Yig'ilgan `0100` va javob uchun kontekst.
#[derive(Debug)]
pub struct Built {
    pub msg: IsoMessage,
    pub rrn: String,
    pub dpan_masked: String,
    pub amount_minor: u64,
    pub currency: u16,
    /// Tranzaksiya sanasi `YYMMDD` — kartadan (ICC `9A`), bo'lmasa server sanasi. Takroriy so'rov
    /// kaliti uchun: qayta urinish yarim tundan o'tsa ham o'zgarmaydi.
    pub txn_date: String,
}

/// Terminal so'rovidan `0100` yig'adi.
pub fn build_0100(req: &AuthorizationRequest, now: OffsetDateTime) -> Result<Built, ApiError> {
    if req.stan > 999_999 {
        return Err(ApiError::bad_request("stan 0–999999"));
    }
    let tid = ans_field(&req.terminal_id, 8, "terminal_id")?;
    let mid = ans_field(&req.merchant_id, 15, "merchant_id")?;
    let raw = hex::decode(&req.icc_data).map_err(|_| ApiError::bad_request("icc_data hex emas"))?;
    if raw.len() > MAX_ICC_LEN {
        return Err(ApiError::bad_request("icc_data juda katta"));
    }
    let icc = tlv::parse_all(&raw).map_err(|_| ApiError::bad_request("icc_data BER-TLV emas"))?;
    let t2 = Track2::from_emv(
        tlv::require(&icc, tag::TRACK2).map_err(|_| ApiError::bad_request("Track 2 (57) yo'q"))?,
    )
    .map_err(|_| ApiError::bad_request("Track 2 noto'g'ri"))?;
    if t2.pan.kind() != PanKind::Device {
        return Err(ApiError::bad_request("Track 2 da DPAN kutilgan"));
    }
    let amount = tlv::require(&icc, tag::AMOUNT)
        .ok()
        .and_then(|b| emv::from_bcd(b).ok())
        .ok_or_else(|| ApiError::bad_request("summa (9F02) yo'q"))?;
    let currency = tlv::require(&icc, tag::CURRENCY)
        .ok()
        .and_then(|b| emv::from_bcd(b).ok())
        .ok_or_else(|| ApiError::bad_request("valyuta (5F2A) yo'q"))? as u16;

    let txn_date = tlv::require(&icc, tag::TXN_DATE)
        .ok()
        .filter(|d| d.len() == 3)
        .map(hex::encode)
        .unwrap_or_else(|| crate::dedup::server_date(now));

    let field55: Vec<Tlv> = FIELD55_TAGS
        .iter()
        .filter_map(|t| tlv::find(&icc, *t).cloned())
        .collect();
    let rrn = format!(
        "{}{:03}{:02}{:06}",
        now.year() % 10,
        now.ordinal(),
        now.hour(),
        req.stan
    );
    let mut m = IsoMessage::new(Mti::AUTH_REQUEST);
    let iso = |e: mpay_common::iso8583::Iso8583Error| ApiError::bad_request(e.to_string());
    m.set_str(2, t2.pan.expose_digits()).map_err(iso)?;
    m.set_str(3, "000000").map_err(iso)?;
    m.set_num(4, amount).map_err(iso)?;
    m.set_str(
        7,
        &format!(
            "{:02}{:02}{:02}{:02}{:02}",
            now.month() as u8,
            now.day(),
            now.hour(),
            now.minute(),
            now.second()
        ),
    )
    .map_err(iso)?;
    m.set_num(11, u64::from(req.stan)).map_err(iso)?;
    m.set_str(14, &t2.expiry.to_yymm()).map_err(iso)?;
    m.set_str(22, "071").map_err(iso)?;
    m.set_str(35, &t2.to_iso()).map_err(iso)?;
    m.set_str(37, &rrn).map_err(iso)?;
    m.set_str(41, &tid).map_err(iso)?;
    m.set_str(42, &mid).map_err(iso)?;
    m.set_num(49, u64::from(currency)).map_err(iso)?;
    m.set(55, tlv::encode_all(&field55)).map_err(iso)?;
    Ok(Built {
        msg: m,
        rrn,
        dpan_masked: t2.pan.masked(),
        amount_minor: amount,
        currency,
        txn_date,
    })
}

/// `0110` dan terminal javobi.
pub fn parse_0110(
    resp: &[u8],
    built: &Built,
    stan: u32,
    reason: &str,
    risk_score: Option<u16>,
) -> Result<AuthorizationResponse, ApiError> {
    let m = IsoMessage::unpack(resp).map_err(|e| {
        ApiError::new(
            axum::http::StatusCode::BAD_GATEWAY,
            "ISSUER_FORMAT",
            e.to_string(),
        )
    })?;
    if m.mti != Mti::AUTH_RESPONSE {
        return Err(ApiError::new(
            axum::http::StatusCode::BAD_GATEWAY,
            "ISSUER_FORMAT",
            "0110 kutilgan",
        ));
    }
    let code = m
        .require_str(39)
        .map_err(|e| {
            ApiError::new(
                axum::http::StatusCode::BAD_GATEWAY,
                "ISSUER_FORMAT",
                e.to_string(),
            )
        })?
        .to_owned();
    let iad = m
        .get(55)
        .and_then(|b| tlv::parse_all(b).ok())
        .and_then(|l| {
            tlv::require(&l, tag::ISSUER_AUTH_DATA)
                .ok()
                .map(hex::encode_upper)
        });
    Ok(AuthorizationResponse {
        approved: code == "00",
        response_code: code,
        reason: reason.to_owned(),
        stan,
        rrn: built.rrn.clone(),
        dpan_masked: built.dpan_masked.clone(),
        amount_minor: built.amount_minor,
        currency: built.currency,
        issuer_auth_data: iad,
        risk_score,
    })
}
