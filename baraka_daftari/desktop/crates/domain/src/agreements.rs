//! 6-qonun: umumiy kelishuv dvigateli (SPEC 2F.1–2F.3, 2F.7, 2F.10; `DESKTOP_PROMPT` 5.3).
//!
//! - Har bir kelishuv «Chorsucha shartnomaning 9 savoli»ga javob beradi (`Questions`). Tur faqat qaysi savol
//!   «tegishli emas» deb belgilanishi mumkinligini va qo'shimcha validatsiyani belgilaydi.
//! - `completeness` — 9/9 tekshiruvi (`missing` + `errors`). 9/9 bo'lmasa imzolash bosqichi ochilmaydi.
//! - Versiya mazmuni kanonik JSON (`to_value` + `journal::canonical`): xeshlanadi va o'zgarmas saqlanadi.
//! - Sof hisob: DB, imzo va holat o'tishlari `storage`/`services` da.
use money::{Currency, Money};
use serde_json::{json, Map, Value};

use crate::{
    date_from_str, date_to_string, journal::canonical, AgreementSignKind, AgreementStatus,
    AgreementType, Date, ReportPeriod,
};

/// Kelishuvning majburiy savollari soni.
pub const QUESTION_COUNT: u8 = 9;
/// Bitta sheriklik/kelishuv uchun eng ko'p tomon (D12 bilan bir xil).
pub const MAX_PARTIES: usize = 6;
pub const MIN_PARTIES: usize = 2;
/// Muddat oylarda (D12 bilan bir xil).
pub const MAX_TERM_MONTHS: u32 = 120;

/// Savol javobi: «javob berilmagan», «javob berildi» yoki «tegishli emas» (izoh majburiy).
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Answer<T> {
    Missing,
    Answered(T),
    NotApplicable { reason: String },
}

/// Tomon (SPEC 2F.2, 1-savol). `role` — erkin matn («Kapital egasi», «Qarz beruvchi» ...).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Party {
    pub id: String,
    pub name: String,
    pub role: String,
    /// Xonadon a'zosi bo'lsa — uning identifikatori.
    pub member_id: Option<String>,
}

/// Hissa (2-savol): pul bo'lsa `amount` bilan, mehnat yoki tanish-bilish bo'lsa faqat tavsif bilan.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Contribution {
    pub party_id: String,
    pub description: String,
    pub amount: Option<Money>,
}

/// Vazifa (3-savol). `owner_party_id` — yagona mas'ul; `None` («hamma») qabul qilinmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Duty {
    pub text: String,
    pub owner_party_id: Option<String>,
    /// «Bajarilmasa» bandi: masalan, «1 kun ichida xabar beradi va o'rniga yechim topadi».
    pub if_not_done: String,
}

/// Bitta tomonning foyda ulushi (bazis punkt: 5000 = 50%).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfitShare {
    pub party_id: String,
    pub share_bp: u32,
}

/// Foyda qoidasi (4-savol): faqat foiz (bp). `fixed_amount` berilsa — kafolatlangan daromad, rad etiladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ProfitRule {
    pub shares: Vec<ProfitShare>,
    pub fixed_amount: Option<Money>,
}

/// Zarar qoidasi (5-savol): tur bo'yicha taklif qilinadi, foydalanuvchi tahrirlaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LossRule {
    pub text: String,
}

/// Pul va hisob (6-savol): pul qayerda, hisobni kim yuritadi, ikkinchi tomon qachon ko'radi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Custody {
    pub place: String,
    /// Hisob yurituvchi qurilma (standart — kelishuvni yaratgan qurilma).
    pub keeper_device_id: Option<String>,
    /// Ko'rik davriyligi (standart — oyiga bir marta).
    pub review_every: ReportPeriod,
}

/// Chiqish tartibi (7-savol): ogohlantirish muddati, baholash, to'lash, mol-mulk taqsimoti.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExitClause {
    pub text: String,
}

/// Hakam (8-savol). Hakam tomonlardan biri bo'lishi mumkin emas.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Arbiter {
    pub name: String,
    /// Agar hakam tomonlardan biri deb belgilansa — shu tomonning identifikatori (tekshiriladi).
    pub party_id: Option<String>,
}

/// Muddat va yangilanish (9-savol). `review_date` majburiy; `months` — cheklangan muddat bo'lsa.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Term {
    pub months: Option<u32>,
    pub review_date: Date,
}

/// 9 savol. Maydon nomlari `DESKTOP_PROMPT` va `MVP_PLAN` dagi tartib bilan bir xil.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Questions {
    pub parties: Answer<Vec<Party>>,
    pub contributions: Answer<Vec<Contribution>>,
    pub duties: Answer<Vec<Duty>>,
    pub profit: Answer<ProfitRule>,
    pub loss: Answer<LossRule>,
    pub custody: Answer<Custody>,
    pub exit: Answer<ExitClause>,
    pub arbiter: Answer<Arbiter>,
    pub term: Answer<Term>,
}

