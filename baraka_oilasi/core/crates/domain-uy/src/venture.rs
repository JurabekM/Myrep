//! 5-qonun: sheriklik kassa daftari va davr taqsimoti (uy/SPEC 2E.3), «Hunardan ishga»
//! rejalovchisi (2E.4) va «kafolatlangan foyda» detektori (2E.5).
//!
//! OQ-D1: standart siyosat — `CapitalFirst` (klassik qoida: foyda avval o'tgan zarar bilan
//! kamaygan kapitalni tiklaydi, qolgani ulush bo'yicha). `PerPeriod` — har davr alohida.
//! OQ-D6: buyout to'lovi narxi davr yopilganda kelishiladi (standart — jadvaldagi qiymat).
//! Vektorlar: `venture_period`, `venture_idea`, `offer_check`.
use baraka_money::{allocate_minor, percent_of, Currency, Money};

use crate::partnership::{Negligence, Partner, PartnerRole, PartnershipKind};
use crate::DomainError;

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum EntryKind {
    Income,
    Expense,
    ForceMajeure,
    /// Ishorali tuzatish: yopilgan davrdagi xato joriy davrda shu yozuv bilan to'g'rilanadi.
    Correction,
}

impl EntryKind {
    pub const ALL: [Self; 4] = [
        Self::Income,
        Self::Expense,
        Self::ForceMajeure,
        Self::Correction,
    ];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Income => "INCOME",
            Self::Expense => "EXPENSE",
            Self::ForceMajeure => "FORCE_MAJEURE",
            Self::Correction => "CORRECTION",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, Default, PartialEq, Eq, Hash)]
pub enum LossPolicy {
    /// Klassik qoida (OQ-D1 bo'yicha vaqtinchalik standart).
    #[default]
    CapitalFirst,
    PerPeriod,
}

