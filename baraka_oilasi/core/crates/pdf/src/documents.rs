use chrono::NaiveDate;
use qrcode::render::svg;
use qrcode::{EcLevel, QrCode};
use serde::Serialize;
use serde_json::{json, Map, Value};

use crate::{PdfEngine, PdfError, Rendered};

const LOAN_RECEIPT: &str = include_str!("../../../../shared/pdf/loan_receipt.typ");
const CEREMONY_ESTIMATE: &str = include_str!("../../../../shared/pdf/ceremony_estimate.typ");
const PARTNERSHIP_CONTRACT: &str = include_str!("../../../../shared/pdf/partnership_contract.typ");
const VENTURE_REPORT: &str = include_str!("../../../../shared/pdf/venture_report.typ");
const REVIEW_PROTOCOL: &str = include_str!("../../../../shared/pdf/review_protocol.typ");
const ARBITER_FOLDER: &str = include_str!("../../../../shared/pdf/arbiter_folder.typ");
const KK_MONTH_CLOSE: &str = include_str!("../../../../shared/pdf/kk_month_close.typ");
const KK_AGREEMENT: &str = include_str!("../../../../shared/pdf/kk_agreement.typ");
const KK_PAYSLIP: &str = include_str!("../../../../shared/pdf/kk_payslip.typ");

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

/// QR kod SVG ko'rinishida (PDF ichida va qurilmani ulash ekranida).
pub fn qr_svg(payload: &str) -> Result<Vec<u8>, PdfError> {
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

/// Davr hisobotidagi daftar yozuvi (tayyor matnlar).
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ReportEntry {
    pub date: String,
    /// `INCOME`, `EXPENSE`, `FORCE_MAJEURE`, `CORRECTION`.
    pub kind: String,
    pub category: Option<String>,
    pub note: String,
    /// Natijaga ta'siri, ishorasi bilan.
    pub amount: String,
    pub attachments: u32,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ReportParty {
    pub name: String,
    pub role: String,
    pub share: String,
    pub recovered: String,
    pub liability: String,
    pub payout: String,
    pub capital_after: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct ReportBuyout {
    pub seller: String,
    pub buyer: String,
    pub paid: String,
    pub unpaid: String,
    pub amount: String,
    pub progress: String,
}

/// Sherik uchun davr hisoboti (uy/SPEC 2E.3, MVP_PLAN 14): kirim, xarajat, natija, taqsimot,
/// buyout holati va zanjir boshi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct VentureReport {
    pub ident: String,
    pub locale: PdfLocale,
    pub title: String,
    pub kind: String,
    pub period_no: u32,
    pub start: String,
    pub end: String,
    pub version: String,
    /// `CAPITAL_FIRST` yoki `PER_PERIOD`.
    pub loss_policy: String,
    pub totals: Vec<(String, String)>,
    pub entries: Vec<ReportEntry>,
    pub parties: Vec<ReportParty>,
    pub buyout: Option<ReportBuyout>,
    pub negligence: Option<String>,
    pub chain_head: String,
    pub chain_short_code: String,
}

impl VentureReport {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("venture.title")
            .and_then(Value::as_str)
            .unwrap_or("Davr hisoboti")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.title),
            "name": self.title,
            "labels": labels,
            "kind": self.kind,
            "periodNo": self.period_no,
            "start": self.start,
            "end": self.end,
            "version": self.version,
            "lossPolicy": self.loss_policy,
            "totals": self.totals,
            "entries": self.entries,
            "parties": self.parties,
            "buyout": self.buyout,
            "negligence": self.negligence,
            "chain_short_code": self.chain_short_code,
        });
        let files = vec![("qr.svg", qr_svg(&self.chain_head)?)];
        engine.render(VENTURE_REPORT, &data, &files, &self.ident, today)
    }
}

/// Vazifa hodisasi (tayyor matnlar).
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct IncidentLine {
    pub date: String,
    pub duty: String,
    pub party: String,
    pub reason: String,
    pub solution: String,
    /// `OPEN` yoki `RESOLVED`.
    pub status: String,
}

/// Bayonnomadagi tomon belgisi: `AGREE` yoki `OBJECT` + izoh.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct AckLine {
    pub party: String,
    pub verdict: String,
    pub note: String,
}