impl Questions {
    /// Hammasi «javob berilmagan» holat (yangi qoralama).
    #[must_use]
    pub const fn empty() -> Self {
        Self {
            parties: Answer::Missing,
            contributions: Answer::Missing,
            duties: Answer::Missing,
            profit: Answer::Missing,
            loss: Answer::Missing,
            custody: Answer::Missing,
            exit: Answer::Missing,
            arbiter: Answer::Missing,
            term: Answer::Missing,
        }
    }
}

/// Kelishuv hujjati (versiya mazmuni).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementDoc {
    pub agreement_type: AgreementType,
    /// Kuchga kirish sanasi — o'tmishda bo'lishi mumkin (SPEC 2F.9).
    pub effective_from: Date,
    pub witnesses: Vec<String>,
    pub questions: Questions,
}

/// Tekshiruv xatosi: savol raqami (1–9) va kod (`DESKTOP_PROMPT` 5.3 va OPEN_QUESTIONS).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Issue {
    pub question: u8,
    pub code: &'static str,
}

/// To'liqlik natijasi: `missing` — javobsiz savollar; `errors` — javob bor, lekin qoidaga zid.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Completeness {
    pub missing: Vec<u8>,
    pub errors: Vec<Issue>,
}

impl Completeness {
    /// 9/9 va xatosiz: imzolash bosqichi ochiladi.
    #[must_use]
    pub fn is_complete(&self) -> bool {
        self.missing.is_empty() && self.errors.is_empty()
    }
}

/// Bloklamaydigan ogohlantirish (SPEC 2F.2: «ko'rik oyiga 1 martadan siyrak bo'lsa»).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Warning {
    pub question: u8,
    pub code: &'static str,
}

/// Turga qarab «tegishli emas» deb belgilash mumkin emas (majburiy savollar).
#[must_use]
pub fn na_forbidden(t: AgreementType, question: u8) -> bool {
    use AgreementType::{Loan, Partnership, Rent, Service};
    match question {
        1 | 3 | 9 => true,
        2 => matches!(t, Partnership | Loan | Rent | Service),
        4 | 5 | 7 => matches!(t, Partnership),
        6 => matches!(t, Partnership),
        8 => matches!(t, Partnership | Loan | Rent | Service),
        _ => false,
    }
}

#[derive(Default)]
struct Sink(Completeness);

impl Sink {
    fn err(&mut self, question: u8, code: &'static str) {
        self.0.errors.push(Issue { question, code });
    }
}

/// Savol holatini ochadi: javob bo'lsa qiymatni qaytaradi, aks holda xatolarni yig'adi.
fn open<'a, T>(sink: &mut Sink, t: AgreementType, n: u8, a: &'a Answer<T>) -> Option<&'a T> {
    match a {
        Answer::Missing => {
            sink.0.missing.push(n);
            None
        }
        Answer::NotApplicable { reason } => {
            if na_forbidden(t, n) {
                sink.err(n, "NOT_APPLICABLE_FORBIDDEN");
            } else if reason.trim().is_empty() {
                sink.err(n, "NA_REASON_REQUIRED");
            }
            None
        }
        Answer::Answered(v) => Some(v),
    }
}

fn blank(s: &str) -> bool {
    s.trim().is_empty()
}