impl LossPolicy {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::CapitalFirst => "CAPITAL_FIRST",
            Self::PerPeriod => "PER_PERIOD",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        [Self::CapitalFirst, Self::PerPeriod]
            .into_iter()
            .find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct PeriodEntry {
    pub kind: EntryKind,
    pub amount: Money,
}

/// Muddati kelgan buyout bosqichi: `capital` — o'tadigan kapital (jadval bo'yicha),
/// `price` — shu kuni kelishilgan narx (OQ-D6).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Installment {
    pub no: u32,
    pub units: u32,
    pub capital: Money,
    pub price: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BuyoutDue {
    pub seller_id: String,
    pub buyer_id: String,
    pub due: Vec<Installment>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodInput {
    pub kind: PartnershipKind,
    pub currency: Currency,
    /// `capital` — davr boshidagi kapital qoldig'i (zarar, tiklash va buyout bilan o'zgaradi).
    pub partners: Vec<Partner>,
    pub entries: Vec<PeriodEntry>,
    pub policy: LossPolicy,
    /// Har bir sherikning hali tiklanmagan zarari (≥ 0), `partners` tartibida.
    pub carried: Vec<Money>,
    pub negligence: Option<Negligence>,
    pub buyout: Option<BuyoutDue>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct BuyoutOutcome {
    pub paid: Vec<u32>,
    pub amount: Money,
    pub capital: Money,
    pub unpaid: Vec<u32>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PeriodResult {
    pub income: Money,
    pub expense: Money,
    pub force_majeure: Money,
    pub corrections: Money,
    pub result: Money,
    pub recovered: Vec<Money>,
    pub distributable: Money,
    /// Foyda ulushi (musbat) yoki zarar ulushi (manfiy).
    pub shares: Vec<Money>,
    /// Beparvolik sababli ishchi qoplaydigan summa.
    pub liability: Vec<Money>,
    pub carried_after: Vec<Money>,
    pub buyout: Option<BuyoutOutcome>,
    /// Shu davrda har bir sherikka to'lanadigan pul (buyout bilan).
    pub payouts: Vec<Money>,
    pub capital_after: Vec<Money>,
}

fn overflow() -> DomainError {
    DomainError::new("OVERFLOW")
}

fn add(a: i64, b: i64) -> Result<i64, DomainError> {
    a.checked_add(b).ok_or_else(overflow)
}

fn sub(a: i64, b: i64) -> Result<i64, DomainError> {
    a.checked_sub(b).ok_or_else(overflow)
}

fn checked_sum(xs: impl IntoIterator<Item = i64>) -> Result<i64, DomainError> {
    xs.into_iter().try_fold(0_i64, add)
}

fn same(c: Currency, m: Money) -> Result<i64, DomainError> {
    if m.currency() != c {
        return Err(DomainError::new("CURRENCY_MISMATCH"));
    }
    Ok(m.minor())
}

/// Davrni yopish: natija, zararni tiklash, taqsimot, beparvolik, buyout ayirmasi.
pub fn close_period(input: &PeriodInput) -> Result<PeriodResult, DomainError> {
    let c = input.currency;
    let ps = &input.partners;
    if ps.len() < 2 {
        return Err(DomainError::on("MIN_TWO_PARTNERS", "partners"));
    }
    let shares: Vec<i64> = ps.iter().map(|p| p.profit_share_bp).collect();
    if shares.iter().any(|s| *s < 0) || checked_sum(shares.iter().copied())? != 10_000 {
        return Err(DomainError::on("PROFIT_SHARES_NOT_100", "profit_share_bp"));
    }
    let caps = ps
        .iter()
        .map(|p| same(c, p.capital))
        .collect::<Result<Vec<_>, _>>()?;
    if caps.iter().any(|x| *x < 0) {
        return Err(DomainError::on("CAPITAL_NEGATIVE", "capital"));
    }
    let carried = input
        .carried
        .iter()
        .map(|m| same(c, *m))
        .collect::<Result<Vec<_>, _>>()?;
    if carried.len() != ps.len()
        || carried.iter().any(|x| *x < 0)
        || (input.policy == LossPolicy::PerPeriod && carried.iter().any(|x| *x != 0))
    {
        return Err(DomainError::on("INVALID_CARRIED", "carried"));
    }
    let (mut income, mut expense, mut fm, mut corr) = (0, 0, 0, 0);
    for e in &input.entries {
        let a = same(c, e.amount)?;
        let ok = match e.kind {
            EntryKind::Correction => a != 0,
            _ => a > 0,
        };
        if !ok {
            return Err(DomainError::on("AMOUNT_NOT_POSITIVE", "amount"));
        }
        let slot = match e.kind {
            EntryKind::Income => &mut income,
            EntryKind::Expense => &mut expense,
            EntryKind::ForceMajeure => &mut fm,
            EntryKind::Correction => &mut corr,
        };
        *slot = add(*slot, a)?;
    }
    let result = add(sub(sub(income, expense)?, fm)?, corr)?;
    let idx = |id: &str| ps.iter().position(|p| p.id == id);
    if let Some(n) = &input.negligence {
        if input.kind != PartnershipKind::Mudaraba {
            return Err(DomainError::on("NEGLIGENCE_NOT_APPLICABLE", "negligence"));
        }
        if n.note.trim().is_empty() {
            return Err(DomainError::on("NEGLIGENCE_NOTE_REQUIRED", "negligence"));
        }
        if !ps
            .iter()
            .any(|p| p.id == n.partner_id && p.role == PartnerRole::Worker)
        {
            return Err(DomainError::on("NEGLIGENCE_PARTY_NOT_WORKER", "negligence"));
        }
        if result >= 0 {
            return Err(DomainError::on("NEGLIGENCE_WITHOUT_LOSS", "negligence"));
        }
    }
    let seller_buyer = match &input.buyout {
        None => None,
        Some(b) => {
            if b.seller_id == b.buyer_id {
                return Err(DomainError::on("BUYOUT_SAME_PARTY", "buyout"));
            }
            let (Some(si), Some(bi)) = (idx(&b.seller_id), idx(&b.buyer_id)) else {
                return Err(DomainError::on("UNKNOWN_PARTY", "buyout"));
            };
            for d in &b.due {
                if d.units == 0 || same(c, d.capital)? < 0 || same(c, d.price)? < 0 {
                    return Err(DomainError::on("INVALID_INSTALLMENT", "buyout"));
                }
            }
            Some((si, bi))
        }
    };

    let n = ps.len();
    let mut recovered = vec![0; n];
    let mut liability = vec![0; n];
    let mut carried_after = carried.clone();
    let mut cap_after = caps.clone();
    let distributable;
    let parts;
    if result >= 0 {
        let rec_total = match input.policy {
            LossPolicy::CapitalFirst => result.min(checked_sum(carried.iter().copied())?),
            LossPolicy::PerPeriod => 0,
        };
        if rec_total > 0 {
            recovered = allocate_minor(rec_total, &carried)?;
        }
        distributable = sub(result, rec_total)?;
        parts = allocate_minor(distributable, &shares)?;
        for i in 0..n {
            carried_after[i] = sub(carried[i], recovered[i])?;
            cap_after[i] = add(caps[i], recovered[i])?;
        }
    } else {
        distributable = 0;
        if let Some(neg) = &input.negligence {
            let ratios: Vec<i64> = ps
                .iter()
                .map(|p| i64::from(p.id == neg.partner_id))
                .collect();
            parts = allocate_minor(result, &ratios)?;
            for i in 0..n {
                liability[i] = parts[i].checked_neg().ok_or_else(overflow)?;
            }
        } else {
            if caps.iter().all(|x| *x == 0) {
                return Err(DomainError::on("NO_CAPITAL", "capital"));
            }
            parts = allocate_minor(result, &caps)?;
            for i in 0..n {
                cap_after[i] = add(caps[i], parts[i])?;
                if input.policy == LossPolicy::CapitalFirst {
                    carried_after[i] = sub(carried[i], parts[i])?;
                }
            }
        }
    }
    let mut payouts: Vec<i64> = parts.iter().map(|x| (*x).max(0)).collect();
    let buyout = match (&input.buyout, seller_buyer) {
        (Some(b), Some((si, bi))) => {
            let available = payouts[bi];
            let (mut amount, mut capital) = (0, 0);
            let mut paid = Vec::new();
            for d in &b.due {
                let next = add(amount, d.price.minor())?;
                if next > available {
                    break;
                }
                amount = next;
                capital = add(capital, d.capital.minor())?;
                paid.push(d.no);
            }
            capital = capital.min(cap_after[si].max(0));
            payouts[bi] = sub(payouts[bi], amount)?;
            payouts[si] = add(payouts[si], amount)?;
            cap_after[si] = sub(cap_after[si], capital)?;
            cap_after[bi] = add(cap_after[bi], capital)?;
            let unpaid = b
                .due
                .iter()
                .map(|d| d.no)
                .filter(|no| !paid.contains(no))
                .collect();
            Some(BuyoutOutcome {
                paid,
                amount: Money::new(amount, c),
                capital: Money::new(capital, c),
                unpaid,
            })
        }
        _ => None,
    };
    let m = |v: i64| Money::new(v, c);
    let ms = |v: &[i64]| v.iter().map(|x| Money::new(*x, c)).collect::<Vec<_>>();
    Ok(PeriodResult {
        income: m(income),
        expense: m(expense),
        force_majeure: m(fm),
        corrections: m(corr),
        result: m(result),
        recovered: ms(&recovered),
        distributable: m(distributable),
        shares: ms(&parts),
        liability: ms(&liability),
        carried_after: ms(&carried_after),
        buyout,
        payouts: ms(&payouts),
        capital_after: ms(&cap_after),
    })
}

// --- «Hunardan ishga» (2E.4) --------------------------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum ScenarioName {
    Pessimistic,
    Base,
    Optimistic,
}

impl ScenarioName {
    pub const ALL: [Self; 3] = [Self::Pessimistic, Self::Base, Self::Optimistic];

    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Pessimistic => "PESSIMISTIC",
            Self::Base => "BASE",
            Self::Optimistic => "OPTIMISTIC",
        }
    }

    pub fn parse(s: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|k| k.as_str() == s)
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct IdeaScenario {
    pub name: ScenarioName,
    pub income: Money,
    pub expense: Money,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IdeaInput {
    pub currency: Currency,
    pub capex: Vec<Money>,
    pub scenarios: Vec<IdeaScenario>,
    /// Sheriklikda mehnat egasining foyda ulushi (bp); `None` — o'z puli bilan.
    pub worker_share_bp: Option<i64>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct IdeaRow {
    pub name: ScenarioName,
    pub net: Money,
    pub annual_net: Money,
    pub payback_months: Option<i64>,
    pub worker_monthly: Option<Money>,
    pub investor_monthly: Option<Money>,
    pub investor_payback_months: Option<i64>,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct IdeaResult {
    pub capex: Money,
    pub scenarios: Vec<IdeaRow>,
    pub warnings: Vec<&'static str>,
}

fn payback(capex: i64, monthly: i64) -> Option<i64> {
    // Ikkalasi ham musbat: (a + b − 1) / b, toshib ketmasligi uchun i128 da.
    (monthly > 0).then(|| {
        let v = (i128::from(capex) + i128::from(monthly) - 1) / i128::from(monthly);
        i64::try_from(v).unwrap_or(i64::MAX)
    })
}

pub fn venture_idea(input: &IdeaInput) -> Result<IdeaResult, DomainError> {
    let c = input.currency;
    let mut capex = 0;
    for a in &input.capex {
        let v = same(c, *a)?;
        if v <= 0 {
            return Err(DomainError::on("CAPEX_ITEM_NOT_POSITIVE", "capex"));
        }
        capex = add(capex, v)?;
    }
    let mut names: Vec<ScenarioName> = input.scenarios.iter().map(|s| s.name).collect();
    names.sort();
    if names != ScenarioName::ALL {
        return Err(DomainError::on("INVALID_SCENARIOS", "scenarios"));
    }
    if let Some(bp) = input.worker_share_bp {
        if !(0..=10_000).contains(&bp) {
            return Err(DomainError::on("INVALID_BP", "workerShareBp"));
        }
    }
    let mut rows = Vec::new();
    for name in ScenarioName::ALL {
        let s = input
            .scenarios
            .iter()
            .find(|s| s.name == name)
            .ok_or(DomainError::new("INVALID_SCENARIOS"))?;
        let (inc, exp) = (same(c, s.income)?, same(c, s.expense)?);
        if inc < 0 || exp < 0 {
            return Err(DomainError::on("AMOUNT_NEGATIVE", "scenarios"));
        }
        let net = sub(inc, exp)?;
        let (mut worker, mut investor, mut inv_pay) = (None, None, None);
        if let Some(bp) = input.worker_share_bp {
            let w = if net > 0 {
                percent_of(Money::new(net, c), bp)?.minor()
            } else {
                0
            };
            let inv = sub(net, w)?;
            worker = Some(Money::new(w, c));
            investor = Some(Money::new(inv, c));
            inv_pay = payback(capex, inv);
        }
        rows.push(IdeaRow {
            name,
            net: Money::new(net, c),
            annual_net: Money::new(net.checked_mul(12).ok_or_else(overflow)?, c),
            payback_months: payback(capex, net),
            worker_monthly: worker,
            investor_monthly: investor,
            investor_payback_months: inv_pay,
        });
    }
    let nets: Vec<i64> = rows.iter().map(|r| r.net.minor()).collect();
    let warnings = if nets[0] <= nets[1] && nets[1] <= nets[2] {
        Vec::new()
    } else {
        vec!["SCENARIOS_NOT_ORDERED"]
    };
    Ok(IdeaResult {
        capex: Money::new(capex, c),
        scenarios: rows,
        warnings,
    })
}

// --- «Kafolatlangan foyda» detektori (2E.5) ----------------------------------------------

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash)]
pub enum Reply {
    Yes,
    No,
    Unknown,
}

impl Reply {
    pub fn parse(s: &str) -> Option<Self> {
        match s {
            "YES" => Some(Self::Yes),
            "NO" => Some(Self::No),
            "UNKNOWN" => Some(Self::Unknown),
            _ => None,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OfferAnswers {
    pub guaranteed: Reply,
    pub loss_shared: Reply,
    pub real_activity: Reply,
    pub recruitment: Reply,
    pub urgency: Reply,
    pub written: Reply,
    /// Davlat ruxsati (litsenziya) bormi.
    pub licensed: Reply,
    /// Ishni (ombor, mol, hujjat) o'z ko'zi bilan ko'rishga ruxsat berildimi.
    pub inspection: Reply,
    /// Pulni istagan vaqtda qaytarib olish mumkinmi.
    pub exit_easy: Reply,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Hash, PartialOrd, Ord)]
pub enum Level {
    Green,
    Yellow,
    Red,
}

impl Level {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Green => "GREEN",
            Self::Yellow => "YELLOW",
            Self::Red => "RED",
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct OfferFlag {
    pub code: &'static str,
    pub level: Level,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct OfferVerdict {
    pub verdict: Level,
    pub flags: Vec<OfferFlag>,
    /// «Besh xavf belgisi»dan nechtasi topildi.
    pub signs: u8,
}

/// «Besh xavf belgisi» (Musofir SPEC): 1 — kafolatlangan foyda, 2 — shoshirish,
/// 3 — yangi odam olib kelish, 4 — ishning o'zi yo'q (mol, ruxsat, tekshirtirmaydi), 5 — kirish oson,
/// chiqish qiyin. Ikki va undan ortiq belgi — `TWO_SIGNS` (qizil).
pub const OFFER_SIGNS: [(&str, u8); 7] = [
    ("GUARANTEED_PROFIT", 1),
    ("URGENCY", 2),
    ("RECRUITMENT_REQUIRED", 3),
    ("NO_REAL_ACTIVITY", 4),
    ("NO_LICENSE", 4),
    ("INSPECTION_REFUSED", 4),
    ("EXIT_HARD", 5),
];

/// Bayroqlardagi belgilar soni; ikkitadan ko'p bo'lsa `TWO_SIGNS` qo'shiladi.
pub fn offer_signs(flags: &mut Vec<OfferFlag>) -> u8 {
    let mut seen = [false; 6];
    for f in flags.iter() {
        if let Some((_, n)) = OFFER_SIGNS.iter().find(|(c, _)| *c == f.code) {
            seen[usize::from(*n)] = true;
        }
    }
    let n = u8::try_from(seen.iter().filter(|x| **x).count()).unwrap_or(u8::MAX);
    if n >= 2 {
        flags.push(OfferFlag {
            code: "TWO_SIGNS",
            level: Level::Red,
        });
    }
    n
}

/// Qaror jadvali: (javob → bayroq) har savol uchun; xavfsiz javob bayroqsiz.
pub fn offer_check(a: &OfferAnswers) -> OfferVerdict {
    use Level::{Red, Yellow};
    use Reply::{No, Unknown, Yes};
    let table: [(Reply, Reply, &'static str, Level, &'static str); 9] = [
        (
            a.guaranteed,
            Yes,
            "GUARANTEED_PROFIT",
            Red,
            "GUARANTEED_UNKNOWN",
        ),
        (
            a.loss_shared,
            No,
            "LOSS_NOT_SHARED",
            Red,
            "LOSS_SHARING_UNKNOWN",
        ),
        (
            a.real_activity,
            No,
            "NO_REAL_ACTIVITY",
            Red,
            "REAL_ACTIVITY_UNKNOWN",
        ),
        (
            a.recruitment,
            Yes,
            "RECRUITMENT_REQUIRED",
            Red,
            "RECRUITMENT_UNKNOWN",
        ),
        (a.urgency, Yes, "URGENCY", Yellow, "URGENCY_UNKNOWN"),
        (
            a.written,
            No,
            "NO_WRITTEN_CONTRACT",
            Yellow,
            "WRITTEN_UNKNOWN",
        ),
        (a.licensed, No, "NO_LICENSE", Yellow, "LICENSE_UNKNOWN"),
        (
            a.inspection,
            No,
            "INSPECTION_REFUSED",
            Red,
            "INSPECTION_UNKNOWN",
        ),
        (a.exit_easy, No, "EXIT_HARD", Red, "EXIT_UNKNOWN"),
    ];
    let mut flags = Vec::new();
    for (reply, bad, code, level, unknown) in table {
        if reply == bad {
            flags.push(OfferFlag { code, level });
        } else if reply == Unknown {
            flags.push(OfferFlag {
                code: unknown,
                level: Yellow,
            });
        }
    }
    let signs = offer_signs(&mut flags);
    let verdict = flags.iter().map(|f| f.level).max().unwrap_or(Level::Green);
    OfferVerdict {
        verdict,
        flags,
        signs,
    }
}

// --- Kurs yoki ustoz taklifi: umumiy detektorning `COURSE` turi (8-tamoyil, SPEC 2G.4) -----------

/// Kurs taklifi javoblari. `job_abroad` — Musofir uchun ixtiyoriy savol (`None` — so'ralmagan).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct CourseAnswers {
    /// Qisqa muddatda boylik yoki katta daromad va'da qilinadimi.
    pub fast_rich: Reply,
    /// «Sir», «hech kim aytmaydigan usul» kabi da'vo bormi.
    pub secret_formula: Reply,
    /// Kursdan keyin daromad yoki ish kafolatlanadimi.
    pub income_guarantee: Reply,
    /// Dastur va amaliy natija yozilganmi.
    pub syllabus: Reply,
    /// O'qituvchining amaliy ishini ko'rib, tekshirib bo'ladimi.
    pub teacher_verifiable: Reply,
    pub urgency: Reply,
    /// Boshqalarni olib kelsangiz pul qaytadimi.
    pub recruitment: Reply,
    /// Sinov darsi yoki pulni qaytarish sharti bormi.
    pub trial_or_refund: Reply,
    /// Kursdan keyin chet elda ish kafolati.
    pub job_abroad: Option<Reply>,
}

/// Kursda har bir aniq bayroq — alohida belgi; ikki va undan ortiq — `TWO_SIGNS` (qizil).
pub const COURSE_SIGNS: [&str; 9] = [
    "FAST_RICH",
    "SECRET_FORMULA",
    "INCOME_GUARANTEE",
    "NO_SYLLABUS",
    "UNVERIFIABLE_TEACHER",
    "URGENCY",
    "RECRUITMENT_REQUIRED",
    "NO_TRIAL_OR_REFUND",
    "JOB_ABROAD_PROMISE",
];

/// Belgi yo'q — yashil; bitta belgi — sariq; ikki belgi yoki `INCOME_GUARANTEE`,
/// `RECRUITMENT_REQUIRED`, `JOB_ABROAD_PROMISE` ning o'zi — qizil. `UNKNOWN` — sariq, belgi emas.
pub fn course_check(a: &CourseAnswers) -> OfferVerdict {
    use Level::{Red, Yellow};
    use Reply::{No, Unknown, Yes};
    let mut table: Vec<(Reply, Reply, &'static str, Level, &'static str)> = vec![
        (a.fast_rich, Yes, "FAST_RICH", Yellow, "FAST_RICH_UNKNOWN"),
        (
            a.secret_formula,
            Yes,
            "SECRET_FORMULA",
            Yellow,
            "SECRET_FORMULA_UNKNOWN",
        ),
        (
            a.income_guarantee,
            Yes,
            "INCOME_GUARANTEE",
            Red,
            "INCOME_GUARANTEE_UNKNOWN",
        ),
        (a.syllabus, No, "NO_SYLLABUS", Yellow, "SYLLABUS_UNKNOWN"),
        (
            a.teacher_verifiable,
            No,
            "UNVERIFIABLE_TEACHER",
            Yellow,
            "TEACHER_UNKNOWN",
        ),
        (a.urgency, Yes, "URGENCY", Yellow, "URGENCY_UNKNOWN"),
        (
            a.recruitment,
            Yes,
            "RECRUITMENT_REQUIRED",
            Red,
            "RECRUITMENT_UNKNOWN",
        ),
        (
            a.trial_or_refund,
            No,
            "NO_TRIAL_OR_REFUND",
            Yellow,
            "TRIAL_UNKNOWN",
        ),
    ];
    if let Some(r) = a.job_abroad {
        table.push((r, Yes, "JOB_ABROAD_PROMISE", Red, "JOB_ABROAD_UNKNOWN"));
    }
    let mut flags = Vec::new();
    for (reply, bad, code, level, unknown) in table {
        if reply == bad {
            flags.push(OfferFlag { code, level });
        } else if reply == Unknown {
            flags.push(OfferFlag {
                code: unknown,
                level: Yellow,
            });
        }
    }
    let n = flags
        .iter()
        .filter(|f| COURSE_SIGNS.contains(&f.code))
        .count();
    let signs = u8::try_from(n).unwrap_or(u8::MAX);
    if signs >= 2 {
        flags.push(OfferFlag {
            code: "TWO_SIGNS",
            level: Red,
        });
    }
    let verdict = flags.iter().map(|f| f.level).max().unwrap_or(Level::Green);
    OfferVerdict {
        verdict,
        flags,
        signs,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn uzs(v: i64) -> Money {
        Money::new(v, Currency::Uzs)
    }

    fn mud(cap: i64) -> Vec<Partner> {
        vec![
            Partner {
                id: "A".into(),
                role: PartnerRole::CapitalProvider,
                profit_share_bp: 5000,
                capital: uzs(cap),
            },
            Partner {
                id: "B".into(),
                role: PartnerRole::Worker,
                profit_share_bp: 5000,
                capital: uzs(0),
            },
        ]
    }

    fn period(cap: i64, kind: EntryKind, amount: i64, carried: i64) -> PeriodInput {
        PeriodInput {
            kind: PartnershipKind::Mudaraba,
            currency: Currency::Uzs,
            partners: mud(cap),
            entries: vec![PeriodEntry {
                kind,
                amount: uzs(amount),
            }],
            policy: LossPolicy::CapitalFirst,
            carried: vec![uzs(carried), uzs(0)],
            negligence: None,
            buyout: None,
        }
    }

    /// OQ-D1 misoli: 1-oy zarar 2 mln, 2-oy foyda 3 mln — avval 2 mln kapitalga, so'ng 0,5 + 0,5.
    #[test]
    fn loss_is_recovered_before_profit_is_shared() {
        let l = close_period(&period(800, EntryKind::Expense, 200, 0)).unwrap();
        assert_eq!(l.carried_after, [uzs(200), uzs(0)]);
        assert_eq!(l.capital_after, [uzs(600), uzs(0)]);
        let g = close_period(&period(600, EntryKind::Income, 300, 200)).unwrap();
        assert_eq!(g.recovered, [uzs(200), uzs(0)]);
        assert_eq!(g.shares, [uzs(50), uzs(50)]);
        assert_eq!(g.capital_after, [uzs(800), uzs(0)]);
    }

    #[test]
    fn payback_rounds_up() {
        assert_eq!(payback(800, 250), Some(4));
        assert_eq!(payback(800, 300), Some(3));
        assert_eq!(payback(800, 0), None);
        assert_eq!(payback(0, 10), Some(0));
    }

    #[test]
    fn offer_decision_table() {
        let safe = OfferAnswers {
            guaranteed: Reply::No,
            loss_shared: Reply::Yes,
            real_activity: Reply::Yes,
            recruitment: Reply::No,
            urgency: Reply::No,
            written: Reply::Yes,
            licensed: Reply::Yes,
            inspection: Reply::Yes,
            exit_easy: Reply::Yes,
        };
        assert_eq!(offer_check(&safe).verdict, Level::Green);
        let urgent = OfferAnswers {
            urgency: Reply::Yes,
            ..safe
        };
        assert_eq!(offer_check(&urgent).verdict, Level::Yellow);
        let pyramid = OfferAnswers {
            recruitment: Reply::Yes,
            ..safe
        };
        let v = offer_check(&pyramid);
        assert_eq!(v.verdict, Level::Red);
        assert_eq!(v.flags[0].code, "RECRUITMENT_REQUIRED");
        let unsure = OfferAnswers {
            guaranteed: Reply::Unknown,
            ..safe
        };
        assert_eq!(offer_check(&unsure).verdict, Level::Yellow);
        // Ikki sariq belgi — voz kechish.
        let two = OfferAnswers {
            licensed: Reply::No,
            ..urgent
        };
        let v = offer_check(&two);
        assert_eq!((v.verdict, v.signs), (Level::Red, 2));
        assert_eq!(v.flags.last().map(|f| f.code), Some("TWO_SIGNS"));
    }
}