/// Ochiq hisob ko'rigi bayonnomasi (uy/SPEC 2F.5): davr yozuvlari, yakun, ochiq hodisalar,
/// tomonlar belgisi va o'sha paytdagi zanjir boshi (6.5 bloki).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ReviewProtocol {
    pub ident: String,
    pub locale: PdfLocale,
    pub title: String,
    pub review_no: u32,
    pub range: String,
    pub held_on: String,
    /// `SCHEDULED`, `PROFIT_SPIKE`, `EXTRA`.
    pub reason: String,
    pub version: String,
    pub totals: Vec<(String, String)>,
    pub entries: Vec<ReportEntry>,
    pub incidents: Vec<IncidentLine>,
    pub acks: Vec<AckLine>,
    pub chain_ok: bool,
    pub chain_head: String,
    pub chain_short_code: String,
}

impl ReviewProtocol {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("protocol.title")
            .and_then(Value::as_str)
            .unwrap_or("Bayonnoma")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.title),
            "name": self.title,
            "labels": labels,
            "reviewNo": self.review_no,
            "range": self.range,
            "heldOn": self.held_on,
            "reason": self.reason,
            "version": self.version,
            "totals": self.totals,
            "entries": self.entries,
            "incidents": self.incidents,
            "acks": self.acks,
            "chainOk": self.chain_ok,
            "chain_short_code": self.chain_short_code,
        });
        let files = vec![("qr.svg", qr_svg(&self.chain_head)?)];
        engine.render(REVIEW_PROTOCOL, &data, &files, &self.ident, today)
    }
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FolderVersion {
    pub no: String,
    pub date: String,
    pub hash_code: String,
    pub signatures: String,
    pub note: String,
    pub in_force: bool,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FolderPeriod {
    pub title: String,
    pub totals: Vec<(String, String)>,
    pub entries: Vec<ReportEntry>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FolderReview {
    pub no: String,
    pub range: String,
    pub held_on: String,
    pub acks: Vec<AckLine>,
    pub chain_code: String,
    /// `INTACT`, `CHAIN_BROKEN`, `HEAD_MISMATCH`, `TRUNCATED`.
    pub integrity: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FolderClaim {
    pub party: String,
    pub claim: String,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
pub struct FolderDecision {
    pub decided_on: String,
    pub arbiter: String,
    pub decision: String,
    /// `RESUME` yoki `AMEND`.
    pub outcome: String,
}

/// «Hakam uchun ish papkasi» (uy/SPEC 2F.8): bitta PDF, mundarija va sahifa raqamlari bilan.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct ArbiterFolder {
    pub ident: String,
    pub locale: PdfLocale,
    pub title: String,
    pub kind: String,
    pub arbiter: String,
    pub opened_on: String,
    pub opened_by: String,
    pub subject: String,
    pub clauses: String,
    pub claims: Vec<FolderClaim>,
    /// Amaldagi shartnomaning asosiy shartlari (i18n kaliti, qiymat).
    pub terms: Vec<(String, String)>,
    pub versions: Vec<FolderVersion>,
    pub periods: Vec<FolderPeriod>,
    pub chain_ok: bool,
    pub chain_entries: u32,
    pub chain_short_code: String,
    pub reviews: Vec<FolderReview>,
    pub incidents: Vec<IncidentLine>,
    pub decision: Option<FolderDecision>,
}

impl ArbiterFolder {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("folder.title")
            .and_then(Value::as_str)
            .unwrap_or("Hakam uchun ish papkasi")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.title),
            "name": self.title,
            "labels": labels,
            "kind": self.kind,
            "arbiter": self.arbiter,
            "openedOn": self.opened_on,
            "openedBy": self.opened_by,
            "subject": self.subject,
            "clauses": self.clauses,
            "claims": self.claims,
            "terms": self.terms,
            "versions": self.versions,
            "periods": self.periods,
            "chainOk": self.chain_ok,
            "chainEntries": self.chain_entries,
            "chainCode": self.chain_short_code,
            "reviews": self.reviews,
            "incidents": self.incidents,
            "decision": self.decision,
        });
        engine.render(ARBITER_FOLDER, &data, &[], &self.ident, today)
    }
}

/// Kasb-kor «Hisob kuni» bayonnomasi (kasbkor/SPEC 4.5): oy yakunlari, soliq zaxirasi, egasi maoshi,
/// qolgan pul va taqsimot; oxirida bayonnomalar zanjiri boshi. Qatorlar — `(yorliq kaliti, qiymat)`.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkCloseReport {
    pub ident: String,
    pub locale: PdfLocale,
    pub business: String,
    pub period: String,
    pub closed_on: String,
    pub totals: Vec<(String, String)>,
    pub rule: Vec<(String, String)>,
    pub allocation: Option<Vec<(String, String)>>,
    pub notes: Vec<String>,
    pub explanation: Option<String>,
    pub chain_head: String,
    pub chain_short_code: String,
}