/// 9 savol bo'yicha to'liqlik va qoida tekshiruvi (SPEC 2F.2). Tartib: savol raqami bo'yicha.
#[must_use]
pub fn completeness(doc: &AgreementDoc) -> Completeness {
    let t = doc.agreement_type;
    let q = &doc.questions;
    let mut s = Sink::default();

    // 1. Tomonlar: kamida 2, nomlari bor, identifikatorlari takrorlanmaydi.
    let parties = open(&mut s, t, 1, &q.parties);
    if let Some(ps) = parties {
        if ps.len() < MIN_PARTIES {
            s.err(1, "TOO_FEW_PARTIES");
        }
        if ps.len() > MAX_PARTIES {
            s.err(1, "TOO_MANY_PARTIES");
        }
        for (i, p) in ps.iter().enumerate() {
            if blank(&p.name) {
                s.err(1, "PARTY_NAME_REQUIRED");
            }
            if ps[..i].iter().any(|o| o.id == p.id) {
                s.err(1, "DUPLICATE_PARTY_ID");
            }
        }
    }
    let known: Option<Vec<&str>> = parties.map(|ps| ps.iter().map(|p| p.id.as_str()).collect());
    let known_party = |id: &str| known.as_ref().is_none_or(|k| k.contains(&id));

    // 2. Hissalar: har bir tomonda kamida bitta hissa.
    if let Some(cs) = open(&mut s, t, 2, &q.contributions) {
        for c in cs {
            if !known_party(&c.party_id) {
                s.err(2, "UNKNOWN_PARTY");
            }
            if blank(&c.description) {
                s.err(2, "EMPTY_TEXT");
            }
        }
        if let Some(ps) = parties {
            for p in ps {
                if !cs.iter().any(|c| c.party_id == p.id) {
                    s.err(2, "PARTY_WITHOUT_CONTRIBUTION");
                }
            }
        }
    }

    // 3. Vazifalar: har birida yagona mas'ul va «bajarilmasa» bandi.
    if let Some(ds) = open(&mut s, t, 3, &q.duties) {
        if ds.is_empty() {
            s.err(3, "DUTIES_REQUIRED");
        }
        for d in ds {
            match &d.owner_party_id {
                None => s.err(3, "DUTY_WITHOUT_OWNER"),
                Some(id) if !known_party(id) => s.err(3, "UNKNOWN_PARTY"),
                Some(_) => {}
            }
            if blank(&d.text) {
                s.err(3, "EMPTY_TEXT");
            }
            if blank(&d.if_not_done) {
                s.err(3, "DUTY_WITHOUT_IF_NOT_DONE");
            }
        }
    }

    // 4. Foyda: faqat bp; sheriklikda har bir tomon uchun bitta ulush, yig'indisi 100%.
    if let Some(p) = open(&mut s, t, 4, &q.profit) {
        if p.fixed_amount.is_some() {
            s.err(4, "GUARANTEED_RETURN_FORBIDDEN");
        }
        if t == AgreementType::Partnership {
            let total: u64 = p.shares.iter().map(|x| u64::from(x.share_bp)).sum();
            // Tomonlar ro'yxati noma'lum bo'lsa qamrov tekshirilmaydi; takroriy tomon 1-savolda qayd etiladi
            // (shu sababli bu yerda faqat noyob identifikatorlar sanaladi — xatolar zanjirlanmaydi).
            let covered = parties.is_none_or(|ps| {
                let mut ids: Vec<&str> = ps.iter().map(|x| x.id.as_str()).collect();
                ids.sort_unstable();
                ids.dedup();
                p.shares.len() == ids.len()
                    && ids
                        .iter()
                        .all(|id| p.shares.iter().filter(|x| x.party_id == *id).count() == 1)
            });
            if total != 10_000 || !covered {
                s.err(4, "PROFIT_SHARES_NOT_100");
            }
            if p.shares.iter().any(|x| !known_party(&x.party_id)) {
                s.err(4, "UNKNOWN_PARTY");
            }
        }
    }

    // 5. Zarar: matn bo'lishi kerak (tur bo'yicha taklif qilingan, lekin tasdiqlangan bo'lsin).
    if let Some(l) = open(&mut s, t, 5, &q.loss) {
        if blank(&l.text) {
            s.err(5, "EMPTY_TEXT");
        }
    }

    // 6. Pul va hisob: joy, hisob yurituvchi qurilma.
    if let Some(c) = open(&mut s, t, 6, &q.custody) {
        if blank(&c.place) {
            s.err(6, "EMPTY_TEXT");
        }
        if c.keeper_device_id.as_deref().is_none_or(blank) {
            s.err(6, "KEEPER_DEVICE_REQUIRED");
        }
    }

    // 7. Chiqish tartibi.
    if let Some(e) = open(&mut s, t, 7, &q.exit) {
        if blank(&e.text) {
            s.err(7, "EMPTY_TEXT");
        }
    }

    // 8. Hakam: tomonlardan biri bo'lmasligi shart.
    if let Some(a) = open(&mut s, t, 8, &q.arbiter) {
        if blank(&a.name) {
            s.err(8, "EMPTY_TEXT");
        }
        if let Some(id) = &a.party_id {
            if !known_party(id) {
                s.err(8, "UNKNOWN_PARTY");
            } else {
                s.err(8, "ARBITER_IS_PARTY");
            }
        }
        if let Some(ps) = parties {
            let name = a.name.trim();
            if ps.iter().any(|p| p.name.trim().eq_ignore_ascii_case(name)) {
                s.err(8, "ARBITER_IS_PARTY");
            }
        }
    }

    // 9. Muddat va yangilash sanasi.
    if let Some(term) = open(&mut s, t, 9, &q.term) {
        if term
            .months
            .is_some_and(|m| !(1..=MAX_TERM_MONTHS).contains(&m))
        {
            s.err(9, "TERM_OUT_OF_RANGE");
        }
    }

    let mut out = s.0;
    // Ayni xatoni bir necha marta yozmaslik (masalan, har bir takroriy tomon uchun).
    out.errors.dedup();
    out
}

/// Kelishuv qoidalarini buzmaydigan, lekin e'tibor talab qiladigan holatlar.
#[must_use]
pub fn warnings(doc: &AgreementDoc) -> Vec<Warning> {
    let mut out = Vec::new();
    if let Answer::Answered(c) = &doc.questions.custody {
        if c.review_every != ReportPeriod::Monthly {
            out.push(Warning {
                question: 6,
                code: "REVIEW_LESS_OFTEN_THAN_MONTHLY",
            });
        }
    }
    if let Answer::Answered(t) = &doc.questions.term {
        let limit = add_years(doc.effective_from, 1);
        if limit.is_some_and(|l| t.review_date > l) {
            out.push(Warning {
                question: 9,
                code: "REVIEW_MORE_THAN_A_YEAR_AHEAD",
            });
        }
    }
    out
}

fn add_years(d: Date, years: i32) -> Option<Date> {
    let year = d.year().checked_add(years)?;
    Date::from_calendar_date(year, d.month(), d.day()).ok()
}

