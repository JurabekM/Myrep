//! Kelishuv dvigateli (SPEC 2F.2): 9 savol → majburiy bo'limlar va to'liqlik tekshiruvi.
//!
//! Savollar hamma turda bir xil. Tur bo'yicha farq: `LOAN` uchun 3-savol — qaytarish jadvali (`has_schedule`),
//! 4–5-savollar avtomatik «foiz yo'q»; `FAMILY` uchun hakam ixtiyoriy va 4–5 «tegishli emas» izoh bilan ruxsat.
//! «Tegishli emas» izohsiz qo'yilmaydi (`NA_REASON_REQUIRED`).

use std::collections::BTreeMap;

use money::Money;
use time::Date;

/// To'liq ulush, bazis punktlarda (100% = 10 000).
pub const FULL_SHARE_BP: i64 = 10_000;

/// Savollar soni.
pub const QUESTION_COUNT: u8 = 9;

/// Kelishuv turi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgreementType {
    /// Qarz tilxati.
    Loan,
    /// Sheriklik (musharaka / mudoraba).
    Partnership,
    /// Oilaviy kelishuv.
    Family,
    /// Boshqa.
    Other,
}

impl AgreementType {
    /// Bazadagi va vektordagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Loan => "LOAN",
            Self::Partnership => "PARTNERSHIP",
            Self::Family => "FAMILY",
            Self::Other => "OTHER",
        }
    }

    /// Koddan tur. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "LOAN" => Some(Self::Loan),
            "PARTNERSHIP" => Some(Self::Partnership),
            "FAMILY" => Some(Self::Family),
            "OTHER" => Some(Self::Other),
            _ => None,
        }
    }
}

/// Tomon (1-savol).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Party {
    /// Tomon identifikatori (`P1`, `P2`, ...).
    pub id: String,
    /// To'liq ism-sharif.
    pub name: String,
    /// Roli.
    pub role: String,
    /// Aloqasi (oilaviy kelishuvda).
    pub relation: String,
    /// Shu qurilma egasi.
    pub is_me: bool,
}

/// Hissa (2-savol): pul, mol, mehnat yoki tanish-bilish.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Contribution {
    /// Tomon identifikatori.
    pub party_id: String,
    /// Turi (`money`, `goods`, `labor`, `connections`).
    pub kind: String,
    /// Miqdori, bo'lsa.
    pub amount: Option<Money>,
    /// Tavsifi.
    pub description: String,
}

/// Vazifa (3-savol): yagona mas'ul tomon va «bajarilmasa» bandi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Duty {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub title: String,
    /// Mas'ul tomon. `None` — egasiz («hamma») vazifa, qabul qilinmaydi.
    pub owner_party_id: Option<String>,
    /// «Bajarilmasa» bandi.
    pub breach_clause: String,
}

/// Foyda qoidasi (4-savol): faqat foiz (bp). So'mdagi qat'iy summa — sheriklikda taqiq.
#[derive(Debug, Clone, PartialEq, Eq, Default)]
pub struct ProfitRule {
    /// Tomon → ulush (bp).
    pub shares: BTreeMap<String, i64>,
    /// Qat'iy summa (taqiqlangan), bo'lsa.
    pub fixed_amount: Option<Money>,
    /// Qo'shimcha matn.
    pub text: String,
}

/// Hisob yuritish (6-savol).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Custody {
    /// Pul qayerda turadi.
    pub location: String,
    /// Hisob yurituvchi tomon.
    pub keeper_party_id: Option<String>,
    /// Hisob yurituvchi qurilma (ixtiyoriy).
    pub keeper_device_id: Option<String>,
    /// Ko'rib chiqish davriyligi, kunlarda.
    pub review_every_days: i64,
}