impl KkCloseReport {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = labels
            .get("kkclose.title")
            .and_then(Value::as_str)
            .unwrap_or("Hisob kuni bayonnomasi")
            .to_string();
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.period),
            "labels": labels,
            "business": self.business,
            "period": self.period,
            "closedOn": self.closed_on,
            "totals": self.totals,
            "rule": self.rule,
            "allocation": self.allocation,
            "notes": self.notes,
            "explanation": self.explanation,
            "chain_short_code": self.chain_short_code,
        });
        let files = vec![("qr.svg", qr_svg(&self.chain_head)?)];
        engine.render(KK_MONTH_CLOSE, &data, &files, &self.ident, today)
    }
}

/// Shablon bandi: 9 savol raqami, yorliq va matn kalitlari (`shared/content/templates`).
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkClauseLine {
    pub n: u32,
    pub label: String,
    pub text: String,
}

/// Kasb-kor xodim (`EMPLOYMENT`) yoki ta'minotchi (`SUPPLY`) kelishuvi (kasbkor/SPEC 7). Band matnlaridagi
/// `{kalit}` lar `values` dan to'ldiriladi; qiymat `(matn, true)` bo'lsa — matn yorliq kaliti.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkAgreementDoc {
    pub ident: String,
    pub locale: PdfLocale,
    pub kind: String,
    pub business: String,
    pub party: String,
    /// Imzolangan versiya raqami; `None` — qoralama.
    pub version: Option<String>,
    pub signed_on: Option<String>,
    pub effective_from: Option<String>,
    pub hash_code: Option<String>,
    /// Shablon yurist ko'rigidan o'tmagan (`reviewStatus = PENDING`) — «Tekshiruvdan o'tmagan namuna».
    pub review_pending: bool,
    pub clauses: Vec<KkClauseLine>,
    pub values: Vec<(String, (String, bool))>,
    pub disclaimer: String,
}

fn label_of(labels: &Value, key: &str) -> String {
    labels
        .get(key)
        .and_then(Value::as_str)
        .unwrap_or(key)
        .to_string()
}

impl KkAgreementDoc {
    fn fill(&self, labels: &Value, key: &str) -> String {
        let mut text = label_of(labels, key);
        for (k, (v, is_key)) in &self.values {
            let v = if *is_key {
                label_of(labels, v)
            } else {
                v.clone()
            };
            text = text.replace(&format!("{{{k}}}"), &v);
        }
        text
    }

    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = label_of(&labels, &format!("kkagr.title.{}", self.kind));
        let clauses: Vec<Value> = self
            .clauses
            .iter()
            .map(|c| {
                json!({
                    "n": c.n,
                    "label": label_of(&labels, &c.label),
                    "text": self.fill(&labels, &c.text),
                })
            })
            .collect();
        let signers = if self.kind == "EMPLOYMENT" {
            ["kkagr.signer.employer", "kkagr.signer.employee"]
        } else {
            ["kkagr.signer.buyer", "kkagr.signer.supplier"]
        };
        let data = json!({
            "locale": self.locale.tag(),
            "title": title,
            "labels": labels,
            "business": self.business,
            "version": self.version,
            "signedOn": self.signed_on,
            "effectiveFrom": self.effective_from,
            "hashCode": self.hash_code,
            "reviewPending": self.review_pending,
            "clauses": clauses,
            "disclaimer": label_of(&labels, &self.disclaimer),
            "signers": [
                { "role": label_of(&labels, signers[0]), "name": self.business },
                { "role": label_of(&labels, signers[1]), "name": self.party },
            ],
        });
        engine.render(KK_AGREEMENT, &data, &[], &self.ident, today)
    }
}

/// Xodim bilan oylik hisob varaqchasi (kasbkor/SPEC 7.2): qatorlar — `(yorliq kaliti, qiymat)`, to'lovlar —
/// `(sana, tur yorlig'i kaliti, summa)`; oxirida imzo joyi.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct KkPayslip {
    pub ident: String,
    pub locale: PdfLocale,
    pub business: String,
    pub employee: String,
    pub role: Option<String>,
    pub period: String,
    pub rows: Vec<(String, String)>,
    pub payments: Vec<(String, String, String)>,
}

impl KkPayslip {
    pub fn render(&self, engine: &PdfEngine, today: NaiveDate) -> Result<Rendered, PdfError> {
        let labels = self.locale.labels();
        let title = label_of(&labels, "kkslip.title");
        let data = json!({
            "locale": self.locale.tag(),
            "title": format!("{title}: {}", self.period),
            "labels": labels,
            "business": self.business,
            "employee": self.employee,
            "role": self.role,
            "period": self.period,
            "rows": self.rows,
            "payments": self.payments,
        });
        engine.render(KK_PAYSLIP, &data, &[], &self.ident, today)
    }
}