/// Imzolanishi shart bo'lgan tomon/guvoh/hakam (oilaviy rozilik alohida, xizmat qatlamida qo'shiladi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RequiredSignature {
    pub kind: AgreementSignKind,
    /// Tomon uchun — tomon identifikatori; guvoh uchun — ismi; hakam uchun — `"arbiter"`.
    pub key: String,
    pub name: String,
}

/// Joriy versiya uchun majburiy imzolar. To'liqlik tekshiruvidan o'tgandan keyin chaqiriladi.
#[must_use]
pub fn required_signatures(doc: &AgreementDoc) -> Vec<RequiredSignature> {
    let mut out = Vec::new();
    if let Answer::Answered(ps) = &doc.questions.parties {
        out.extend(ps.iter().map(|p| RequiredSignature {
            kind: AgreementSignKind::Party,
            key: p.id.clone(),
            name: p.name.clone(),
        }));
    }
    out.extend(doc.witnesses.iter().map(|w| RequiredSignature {
        kind: AgreementSignKind::Witness,
        key: w.clone(),
        name: w.clone(),
    }));
    if let Answer::Answered(a) = &doc.questions.arbiter {
        out.push(RequiredSignature {
            kind: AgreementSignKind::Arbiter,
            key: "arbiter".into(),
            name: a.name.clone(),
        });
    }
    out
}

/// Holat o'tishlari (SPEC 2F.1): versiya o'zgarsa qoralamaga qaytadi; `CLOSED` qaytarib bo'lmaydi.
#[must_use]
pub fn can_transition(from: AgreementStatus, to: AgreementStatus) -> bool {
    use AgreementStatus::{Active, Closed, Draft, InDispute, Signed};
    matches!(
        (from, to),
        (Draft, Signed)
            | (Signed, Active)
            | (Signed | Active | InDispute, Draft)
            | (Active, InDispute)
            | (InDispute, Active)
            | (Draft | Signed | Active | InDispute, Closed)
    )
}

/// SPEC 2F.7: «katta foyda» — davr foydasi rejadan ≥ 150% yoki oxirgi 3 davr o'rtachasidan ≥ 200%.
/// Butun sonlar, bo'linmasiz: `actual × 10000 ≥ plan × 15000`; `actual × 3 × 10000 ≥ S × 20000`.
#[must_use]
pub fn profit_spike_alert(
    actual: Money,
    plan: Option<Money>,
    last_three: Option<[Money; 3]>,
) -> bool {
    let a = i128::from(actual.minor());
    if a <= 0 {
        return false;
    }
    let by_plan =
        plan.is_some_and(|p| p.minor() > 0 && a * 10_000 >= i128::from(p.minor()) * 15_000);
    let by_history = last_three.is_some_and(|h| {
        let s: i128 = h.iter().map(|m| i128::from(m.minor())).sum();
        s > 0 && a * 3 * 10_000 >= s * 20_000
    });
    by_plan || by_history
}

// ------------------------------------------------------------------ kodek (mazmun ↔ JSON)

fn money_value(m: Money) -> Value {
    json!({ "minor": m.minor().to_string(), "currency": m.currency().code() })
}

fn party_value(p: &Party) -> Value {
    let mut m = Map::new();
    m.insert("id".into(), json!(p.id));
    m.insert("name".into(), json!(p.name));
    m.insert("role".into(), json!(p.role));
    if let Some(mid) = &p.member_id {
        m.insert("memberId".into(), json!(mid));
    }
    Value::Object(m)
}

fn contribution_value(c: &Contribution) -> Value {
    let mut m = Map::new();
    m.insert("partyId".into(), json!(c.party_id));
    m.insert("description".into(), json!(c.description));
    if let Some(a) = c.amount {
        m.insert("amount".into(), money_value(a));
    }
    Value::Object(m)
}

fn duty_value(d: &Duty) -> Value {
    let mut m = Map::new();
    m.insert("text".into(), json!(d.text));
    if let Some(o) = &d.owner_party_id {
        m.insert("ownerPartyId".into(), json!(o));
    }
    m.insert("ifNotDone".into(), json!(d.if_not_done));
    Value::Object(m)
}

fn profit_value(p: &ProfitRule) -> Value {
    let shares: Vec<Value> = p
        .shares
        .iter()
        .map(|s| json!({ "partyId": s.party_id, "shareBp": s.share_bp.to_string() }))
        .collect();
    let mut m = Map::new();
    m.insert("shares".into(), Value::Array(shares));
    if let Some(f) = p.fixed_amount {
        m.insert("fixedAmount".into(), money_value(f));
    }
    Value::Object(m)
}

fn custody_value(c: &Custody) -> Value {
    let mut m = Map::new();
    m.insert("place".into(), json!(c.place));
    if let Some(k) = &c.keeper_device_id {
        m.insert("keeperDeviceId".into(), json!(k));
    }
    m.insert("reviewEvery".into(), json!(c.review_every.as_str()));
    Value::Object(m)
}

fn arbiter_value(a: &Arbiter) -> Value {
    let mut m = Map::new();
    m.insert("name".into(), json!(a.name));
    if let Some(p) = &a.party_id {
        m.insert("partyId".into(), json!(p));
    }
    Value::Object(m)
}

