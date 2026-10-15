use std::collections::BTreeSet;

use serde::Serialize;

use crate::{AgreementDraft, AgreementType, Answer};

pub const QUESTION_COUNT: u8 = 9;
/// Ko'rik davriyligi bundan siyrak bo'lsa — ogohlantirish (oyiga 1 martadan siyrak).
pub const REVIEW_WARN_AFTER_DAYS: u32 = 31;

/// To'liqlik natijasi: «N / 9», javobsiz savollar raqamlari, xatolar va ogohlantirishlar.
#[derive(Clone, Debug, PartialEq, Eq, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct Completeness {
    pub answered: u8,
    pub complete: bool,
    pub can_sign: bool,
    pub missing: Vec<u8>,
    pub errors: Vec<&'static str>,
    pub warnings: Vec<&'static str>,
}

const ALL_WORDS: [&str; 4] = ["hamma", "hammasi", "barcha", "все"];

fn is_everyone(id: &str) -> bool {
    let t = id.trim().to_lowercase();
    t == "*" || t == "all" || ALL_WORDS.contains(&t.as_str())
}

/// Tur bo'yicha avtomatik javoblar (strategy): LOAN uchun 4–5-savollar «foiz yo'q»,
/// FAMILY uchun hakam ixtiyoriy.
fn auto_not_applicable(kind: AgreementType, question: u8) -> bool {
    matches!(
        (kind, question),
        (AgreementType::Loan, 4 | 5) | (AgreementType::Family, 8)
    )
}

struct Checker {
    answered: u8,
    missing: Vec<u8>,
    errors: BTreeSet<&'static str>,
    warnings: BTreeSet<&'static str>,
}

impl Checker {
    fn status<T>(&mut self, kind: AgreementType, n: u8, a: &Answer<T>) -> bool {
        match a {
            Answer::Answered { .. } => {
                self.answered += 1;
                true
            }
            Answer::NotApplicable { reason } => {
                if reason.trim().is_empty() {
                    self.errors.insert("NA_REASON_REQUIRED");
                    self.missing.push(n);
                } else {
                    self.answered += 1;
                }
                false
            }
            Answer::Unanswered if auto_not_applicable(kind, n) => {
                self.answered += 1;
                false
            }
            Answer::Unanswered => {
                self.missing.push(n);
                false
            }
        }
    }
}