/// Ajralib chiqish (7-savol).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExitClause {
    /// Oldindan ogohlantirish muddati, kunlarda.
    pub notice_days: i64,
    /// Ulushni baholash usuli.
    pub valuation: String,
    /// To'lash muddati va tartibi.
    pub payout: String,
    /// Mol-mulk qanday bo'linadi.
    pub assets: String,
}

/// Hakam (8-savol).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Arbiter {
    /// Ism-sharif.
    pub name: String,
    /// Roli.
    pub role: String,
}

/// Muddat va yangilash (9-savol).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Term {
    /// Amal qilish muddati, oylarda.
    pub term_months: i64,
    /// Keyingi ko'rib chiqish sanasi.
    pub review_date: Option<Date>,
}

/// Barcha javoblar (`AgreementAnswers`). «Tegishli emas» — sabab matni bilan (`Some`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct AgreementAnswers {
    /// 4-savol «tegishli emas» sababi.
    pub profit_not_applicable: Option<String>,
    /// 5-savol «tegishli emas» sababi.
    pub loss_not_applicable: Option<String>,
    /// 7-savol «tegishli emas» sababi.
    pub exit_not_applicable: Option<String>,
    /// 1-savol.
    pub parties: Vec<Party>,
    /// 2-savol.
    pub contributions: Vec<Contribution>,
    /// 3-savol (qaytarish jadvalidan tashqari).
    pub duties: Vec<Duty>,
    /// 4-savol.
    pub profit: ProfitRule,
    /// 5-savol: zarar qoidasi matni (tur bo'yicha avtomatik taklif qilinadi).
    pub loss_text: String,
    /// 6-savol.
    pub custody: Custody,
    /// 7-savol.
    pub exit: ExitClause,
    /// 8-savol. `None` — hakam yo'q.
    pub arbiter: Option<Arbiter>,
    /// 9-savol.
    pub term: Term,
}

/// Kelishuv holati.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum AgreementStatus {
    /// Tayyorlanmoqda: savollar to'ldirilmoqda, imzolash ochilmagan.
    Draft,
    /// Imzolangan: jurnal yozish mumkin.
    Signed,
    /// Nizoda: taqsimot bloklangan (D13A).
    InDispute,
    /// Tugatilgan.
    Ended,
}

impl AgreementStatus {
    /// Bazadagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Draft => "DRAFT",
            Self::Signed => "SIGNED",
            Self::InDispute => "IN_DISPUTE",
            Self::Ended => "ENDED",
        }
    }

    /// Koddan holat. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "DRAFT" => Some(Self::Draft),
            "SIGNED" => Some(Self::Signed),
            "IN_DISPUTE" => Some(Self::InDispute),
            "ENDED" => Some(Self::Ended),
            _ => None,
        }
    }
}

/// To'liqlik natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Completeness {
    /// Barcha savollar javoblangan.
    pub complete: bool,
    /// Javobsiz savollar raqamlari (1–9, o'sish tartibida).
    pub missing: Vec<u8>,
    /// Xato kodlari (takrorlanmaydi, tartib bilan).
    pub errors: Vec<&'static str>,
}

fn add_error(errors: &mut Vec<&'static str>, code: &'static str) {
    if !errors.contains(&code) {
        errors.push(code);
    }
}

fn same_name(left: &str, right: &str) -> bool {
    left.trim().to_lowercase() == right.trim().to_lowercase()
}