fn term_value(t: &Term) -> Result<Value, String> {
    let mut m = Map::new();
    if let Some(months) = t.months {
        m.insert("months".into(), json!(months.to_string()));
    }
    m.insert(
        "reviewDate".into(),
        json!(date_to_string(t.review_date).map_err(|e| e.to_string())?),
    );
    Ok(Value::Object(m))
}

/// Javob qutisi: `Missing` → kalit yo'q; aks holda `{status, value|reason}`.
fn answer_value<T>(
    a: &Answer<T>,
    f: impl Fn(&T) -> Result<Value, String>,
) -> Result<Option<Value>, String> {
    Ok(match a {
        Answer::Missing => None,
        Answer::Answered(v) => Some(json!({ "status": "ANSWERED", "value": f(v)? })),
        Answer::NotApplicable { reason } => {
            Some(json!({ "status": "NOT_APPLICABLE", "reason": reason }))
        }
    })
}

fn list_value<T>(items: &[T], f: impl Fn(&T) -> Value) -> Value {
    Value::Array(items.iter().map(f).collect())
}

impl AgreementDoc {
    /// Kanonik JSON (sonlar satr). Xeshlash va saqlash uchun.
    ///
    /// # Errors
    /// Sana formatlanmasa.
    pub fn to_value(&self) -> Result<Value, String> {
        let q = &self.questions;
        let mut qs = Map::new();
        let mut put = |key: &str, v: Option<Value>| {
            if let Some(v) = v {
                qs.insert(key.into(), v);
            }
        };
        put(
            "parties",
            answer_value(&q.parties, |ps| Ok(list_value(ps, party_value)))?,
        );
        put(
            "contributions",
            answer_value(&q.contributions, |cs| {
                Ok(list_value(cs, contribution_value))
            })?,
        );
        put(
            "duties",
            answer_value(&q.duties, |ds| Ok(list_value(ds, duty_value)))?,
        );
        put("profit", answer_value(&q.profit, |p| Ok(profit_value(p)))?);
        put(
            "loss",
            answer_value(&q.loss, |l| Ok(json!({ "text": l.text })))?,
        );
        put(
            "custody",
            answer_value(&q.custody, |c| Ok(custody_value(c)))?,
        );
        put(
            "exit",
            answer_value(&q.exit, |e| Ok(json!({ "text": e.text })))?,
        );
        put(
            "arbiter",
            answer_value(&q.arbiter, |a| Ok(arbiter_value(a)))?,
        );
        put("term", answer_value(&q.term, term_value)?);
        Ok(json!({
            "type": self.agreement_type.as_str(),
            "effectiveFrom": date_to_string(self.effective_from).map_err(|e| e.to_string())?,
            "witnesses": self.witnesses,
            "questions": Value::Object(qs),
        }))
    }

    /// Kanonik satr (RFC 8785): versiya mazmuni shu satr bo'yicha xeshlanadi.
    ///
    /// # Errors
    /// [`Self::to_value`] yoki kanonizatsiya xatosi.
    pub fn canonical_text(&self) -> Result<String, String> {
        let v = self.to_value()?;
        canonical(&v).map_err(|e| e.code().to_owned())
    }

    /// JSON → hujjat. Noto'g'ri shakl yoki noma'lum qiymat bo'lsa, maydon nomi bilan xato.
    ///
    /// # Errors
    /// Shakl, tur yoki sana noto'g'ri bo'lsa.
    pub fn from_value(v: &Value) -> Result<Self, String> {
        let m = obj(v, "hujjat")?;
        let agreement_type = AgreementType::parse(text(m, "type")?.as_str())
            .ok_or("type: noma'lum kelishuv turi")?;
        let effective_from =
            date_from_str(&text(m, "effectiveFrom")?).map_err(|e| e.to_string())?;
        let witnesses = str_list(m, "witnesses")?;
        let qs = match m.get("questions") {
            None | Some(Value::Null) => Map::new(),
            Some(other) => obj(other, "questions")?.clone(),
        };
        let questions = Questions {
            parties: answer(&qs, "parties", |x| list(x, party_of))?,
            contributions: answer(&qs, "contributions", |x| list(x, contribution_of))?,
            duties: answer(&qs, "duties", |x| list(x, duty_of))?,
            profit: answer(&qs, "profit", profit_of)?,
            loss: answer(&qs, "loss", |x| {
                Ok(LossRule {
                    text: text(obj(single(x)?, "loss")?, "text")?,
                })
            })?,
            custody: answer(&qs, "custody", custody_of)?,
            exit: answer(&qs, "exit", |x| {
                Ok(ExitClause {
                    text: text(obj(single(x)?, "exit")?, "text")?,
                })
            })?,
            arbiter: answer(&qs, "arbiter", arbiter_of)?,
            term: answer(&qs, "term", term_of)?,
        };
        Ok(Self {
            agreement_type,
            effective_from,
            witnesses,
            questions,
        })
    }
}

