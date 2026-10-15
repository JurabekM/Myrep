use chrono::NaiveDate;
use qrcode::render::svg;
use qrcode::{EcLevel, QrCode};
use serde::Serialize;
use serde_json::{json, Map, Value};

use crate::{PdfEngine, PdfError, Rendered};

const LOAN_RECEIPT: &str = include_str!("../../../../shared/pdf/loan_receipt.typ");
const CEREMONY_ESTIMATE: &str = include_str!("../../../../shared/pdf/ceremony_estimate.typ");
const PARTNERSHIP_CONTRACT: &str = include_str!("../../../../shared/pdf/partnership_contract.typ");

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

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EstimateLine {
    pub title: String,
    /// `ONE_OFF` yoki `PER_GUEST`.
    pub kind: String,
    /// Kishi boshiga narx (formatlangan).
    pub unit: String,
    pub guests: String,
    pub amount: String,
    /// `SAVINGS`, `FAMILY`, `EXPECTED_GIFTS`, `DEBT`.
    pub source: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EstimateTotal {
    pub source: String,
    pub amount: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EstimateAnswer {
    pub key: String,
    pub note: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct EstimateAgreement {
    pub name: String,
    pub date: String,
}

/// Marosim smetasi. Kodlar (tur, holat, manba) shablonda `pdf.*` matnlariga aylantiriladi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct CeremonyEstimate {
    pub ident: String,
    pub locale: PdfLocale,
    pub kind: String,
    pub title: String,
    pub date: Option<String>,
    pub status: String,
    pub scenario: String,
    pub guests: String,
    pub lines: Vec<EstimateLine>,
    pub totals: Vec<EstimateTotal>,
    pub total: String,
    pub payoff_months: Option<String>,
    pub payoff_date: Option<String>,
    pub answers: Vec<EstimateAnswer>,
    pub agreed: Vec<EstimateAgreement>,
    pub adults: Vec<String>,
}

impl CeremonyEstimate {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("estimate.title")
            .and_then(Value::as_str)
            .unwrap_or("Smeta")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.title),
            "name": self.title,
            "labels": labels,
            "kind": self.kind,
            "date": self.date,
            "status": self.status,
            "scenario": self.scenario,
            "guests": self.guests,
            "lines": self.lines,
            "totals": self.totals,
            "total": self.total,
            "payoff_months": self.payoff_months,
            "payoff_date": self.payoff_date,
            "answers": self.answers,
            "agreed": self.agreed,
            "adults": self.adults,
        });
        engine.render(CEREMONY_ESTIMATE, &data, &[], &self.ident, today)
    }
}

/// Sheriklik shartnomasi bandi: javob, «tegishli emas» (izoh bilan) yoki javobsiz.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractClause {
    /// `ANSWERED`, `NOT_APPLICABLE`, `UNANSWERED`.
    pub status: String,
    /// `NOT_APPLICABLE` izohi.
    pub reason: Option<String>,
    /// Kalit — qiymat juftliklari (formatlangan).
    pub rows: Vec<(String, String)>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractParty {
    pub name: String,
    /// `CAPITAL_PROVIDER`, `WORKER`, `BOTH`.
    pub role: String,
    pub capital: String,
    pub profit_share: String,
    pub loss_share: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractCapital {
    pub party: String,
    /// `MONEY` yoki `EQUIPMENT`.
    pub kind: String,
    pub description: String,
    pub amount: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractDuty {
    pub title: String,
    pub owner: String,
    pub breach: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractBuyoutRow {
    pub period: String,
    pub date: String,
    pub payment: String,
    pub remaining: String,
    pub seller: String,
    pub buyer: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ContractBuyout {
    pub seller: String,
    pub buyer: String,
    pub rows: Vec<ContractBuyoutRow>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ContractSigner {
    /// `PARTY`, `WITNESS`, `ARBITER`.
    pub role: String,
    pub name: String,
    pub signed_at: Option<String>,
    /// Chizilgan imzo (faqat raqamlardan yig'ilgan SVG, `baraka_agreements::signature_svg`).
    pub svg: Option<String>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PartnershipContract {
    pub ident: String,
    pub locale: PdfLocale,
    pub title: String,
    /// `MUDARABA` yoki `MUSHARAKA`.
    pub kind: String,
    /// `v2` yoki `None` — imzolanmagan qoralama.
    pub version: Option<String>,
    /// Shartnoma matni xeshining qisqa kodi.
    pub hash_code: String,
    /// Shablon yurist va ulamo tomonidan tekshirilmagan (`reviewStatus = PENDING`).
    pub review_pending: bool,
    pub parties: Vec<ContractParty>,
    pub capital: Vec<ContractCapital>,
    pub duties: ContractClause,
    pub duty_rows: Vec<ContractDuty>,
    pub negligence: Option<String>,
    pub custody: ContractClause,
    pub exit: ContractClause,
    pub buyout: Option<ContractBuyout>,
    pub arbiter: ContractClause,
    pub term: ContractClause,
    pub witnesses: Vec<String>,
    pub signers: Vec<ContractSigner>,
}

impl PartnershipContract {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("contract.title")
            .and_then(Value::as_str)
            .unwrap_or("Shartnoma")
            .to_string();
        let mut files: Vec<(String, Vec<u8>)> = Vec::new();
        let signers: Vec<Value> = self
            .signers
            .iter()
            .map(|s| {
                let file = s.svg.as_ref().map(|svg| {
                    let name = format!("sig-{}.svg", files.len());
                    files.push((name.clone(), svg.clone().into_bytes()));
                    name
                });
                json!({ "role": s.role, "name": s.name, "signedAt": s.signed_at, "file": file })
            })
            .collect();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.title),
            "name": self.title,
            "labels": labels,
            "kind": self.kind,
            "version": self.version,
            "hashCode": self.hash_code,
            "reviewPending": self.review_pending,
            "parties": self.parties,
            "capital": self.capital,
            "duties": self.duties,
            "dutyRows": self.duty_rows,
            "negligence": self.negligence,
            "custody": self.custody,
            "exit": self.exit,
            "buyout": self.buyout,
            "arbiter": self.arbiter,
            "term": self.term,
            "witnesses": self.witnesses,
            "signers": signers,
        });
        let extra: Vec<(&str, Vec<u8>)> =
            files.iter().map(|(n, b)| (n.as_str(), b.clone())).collect();
        engine.render(PARTNERSHIP_CONTRACT, &data, &extra, &self.ident, today)
    }
}