/// 9 savolning to'liqligi. `has_schedule` — LOAN uchun qaytarish jadvali bormi.
pub fn completeness(
    kind: AgreementType,
    answers: &AgreementAnswers,
    has_schedule: bool,
) -> Completeness {
    let mut missing: Vec<u8> = Vec::new();
    let mut errors: Vec<&'static str> = Vec::new();
    let parties = &answers.parties;
    let is_party = |id: &str| parties.iter().any(|party| party.id == id);

    // 1. Kim bilan kim? Kamida ikki tomon.
    if parties.len() < 2 {
        missing.push(1);
        if parties.len() == 1 {
            add_error(&mut errors, "PARTIES_MIN_2");
        }
    }

    // 2. Kim nima qo'shyapti? Har bir tomonda kamida bitta hissa.
    let mut contributions_ok = !parties.is_empty();
    for party in parties {
        if !answers
            .contributions
            .iter()
            .any(|contribution| contribution.party_id == party.id)
        {
            contributions_ok = false;
            add_error(&mut errors, "CONTRIBUTION_MISSING");
        }
    }
    if !contributions_ok {
        missing.push(2);
    }

    // 3. Kim nima qiladi? LOAN — qaytarish jadvali; boshqalari — egasi va «bajarilmasa» bandi bor vazifalar.
    if kind == AgreementType::Loan {
        if !has_schedule {
            missing.push(3);
        }
    } else {
        let mut duties_ok = !answers.duties.is_empty();
        for duty in &answers.duties {
            let owned = duty.owner_party_id.as_deref().is_some_and(is_party);
            if !owned {
                duties_ok = false;
                add_error(&mut errors, "DUTY_WITHOUT_OWNER");
            }
            if duty.breach_clause.trim().is_empty() {
                duties_ok = false;
                add_error(&mut errors, "DUTY_WITHOUT_BREACH_CLAUSE");
            }
        }
        if !duties_ok {
            missing.push(3);
        }
    }

    // 4. Foyda qanday bo'linadi? Faqat foiz (bp), yig'indisi 100%.
    let profit_ok = if kind == AgreementType::Loan {
        true
    } else if let Some(reason) = &answers.profit_not_applicable {
        if reason.trim().is_empty() {
            add_error(&mut errors, "NA_REASON_REQUIRED");
            false
        } else {
            kind == AgreementType::Family
        }
    } else if answers.profit.fixed_amount.is_some() {
        if kind == AgreementType::Partnership {
            add_error(&mut errors, "GUARANTEED_RETURN_FORBIDDEN");
            false
        } else {
            true
        }
    } else if answers.profit.shares.is_empty() {
        false
    } else {
        let total: i64 = answers.profit.shares.values().sum();
        if total == FULL_SHARE_BP {
            true
        } else {
            add_error(&mut errors, "PROFIT_SHARES_NOT_100");
            false
        }
    };
    if !profit_ok {
        missing.push(4);
    }

    // 5. Zarar ko'rilsa nima bo'ladi? Matn yoki (FAMILY da) izohli «tegishli emas».
    let loss_ok = if kind == AgreementType::Loan {
        true
    } else if let Some(reason) = &answers.loss_not_applicable {
        if reason.trim().is_empty() {
            add_error(&mut errors, "NA_REASON_REQUIRED");
            false
        } else {
            kind == AgreementType::Family
        }
    } else {
        !answers.loss_text.trim().is_empty()
    };
    if !loss_ok {
        missing.push(5);
    }

    // 6. Pul qayerda, hisobni kim yuritadi? Joy va hisob yurituvchi tomon (ikkinchi tomon ko'rib chiqadi).
    let custody_ok = !answers.custody.location.trim().is_empty()
        && answers
            .custody
            .keeper_party_id
            .as_deref()
            .is_some_and(is_party)
        && answers.custody.review_every_days > 0;
    if !custody_ok {
        missing.push(6);
    }

    // 7. Qanday ajralib chiqiladi? «Tegishli emas» izohli bo'lishi shart; aks holda hamma maydon to'ladi.
    let exit_ok = if let Some(reason) = &answers.exit_not_applicable {
        if reason.trim().is_empty() {
            add_error(&mut errors, "NA_REASON_REQUIRED");
            false
        } else {
            true
        }
    } else {
        answers.exit.notice_days > 0
            && !answers.exit.valuation.trim().is_empty()
            && !answers.exit.payout.trim().is_empty()
    };
    if !exit_ok {
        missing.push(7);
    }

    // 8. Kelisha olmasangiz, kim hakam? Tomonlardan biri bo'lmasligi shart. FAMILY da ixtiyoriy.
    let arbiter_ok = match &answers.arbiter {
        None => kind == AgreementType::Family,
        Some(arbiter) => {
            if arbiter.name.trim().is_empty() {
                false
            } else if parties
                .iter()
                .any(|party| same_name(&party.name, &arbiter.name))
            {
                add_error(&mut errors, "ARBITER_IS_PARTY");
                false
            } else {
                true
            }
        }
    };
    if !arbiter_ok {
        missing.push(8);
    }

    // 9. Qachon yangilanadi? Muddat va keyingi ko'rib chiqish sanasi.
    if answers.term.term_months <= 0 || answers.term.review_date.is_none() {
        missing.push(9);
    }

    Completeness {
        complete: missing.is_empty(),
        missing,
        errors,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    fn full_answers() -> AgreementAnswers {
        let mut shares = BTreeMap::new();
        shares.insert("P1".to_owned(), 5_000);
        shares.insert("P2".to_owned(), 5_000);
        AgreementAnswers {
            profit_not_applicable: None,
            loss_not_applicable: None,
            exit_not_applicable: None,
            parties: vec![party("P1", "Akmal Karimov"), party("P2", "Jasur Rahimov")],
            contributions: vec![contribution("P1"), contribution("P2")],
            duties: vec![Duty {
                id: "d1".to_owned(),
                title: "Yetkazish".to_owned(),
                owner_party_id: Some("P1".to_owned()),
                breach_clause: "1 kun ichida xabar beradi".to_owned(),
            }],
            profit: ProfitRule {
                shares,
                fixed_amount: None,
                text: String::new(),
            },
            loss_text: "Zarar kapitalga mutanosib".to_owned(),
            custody: Custody {
                location: "Umumiy karta".to_owned(),
                keeper_party_id: Some("P1".to_owned()),
                keeper_device_id: None,
                review_every_days: 30,
            },
            exit: ExitClause {
                notice_days: 30,
                valuation: "Oxirgi ko'rik bo'yicha".to_owned(),
                payout: "3 oy ichida".to_owned(),
                assets: String::new(),
            },
            arbiter: Some(Arbiter {
                name: "Shavkat aka".to_owned(),
                role: "mahalla oqsoqoli".to_owned(),
            }),
            term: Term {
                term_months: 12,
                review_date: Some(time::macros::date!(2027 - 10 - 01)),
            },
        }
    }

    fn party(id: &str, name: &str) -> Party {
        Party {
            id: id.to_owned(),
            name: name.to_owned(),
            role: "sherik".to_owned(),
            relation: String::new(),
            is_me: id == "P1",
        }
    }

    fn contribution(party_id: &str) -> Contribution {
        Contribution {
            party_id: party_id.to_owned(),
            kind: "money".to_owned(),
            amount: Some(Money::new(300_000_000, Currency::Uzs)),
            description: "naqd".to_owned(),
        }
    }

    #[test]
    fn tur_kodlari_qaytariladi() {
        for kind in [
            AgreementType::Loan,
            AgreementType::Partnership,
            AgreementType::Family,
            AgreementType::Other,
        ] {
            assert_eq!(AgreementType::from_code(kind.code()), Some(kind));
        }
    }

    #[test]
    fn toliq_javoblar_9_9() {
        let result = completeness(AgreementType::Partnership, &full_answers(), false);
        assert!(result.complete);
        assert!(result.missing.is_empty());
    }

    #[test]
    fn oilaviy_kelishuvda_hakam_shart_emas() {
        let mut answers = full_answers();
        answers.arbiter = None;
        assert!(completeness(AgreementType::Family, &answers, false).complete);
        assert_eq!(
            completeness(AgreementType::Partnership, &answers, false).missing,
            vec![8]
        );
    }
}