fn obj<'a>(v: &'a Value, what: &str) -> Result<&'a Map<String, Value>, String> {
    v.as_object().ok_or_else(|| format!("{what}: obyekt kerak"))
}

fn text(m: &Map<String, Value>, key: &str) -> Result<String, String> {
    m.get(key)
        .and_then(Value::as_str)
        .map(str::to_owned)
        .ok_or_else(|| format!("{key}: satr kerak"))
}

fn opt_text(m: &Map<String, Value>, key: &str) -> Result<Option<String>, String> {
    match m.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(s)) if s.trim().is_empty() => Ok(None),
        Some(Value::String(s)) => Ok(Some(s.clone())),
        Some(_) => Err(format!("{key}: satr kerak")),
    }
}

fn str_list(m: &Map<String, Value>, key: &str) -> Result<Vec<String>, String> {
    match m.get(key) {
        None | Some(Value::Null) => Ok(Vec::new()),
        Some(Value::Array(items)) => items
            .iter()
            .map(|x| {
                x.as_str()
                    .map(str::to_owned)
                    .ok_or_else(|| format!("{key}: satrlar kerak"))
            })
            .collect(),
        Some(_) => Err(format!("{key}: massiv kerak")),
    }
}

fn number_str(m: &Map<String, Value>, key: &str) -> Result<Option<u32>, String> {
    match m.get(key) {
        None | Some(Value::Null) => Ok(None),
        Some(Value::String(s)) => s
            .parse::<u32>()
            .map(Some)
            .map_err(|_| format!("{key}: butun son satri kerak")),
        Some(_) => Err(format!("{key}: son satr sifatida yozilishi kerak")),
    }
}

fn money_of(v: &Value) -> Result<Money, String> {
    let m = obj(v, "summa")?;
    let minor: i64 = text(m, "minor")?
        .parse()
        .map_err(|_| "minor: butun son satri kerak".to_owned())?;
    let currency = Currency::from_code(&text(m, "currency")?).map_err(|e| e.to_string())?;
    Ok(Money::new(minor, currency))
}

fn list<T>(v: &Value, f: impl Fn(&Value) -> Result<T, String>) -> Result<Vec<T>, String> {
    v.get("value")
        .and_then(Value::as_array)
        .ok_or("value: massiv kerak")?
        .iter()
        .map(f)
        .collect()
}

fn answer<T>(
    qs: &Map<String, Value>,
    key: &str,
    parse: impl Fn(&Value) -> Result<T, String>,
) -> Result<Answer<T>, String> {
    let Some(v) = qs.get(key) else {
        return Ok(Answer::Missing);
    };
    let o = obj(v, key)?;
    match o.get("status").and_then(Value::as_str) {
        Some("ANSWERED") => {
            let value = o
                .get("value")
                .ok_or_else(|| format!("{key}: value kerak"))?;
            Ok(Answer::Answered(parse(&json!({ "value": value }))?))
        }
        Some("NOT_APPLICABLE") => Ok(Answer::NotApplicable {
            reason: opt_text(o, "reason")?.unwrap_or_default(),
        }),
        Some("MISSING") => Ok(Answer::Missing),
        _ => Err(format!(
            "{key}: status ANSWERED, NOT_APPLICABLE yoki MISSING bo'lishi kerak"
        )),
    }
}

fn single(v: &Value) -> Result<&Value, String> {
    v.get("value").ok_or_else(|| "value kerak".to_owned())
}

fn party_of(v: &Value) -> Result<Party, String> {
    let m = obj(v, "tomon")?;
    Ok(Party {
        id: text(m, "id")?,
        name: text(m, "name")?,
        role: text(m, "role")?,
        member_id: opt_text(m, "memberId")?,
    })
}

fn contribution_of(v: &Value) -> Result<Contribution, String> {
    let m = obj(v, "hissa")?;
    Ok(Contribution {
        party_id: text(m, "partyId")?,
        description: text(m, "description")?,
        amount: match m.get("amount") {
            None | Some(Value::Null) => None,
            Some(a) => Some(money_of(a)?),
        },
    })
}

fn duty_of(v: &Value) -> Result<Duty, String> {
    let m = obj(v, "vazifa")?;
    Ok(Duty {
        text: text(m, "text")?,
        owner_party_id: opt_text(m, "ownerPartyId")?,
        if_not_done: text(m, "ifNotDone")?,
    })
}

fn profit_of(v: &Value) -> Result<ProfitRule, String> {
    let m = obj(single(v)?, "profit")?;
    let shares = match m.get("shares") {
        None | Some(Value::Null) => Vec::new(),
        Some(Value::Array(items)) => items
            .iter()
            .map(|s| {
                let so = obj(s, "ulush")?;
                Ok(ProfitShare {
                    party_id: text(so, "partyId")?,
                    share_bp: number_str(so, "shareBp")?
                        .ok_or_else(|| "shareBp kerak".to_owned())?,
                })
            })
            .collect::<Result<_, String>>()?,
        Some(_) => return Err("shares: massiv kerak".into()),
    };
    Ok(ProfitRule {
        shares,
        fixed_amount: match m.get("fixedAmount") {
            None | Some(Value::Null) => None,
            Some(a) => Some(money_of(a)?),
        },
    })
}