/// 9 savol bo'yicha to'liqlik va validatsiya (uy/SPEC 2F.2). 9/9 va xatosiz bo'lmaguncha
/// imzolash ochilmaydi (`can_sign`).
pub fn check_completeness(kind: AgreementType, d: &AgreementDraft) -> Completeness {
    let mut c = Checker {
        answered: 0,
        missing: Vec::new(),
        errors: BTreeSet::new(),
        warnings: BTreeSet::new(),
    };

    // 1. Kim bilan kim?
    let mut party_ids: BTreeSet<&str> = BTreeSet::new();
    let mut party_names: BTreeSet<String> = BTreeSet::new();
    if c.status(kind, 1, &d.parties) {
        if let Some(parties) = d.parties.value() {
            if parties.len() < 2 {
                c.errors.insert("MIN_TWO_PARTIES");
            }
            for p in parties {
                if p.full_name.trim().is_empty() {
                    c.errors.insert("PARTY_NAME_REQUIRED");
                }
                party_ids.insert(p.id.as_str());
                party_names.insert(p.full_name.trim().to_lowercase());
            }
        }
    }
    let known = |id: &str| party_ids.is_empty() || party_ids.contains(id);

    // 2. Kim nima qo'shyapti?
    if c.status(kind, 2, &d.contributions) {
        if let Some(list) = d.contributions.value() {
            if list.is_empty() {
                c.errors.insert("CONTRIBUTION_MISSING");
            }
            for x in list {
                if !known(&x.party_id) {
                    c.errors.insert("UNKNOWN_PARTY");
                }
            }
            if kind == AgreementType::Partnership {
                let contributors: BTreeSet<&str> =
                    list.iter().map(|x| x.party_id.as_str()).collect();
                if party_ids.iter().any(|p| !contributors.contains(p)) {
                    c.errors.insert("CONTRIBUTION_MISSING");
                }
            }
        }
    }

    // 3. Kim nima qiladi? — yagona mas'ul va «bajarilmasa» bandi.
    if c.status(kind, 3, &d.duties) {
        if let Some(duties) = d.duties.value() {
            for duty in duties {
                match duty.owner_party_id.as_deref() {
                    None => {
                        c.errors.insert("DUTY_WITHOUT_OWNER");
                    }
                    Some(o) if o.trim().is_empty() || is_everyone(o) => {
                        c.errors.insert("DUTY_WITHOUT_OWNER");
                    }
                    Some(o) if !known(o) => {
                        c.errors.insert("UNKNOWN_PARTY");
                    }
                    Some(_) => {}
                }
                if duty
                    .breach_clause
                    .as_deref()
                    .is_none_or(|b| b.trim().is_empty())
                {
                    c.errors.insert("BREACH_CLAUSE_REQUIRED");
                }
            }
        }
    }

    // 4. Foyda — faqat bp; sheriklikda qat'iy summa taqiqlanadi.
    if c.status(kind, 4, &d.profit_rule) {
        if let Some(rule) = d.profit_rule.value() {
            if rule.fixed_amount_minor.is_some() {
                c.errors.insert(if kind == AgreementType::Loan {
                    "INTEREST_FORBIDDEN"
                } else {
                    "GUARANTEED_RETURN_FORBIDDEN"
                });
            }
            let sum: i64 = rule.shares.iter().map(|s| s.share_bp).sum();
            if rule.shares.iter().any(|s| s.share_bp < 0)
                || (!rule.shares.is_empty() && sum != 10_000)
            {
                c.errors.insert("PROFIT_SHARES_NOT_100");
            }
            if rule.shares.iter().any(|s| !known(&s.party_id)) {
                c.errors.insert("UNKNOWN_PARTY");
            }
            if kind == AgreementType::Loan {
                c.errors.insert("INTEREST_FORBIDDEN");
            }
        }
    }

    // 5. Zarar.
    c.status(kind, 5, &d.loss_rule);

    // 6. Pul qayerda, hisobni kim yuritadi, qachon ko'riladi.
    if c.status(kind, 6, &d.custody) {
        if let Some(cu) = d.custody.value() {
            if !known(&cu.keeper_party_id) {
                c.errors.insert("UNKNOWN_PARTY");
            }
            if cu.review_every_days == 0 {
                c.errors.insert("REVIEW_PERIOD_REQUIRED");
            } else if cu.review_every_days > REVIEW_WARN_AFTER_DAYS {
                c.warnings.insert("REVIEW_TOO_RARE");
            }
        }
    }

    // 7. Ajralib chiqish.
    c.status(kind, 7, &d.exit_clause);

    // 8. Hakam — tomonlardan biri bo'lmasligi kerak.
    if c.status(kind, 8, &d.arbiter) {
        if let Some(a) = d.arbiter.value() {
            let by_id = a
                .party_id
                .as_deref()
                .is_some_and(|id| party_ids.contains(id));
            let by_name = party_names.contains(&a.full_name.trim().to_lowercase());
            if by_id || by_name {
                c.errors.insert("ARBITER_IS_PARTY");
            }
        }
    }

    // 9. Qachon yangilanadi.
    c.status(kind, 9, &d.term);

    c.missing.sort_unstable();
    c.missing.dedup();
    let complete = c.missing.is_empty() && c.answered == QUESTION_COUNT;
    let errors: Vec<&'static str> = c.errors.into_iter().collect();
    Completeness {
        answered: c.answered,
        complete,
        can_sign: complete && errors.is_empty(),
        missing: c.missing,
        errors,
        warnings: c.warnings.into_iter().collect(),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::*;

    fn answered<T>(value: T) -> Answer<T> {
        Answer::Answered { value }
    }

    fn party(id: &str, name: &str) -> Party {
        Party {
            id: id.into(),
            full_name: name.into(),
            role: None,
        }
    }

    fn musharaka() -> AgreementDraft {
        AgreementDraft {
            parties: answered(vec![
                party("P1", "Anvar Karimov"),
                party("P2", "Dilshod Rahimov"),
            ]),
            contributions: answered(vec![
                Contribution {
                    party_id: "P1".into(),
                    kind: ContributionKind::Money,
                    description: "naqd".into(),
                    amount_minor: Some("300000000".into()),
                    currency: Some("UZS".into()),
                },
                Contribution {
                    party_id: "P2".into(),
                    kind: ContributionKind::Money,
                    description: "naqd".into(),
                    amount_minor: Some("300000000".into()),
                    currency: Some("UZS".into()),
                },
            ]),
            duties: answered(vec![Duty {
                id: "d1".into(),
                title: "Botni yuritish".into(),
                owner_party_id: Some("P2".into()),
                breach_clause: Some("1 kun ichida xabar beradi".into()),
            }]),
            profit_rule: answered(ProfitRule {
                shares: vec![
                    ProfitShare {
                        party_id: "P1".into(),
                        share_bp: 5000,
                    },
                    ProfitShare {
                        party_id: "P2".into(),
                        share_bp: 5000,
                    },
                ],
                fixed_amount_minor: None,
            }),
            loss_rule: answered(LossRule {
                kind: LossRuleKind::ProportionalToCapital,
                note: None,
            }),
            custody: answered(Custody {
                location: "Karta".into(),
                keeper_party_id: "P1".into(),
                review_every_days: 30,
                keeper_device_id: None,
            }),
            exit_clause: answered(ExitClause {
                notice_days: 30,
                valuation_method: "Kitob qiymati".into(),
                payout_terms: "3 oyda".into(),
                asset_split: None,
            }),
            arbiter: answered(Arbiter {
                full_name: "Sobir hoji".into(),
                role: None,
                party_id: None,
            }),
            term: answered(Term {
                effective_from: "2026-10-01".into(),
                duration_months: Some(12),
                review_date: "2027-10-01".into(),
            }),
        }
    }

    #[test]
    fn complete_partnership_can_sign() {
        let c = check_completeness(AgreementType::Partnership, &musharaka());
        assert_eq!((c.answered, c.complete, c.can_sign), (9, true, true));
        assert!(c.errors.is_empty() && c.warnings.is_empty());
    }

    #[test]
    fn validation_errors() {
        let mut d = musharaka();
        d.duties = answered(vec![Duty {
            id: "d1".into(),
            title: "x".into(),
            owner_party_id: Some("hamma".into()),
            breach_clause: None,
        }]);
        d.arbiter = answered(Arbiter {
            full_name: "anvar karimov".into(),
            role: None,
            party_id: None,
        });
        d.profit_rule = answered(ProfitRule {
            shares: vec![],
            fixed_amount_minor: Some("50000000".into()),
        });
        let c = check_completeness(AgreementType::Partnership, &d);
        assert!(c.complete && !c.can_sign);
        assert_eq!(
            c.errors,
            vec![
                "ARBITER_IS_PARTY",
                "BREACH_CLAUSE_REQUIRED",
                "DUTY_WITHOUT_OWNER",
                "GUARANTEED_RETURN_FORBIDDEN"
            ]
        );
    }

    #[test]
    fn missing_and_na_reason() {
        let mut d = musharaka();
        d.exit_clause = Answer::Unanswered;
        d.arbiter = Answer::NotApplicable { reason: " ".into() };
        let c = check_completeness(AgreementType::Partnership, &d);
        assert_eq!((c.answered, c.complete), (7, false));
        assert_eq!(c.missing, vec![7, 8]);
        assert_eq!(c.errors, vec!["NA_REASON_REQUIRED"]);
    }

    #[test]
    fn loan_and_family_strategies() {
        let mut d = musharaka();
        d.profit_rule = Answer::Unanswered;
        d.loss_rule = Answer::Unanswered;
        let c = check_completeness(AgreementType::Loan, &d);
        assert!(c.can_sign, "{c:?}");
        d.arbiter = Answer::Unanswered;
        assert!(!check_completeness(AgreementType::Loan, &d).complete);
        assert!(
            check_completeness(AgreementType::Family, &{
                let mut f = musharaka();
                f.arbiter = Answer::Unanswered;
                f
            })
            .complete
        );
    }

    #[test]
    fn rare_review_warns() {
        let mut d = musharaka();
        d.custody = answered(Custody {
            location: "x".into(),
            keeper_party_id: "P1".into(),
            review_every_days: 90,
            keeper_device_id: None,
        });
        let c = check_completeness(AgreementType::Partnership, &d);
        assert!(c.can_sign);
        assert_eq!(c.warnings, vec!["REVIEW_TOO_RARE"]);
    }

    #[test]
    fn serde_shape() {
        let json = serde_json::to_value(&musharaka().arbiter).unwrap();
        assert_eq!(json["status"], "ANSWERED");
        assert_eq!(json["value"]["fullName"], "Sobir hoji");
        let na: Answer<Arbiter> =
            serde_json::from_str(r#"{"status":"NOT_APPLICABLE","reason":"oilaviy"}"#).unwrap();
        assert_eq!(
            na,
            Answer::NotApplicable {
                reason: "oilaviy".into()
            }
        );
    }
}
