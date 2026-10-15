use chrono::NaiveDate;
use qrcode::render::svg;
use qrcode::{EcLevel, QrCode};
use serde::Serialize;
use serde_json::{json, Map, Value};

use crate::{PdfEngine, PdfError, Rendered};

const LOAN_RECEIPT: &str = include_str!("../../../../shared/pdf/loan_receipt.typ");

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum PdfLocale {
    Uz,
    UzCyrl,
    Ru,
}

impl PdfLocale {
    pub fn from_tag(tag: &str) -> Option<Self> {
        match tag {
            "uz" => Some(Self::Uz),
            "uz-Cyrl" => Some(Self::UzCyrl),
            "ru" => Some(Self::Ru),
            _ => None,
        }
    }

    fn tag(self) -> &'static str {
        match self {
            Self::Uz => "uz",
            Self::UzCyrl => "uz-Cyrl",
            Self::Ru => "ru",
        }
    }

    /// `cargo xtask i18n` generatsiya qilgan `pdf.*` matnlari.
    fn labels(self) -> Value {
        let raw = match self {
            Self::Uz => include_str!("i18n/uz.json"),
            Self::UzCyrl => include_str!("i18n/uz-Cyrl.json"),
            Self::Ru => include_str!("i18n/ru.json"),
        };
        serde_json::from_str(raw).unwrap_or(Value::Object(Map::new()))
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ScheduleLine {
    /// Ko'rsatish uchun tayyor sana va summa (formatlash yadroda qilingan).
    pub date: String,
    pub amount: String,
}

/// Qarz tilxati ma'lumotlari. Barcha matnlar tayyor (formatlangan) holda keladi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct LoanReceipt {
    pub ident: String,
    pub locale: PdfLocale,
    pub lender: String,
    pub borrower: String,
    pub amount: String,
    pub issued_on: String,
    pub due_on: String,
    pub place: String,
    pub schedule: Vec<ScheduleLine>,
    pub witnesses: Vec<String>,
    pub note: Option<String>,
    /// Jurnal boshi (to'liq hex) — QR uchun; `chain_short_code` — ko'rinadigan qisqa kod.
    pub chain_head: Option<String>,
    pub chain_short_code: Option<String>,
}

fn qr_svg(payload: &str) -> Result<Vec<u8>, PdfError> {
    let code =
        QrCode::with_error_correction_level(payload.as_bytes(), EcLevel::M).map_err(|e| {
            PdfError {
                code: "PDF_QR",
                details: vec![e.to_string()],
            }
        })?;
    let svg = code
        .render::<svg::Color<'_>>()
        .quiet_zone(true)
        .min_dimensions(200, 200)
        .dark_color(svg::Color("#141413"))
        .light_color(svg::Color("#FFFFFF"))
        .build();
    Ok(svg.into_bytes())
}

impl LoanReceipt {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("receipt.title")
            .and_then(Value::as_str)
            .unwrap_or("Tilxat")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": title,
            "labels": labels,
            "lender": self.lender,
            "borrower": self.borrower,
            "amount": self.amount,
            "issued_on": self.issued_on,
            "due_on": self.due_on,
            "place": self.place,
            "schedule": self.schedule,
            "witnesses": self.witnesses,
            "note": self.note,
            "chain_short_code": self.chain_short_code,
        });
        let mut files = Vec::new();
        if let Some(head) = &self.chain_head {
            files.push(("qr.svg", qr_svg(head)?));
        }
        engine.render(LOAN_RECEIPT, &data, &files, &self.ident, today)
    }
}