fn custody_of(v: &Value) -> Result<Custody, String> {
    let m = obj(single(v)?, "custody")?;
    let every = text(m, "reviewEvery")?;
    Ok(Custody {
        place: text(m, "place")?,
        keeper_device_id: opt_text(m, "keeperDeviceId")?,
        review_every: ReportPeriod::parse(&every).ok_or("reviewEvery: noma'lum davriylik")?,
    })
}

fn arbiter_of(v: &Value) -> Result<Arbiter, String> {
    let m = obj(single(v)?, "arbiter")?;
    Ok(Arbiter {
        name: text(m, "name")?,
        party_id: opt_text(m, "partyId")?,
    })
}

fn term_of(v: &Value) -> Result<Term, String> {
    let m = obj(single(v)?, "term")?;
    Ok(Term {
        months: number_str(m, "months")?,
        review_date: date_from_str(&text(m, "reviewDate")?).map_err(|e| e.to_string())?,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::AgreementType::{Family, Loan, Partnership};

    fn d(s: &str) -> Date {
        date_from_str(s).unwrap()
    }

    fn party(id: &str, name: &str) -> Party {
        Party {
            id: id.into(),
            name: name.into(),
            role: "Tomon".into(),
            member_id: None,
        }
    }

    fn full_partnership() -> AgreementDoc {
        AgreementDoc {
            agreement_type: Partnership,
            effective_from: d("2026-10-01"),
            witnesses: vec!["Karim aka".into()],
            questions: Questions {
                parties: Answer::Answered(vec![party("P1", "Anvar"), party("P2", "Dilshod")]),
                contributions: Answer::Answered(vec![
                    Contribution {
                        party_id: "P1".into(),
                        description: "Pul".into(),
                        amount: Some(Money::new(300_000_000, Currency::Uzs)),
                    },
                    Contribution {
                        party_id: "P2".into(),
                        description: "Mehnat".into(),
                        amount: None,
                    },
                ]),
                duties: Answer::Answered(vec![Duty {
                    text: "Yetkazib berish".into(),
                    owner_party_id: Some("P2".into()),
                    if_not_done: "1 kun ichida xabar beradi".into(),
                }]),
                profit: Answer::Answered(ProfitRule {
                    shares: vec![
                        ProfitShare {
                            party_id: "P1".into(),
                            share_bp: 5_000,
                        },
                        ProfitShare {
                            party_id: "P2".into(),
                            share_bp: 5_000,
                        },
                    ],
                    fixed_amount: None,
                }),
                loss: Answer::Answered(LossRule {
                    text: "Kapitalga mutanosib".into(),
                }),
                custody: Answer::Answered(Custody {
                    place: "Anvar hisobi".into(),
                    keeper_device_id: Some("dev-1".into()),
                    review_every: ReportPeriod::Monthly,
                }),
                exit: Answer::Answered(ExitClause {
                    text: "30 kun oldin xabar".into(),
                }),
                arbiter: Answer::Answered(Arbiter {
                    name: "Usta Olim".into(),
                    party_id: None,
                }),
                term: Answer::Answered(Term {
                    months: Some(12),
                    review_date: d("2027-10-01"),
                }),
            },
        }
    }

    #[test]
    fn full_partnership_is_complete() {
        let c = completeness(&full_partnership());
        assert!(c.is_complete(), "{c:?}");
    }

    #[test]
    fn empty_draft_lists_all_nine_questions() {
        let doc = AgreementDoc {
            agreement_type: Partnership,
            effective_from: d("2026-10-01"),
            witnesses: vec![],
            questions: Questions::empty(),
        };
        let c = completeness(&doc);
        assert_eq!(c.missing, (1..=9).collect::<Vec<u8>>());
        assert!(c.errors.is_empty());
    }

    #[test]
    fn duty_without_owner_is_rejected() {
        let mut doc = full_partnership();
        doc.questions.duties = Answer::Answered(vec![Duty {
            text: "Hamma ishlaydi".into(),
            owner_party_id: None,
            if_not_done: "Xabar beradi".into(),
        }]);
        let c = completeness(&doc);
        assert!(c.errors.contains(&Issue {
            question: 3,
            code: "DUTY_WITHOUT_OWNER"
        }));
    }

    #[test]
    fn arbiter_cannot_be_a_party() {
        let mut doc = full_partnership();
        doc.questions.arbiter = Answer::Answered(Arbiter {
            name: "dilshod".into(),
            party_id: Some("P2".into()),
        });
        let c = completeness(&doc);
        assert!(c.errors.contains(&Issue {
            question: 8,
            code: "ARBITER_IS_PARTY"
        }));
    }

    #[test]
    fn not_applicable_needs_a_reason_and_forbidden_ones_are_refused() {
        // Oilada 7-savol «tegishli emas» bo'lishi mumkin: izoh majburiy.
        let mut family = full_partnership();
        family.agreement_type = Family;
        family.questions.exit = Answer::NotApplicable {
            reason: "  ".into(),
        };
        assert!(completeness(&family).errors.contains(&Issue {
            question: 7,
            code: "NA_REASON_REQUIRED"
        }));
        family.questions.exit = Answer::NotApplicable {
            reason: "sabab".into(),
        };
        assert!(!completeness(&family).errors.iter().any(|i| i.question == 7));
        // Sheriklikda chiqish tartibi majburiy: «tegishli emas» umuman qabul qilinmaydi.
        let mut doc = full_partnership();
        doc.questions.exit = Answer::NotApplicable {
            reason: "sabab".into(),
        };
        assert!(completeness(&doc).errors.contains(&Issue {
            question: 7,
            code: "NOT_APPLICABLE_FORBIDDEN"
        }));
    }

    #[test]
    fn fixed_return_is_refused_for_partnership() {
        let mut doc = full_partnership();
        doc.questions.profit = Answer::Answered(ProfitRule {
            shares: vec![],
            fixed_amount: Some(Money::new(10_000_000, Currency::Uzs)),
        });
        let c = completeness(&doc);
        assert!(c.errors.contains(&Issue {
            question: 4,
            code: "GUARANTEED_RETURN_FORBIDDEN"
        }));
    }

    #[test]
    fn loan_may_leave_profit_not_applicable() {
        let mut doc = full_partnership();
        doc.agreement_type = Loan;
        doc.questions.profit = Answer::NotApplicable {
            reason: "Foizsiz qarz".into(),
        };
        doc.questions.loss = Answer::NotApplicable {
            reason: "Asosiy summa qaytariladi".into(),
        };
        doc.questions.arbiter = Answer::NotApplicable {
            reason: "Hakam kerak emas".into(),
        };
        let c = completeness(&doc);
        assert!(c.errors.contains(&Issue {
            question: 8,
            code: "NOT_APPLICABLE_FORBIDDEN"
        }));
        assert!(!c.errors.iter().any(|i| i.question == 4));
    }

    #[test]
    fn family_may_skip_witnesses_and_arbiter() {
        let mut doc = full_partnership();
        doc.agreement_type = Family;
        doc.witnesses.clear();
        doc.questions.arbiter = Answer::NotApplicable {
            reason: "Oila ichida hakam shart emas".into(),
        };
        assert!(completeness(&doc).is_complete());
    }

    #[test]
    fn profit_shares_must_total_one_hundred_percent() {
        let mut doc = full_partnership();
        if let Answer::Answered(p) = &mut doc.questions.profit {
            p.shares[0].share_bp = 4_000;
        }
        assert!(completeness(&doc).errors.contains(&Issue {
            question: 4,
            code: "PROFIT_SHARES_NOT_100"
        }));
    }

    #[test]
    fn required_signatures_cover_parties_witnesses_and_arbiter() {
        let sigs = required_signatures(&full_partnership());
        let kinds: Vec<AgreementSignKind> = sigs.iter().map(|s| s.kind).collect();
        assert_eq!(
            kinds,
            vec![
                AgreementSignKind::Party,
                AgreementSignKind::Party,
                AgreementSignKind::Witness,
                AgreementSignKind::Arbiter,
            ]
        );
    }

    #[test]
    fn status_transitions_follow_the_law_six_lifecycle() {
        use AgreementStatus::{Active, Closed, Draft, InDispute, Signed};
        assert!(can_transition(Draft, Signed));
        assert!(can_transition(Signed, Active));
        assert!(
            can_transition(Active, Draft),
            "yangi versiya qoralamaga qaytaradi"
        );
        assert!(can_transition(Active, InDispute));
        assert!(!can_transition(Draft, Active), "imzosiz faollashmaydi");
        assert!(
            !can_transition(Closed, Draft),
            "yopilgan kelishuv qaytmaydi"
        );
    }

    #[test]
    fn profit_spike_matches_the_vector_rule() {
        let m = |x: i64| Money::new(x, Currency::Uzs);
        assert!(profit_spike_alert(
            m(150_000_000),
            Some(m(100_000_000)),
            None
        ));
        assert!(!profit_spike_alert(
            m(149_999_999),
            Some(m(100_000_000)),
            None
        ));
        let hist = Some([m(100_000_000), m(120_000_000), m(110_000_000)]);
        assert!(profit_spike_alert(m(220_000_000), None, hist));
        assert!(!profit_spike_alert(m(219_999_999), None, hist));
        assert!(!profit_spike_alert(
            m(-50_000_000),
            Some(m(100_000_000)),
            None
        ));
    }

    #[test]
    fn document_round_trips_through_canonical_json() {
        let doc = full_partnership();
        let text = doc.canonical_text().unwrap();
        let back =
            AgreementDoc::from_value(&serde_json::from_str::<Value>(&text).unwrap()).unwrap();
        assert_eq!(back, doc);
    }

    #[test]
    fn review_more_than_a_year_ahead_warns() {
        let mut doc = full_partnership();
        doc.questions.term = Answer::Answered(Term {
            months: None,
            review_date: d("2028-01-01"),
        });
        assert_eq!(
            warnings(&doc),
            vec![Warning {
                question: 9,
                code: "REVIEW_MORE_THAN_A_YEAR_AHEAD"
            }]
        );
    }
}
