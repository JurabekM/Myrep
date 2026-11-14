//! Dasturiy terminal yadrosi: PPSE → AID → GPO va avtorizatsiya uchun ICC ma'lumoti.

use mpay_common::emv::{self, tag, EmvDate, TerminalData, Track2};
use mpay_common::tlv::{self, Tlv};
use mpay_crypto::rng;
use thiserror::Error;

use crate::apdu::{sw, ApduTransport, Command, Response, TransportError};

/// Terminal xatolari.
#[derive(Debug, Error, Clone, PartialEq, Eq)]
pub enum TerminalError {
    #[error("transport: {0}")]
    Transport(#[from] TransportError),
    #[error("karta holat so'zi {0:04X}")]
    Status(u16),
    #[error("karta javobi noto'g'ri: {0}")]
    BadResponse(&'static str),
    #[error("M-Pay Test Scheme ilovasi topilmadi")]
    NoApplication,
    #[error("tasodifiy son xatosi")]
    Rng,
}

impl TerminalError {
    /// `6986` — "telefonga qarang" (CDCVM kerak).
    pub fn is_see_phone(&self) -> bool {
        matches!(self, Self::Status(s) if *s == sw::SEE_PHONE)
    }
}

/// Tranzaksiya parametrlari.
#[derive(Debug, Clone)]
pub struct TxnParams {
    pub amount_minor: u64,
    pub currency: u16,
    pub country: u16,
    pub date: EmvDate,
    pub txn_type: u8,
}

impl TxnParams {
    /// Bugungi sana, UZS, xarid.
    pub fn purchase(amount_minor: u64) -> Self {
        let now = time::OffsetDateTime::now_utc();
        Self {
            amount_minor,
            currency: emv::UZ_NUMERIC,
            country: emv::UZ_NUMERIC,
            date: EmvDate::new(now.year() as u16, now.month() as u8, now.day()).unwrap_or(
                EmvDate {
                    year: 2026,
                    month: 1,
                    day: 1,
                },
            ),
            txn_type: 0x00,
        }
    }
}

/// Tap natijasi.
#[derive(Debug, Clone)]
pub struct TapResult {
    /// Avtorizatsiya uchun ICC teglari (karta + terminal).
    pub icc: Vec<Tlv>,
    pub dpan_masked: String,
    pub atc: u16,
}

impl TapResult {
    /// `icc_data` (BER-TLV, hex) — `/v1/authorizations` uchun.
    pub fn icc_hex(&self) -> String {
        hex::encode_upper(tlv::encode_all(&self.icc))
    }
}

fn send(t: &mut dyn ApduTransport, c: &Command) -> Result<Vec<u8>, TerminalError> {
    let r = Response::parse(&t.transmit(&c.to_bytes())?)
        .map_err(|_| TerminalError::BadResponse("R-APDU"))?;
    if r.sw != sw::OK {
        return Err(TerminalError::Status(r.sw));
    }
    Ok(r.data)
}

/// Kontaktsiz tranzaksiya (qVSDC uslubidagi soddalashtirilgan oqim).
pub fn tap(t: &mut dyn ApduTransport, p: &TxnParams) -> Result<TapResult, TerminalError> {
    // 1. PPSE
    let ppse = tlv::parse_all(&send(t, &Command::select(emv::PPSE_NAME))?)
        .map_err(|_| TerminalError::BadResponse("PPSE FCI"))?;
    let has_aid = tlv::find(&ppse, tag::FCI_ISSUER_DISCRETIONARY)
        .map(|d| {
            d.children()
                .iter()
                .filter(|a| a.tag.0 == tag::APPLICATION_TEMPLATE)
                .any(|a| a.find(tag::AID).and_then(Tlv::bytes) == Some(&emv::AID[..]))
        })
        .unwrap_or(false);
    if !has_aid {
        return Err(TerminalError::NoApplication);
    }
    // 2. SELECT AID
    let fci = tlv::parse_all(&send(t, &Command::select(&emv::AID))?)
        .map_err(|_| TerminalError::BadResponse("AID FCI"))?;
    let pdol = tlv::parse_dol(
        tlv::require(&fci, tag::PDOL).map_err(|_| TerminalError::BadResponse("PDOL yo'q"))?,
    )
    .map_err(|_| TerminalError::BadResponse("PDOL"))?;
    // 3. PDOL ma'lumoti
    let td = TerminalData {
        amount_minor: p.amount_minor,
        other_amount_minor: 0,
        country: p.country,
        tvr: [0; 5],
        currency: p.currency,
        date: p.date,
        txn_type: p.txn_type,
        unpredictable_number: rng::array::<4>().map_err(|_| TerminalError::Rng)?,
    };
    let full = td
        .to_pdol_data()
        .map_err(|_| TerminalError::BadResponse("summa"))?;
    // Terminal ma'lumoti PDOL tartibida (bizning profilda PDOL qat'iy; boshqa DOL — xato).
    if pdol != emv::PDOL {
        return Err(TerminalError::BadResponse("kutilmagan PDOL"));
    }
    // 4. GPO
    let resp = tlv::parse_all(&send(t, &Command::gpo(&full))?)
        .map_err(|_| TerminalError::BadResponse("GPO"))?;
    let [tmpl] = resp.as_slice() else {
        return Err(TerminalError::BadResponse("GPO shabloni"));
    };
    if tmpl.tag.0 != tag::RESPONSE_TEMPLATE_2 {
        return Err(TerminalError::BadResponse("GPO formati"));
    }
    let card = tmpl.children();
    let track2 = Track2::from_emv(
        tlv::require(card, tag::TRACK2).map_err(|_| TerminalError::BadResponse("Track 2"))?,
    )
    .map_err(|_| TerminalError::BadResponse("Track 2"))?;
    let atc = u16::from_be_bytes(
        tlv::require_len(card, tag::ATC).map_err(|_| TerminalError::BadResponse("ATC"))?,
    );

    let mut icc: Vec<Tlv> = card.to_vec();
    let mut pos = 0;
    for e in &pdol {
        icc.push(Tlv::primitive(e.tag.0, full[pos..pos + e.len].to_vec()));
        pos += e.len;
    }
    Ok(TapResult {
        icc,
        dpan_masked: track2.pan.masked(),
        atc,
    })
}
