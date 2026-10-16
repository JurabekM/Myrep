//! 5-qonun use-case'lari (U11): sheriklik (mudoraba / musharaka), shartnoma ustasi
//! (`Agreement(type = PARTNERSHIP)`, 9 savol), versiyalar va shu qurilmada chizilgan imzolar,
//! buyout jadvali, tayyorgarlik darvozasi va kapital qabul qilishda oilaviy rozilik.
//!
//! Qoidalar `domain-uy::partnership` da (vektorlar `partnership_rules`, `buyout_schedule`),
//! 9 savol — `baraka_agreements::check_completeness`. Shartnomasiz sheriklik ochilmaydi:
//! `ACTIVE` faqat to'liq imzolangan versiyadan keyin. Matn o'zgarsa — yangi versiya va imzolar
//! qayta so'raladi; versiyalar va imzolar DB darajasida o'zgarmas (dalil).
use std::collections::BTreeSet;
use std::sync::OnceLock;

use baraka_agreements::{
    check_completeness, signature_svg, validate_signature, AgreementDraft, AgreementType, Answer,
    Arbiter, Contribution, ContributionKind, Custody, Duty, ExitClause, LossRule as AgrLossRule,
    LossRuleKind, Party, ProfitRule, ProfitShare, Stroke, Term,
};
use baraka_domain_common::{month_period, MemberRole};
use baraka_domain_uy::emergency::{coverage_centi_months, emergency_target, FULL_TARGET_MONTHS};
use baraka_domain_uy::gate::{evaluate_gate, GateInput, GatePolicy};
use baraka_domain_uy::partnership::{
    buyout_schedule, check_rules, BuyoutInput, BuyoutSchedule, CapitalItem, CapitalKind,
    PartnerRole, PartnerTerms, PartnershipKind, RulesInput, RulesResult,
};
use baraka_journal::{short_code, EntryKind, JournalAmount, JournalEntry};
use baraka_money::{format, format_percent_bp, Currency, Money, BP_ONE};
use baraka_pdf::{
    ContractBuyout, ContractBuyoutRow, ContractCapital, ContractClause, ContractDuty,
    ContractParty, ContractSigner, PartnershipContract, PdfEngine,
};
use baraka_storage::repo::partnerships::{
    self as repo, ConsentRow, PartnershipRow, SignatureRow, VersionRow,
};
use baraka_storage::repo::{
    agreements, categories, debts, expenses, household, journal, recovery, vault,
};
use baraka_storage::SpaceScope;
use chrono::{Days, NaiveDate};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use crate::app::Ctx;
use crate::debts::row_is_ribo;
use crate::events::Topic;
use crate::receipt::{amount_in, date, pdf_locale, positive, ymd};
use crate::text::{clean, clean_opt, required};
use crate::*;

/// Shablon hali yurist va ulamo tomonidan tekshirilmagan (MVP_PLAN, Vazifa 13).
pub const TEMPLATE_REVIEW: &str = "PENDING";
const MAX_PARTIES: usize = 10;
const MAX_WITNESSES: usize = 6;
const DRAFT: &str = "DRAFT";
const SIGNED: &str = "SIGNED";
const ACTIVE: &str = "ACTIVE";
const CLOSED: &str = "CLOSED";
/// Darvoza uchun o'rtacha zarur xarajat shuncha oxirgi to'liq davrdan olinadi.
const ESSENTIAL_MONTHS: u32 = 3;

pub(crate) fn engine() -> &'static PdfEngine {
    static ENGINE: OnceLock<PdfEngine> = OnceLock::new();
    ENGINE.get_or_init(PdfEngine::new)
}

fn show(d: &str) -> String {
    NaiveDate::parse_from_str(d, "%Y-%m-%d")
        .map_or_else(|_| d.to_string(), |x| x.format("%d.%m.%Y").to_string())
}

fn pct(bp: i64) -> String {
    format!("{}%", format_percent_bp(bp))
}

fn bp32(bp: i64) -> Result<i32, AppError> {
    i32::try_from(bp).map_err(|_| AppError::new("OVERFLOW"))
}

fn no32(n: i64) -> Result<u32, AppError> {
    u32::try_from(n).map_err(|_| AppError::new("CORRUPT_ROW"))
}

fn hex(bytes: &[u8]) -> String {
    bytes.iter().map(|b| format!("{b:02x}")).collect()
}

// ---- saqlanadigan shartnoma matni (`agreements.payload_json`, versiyalarda nusxasi) ----

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct CapitalP {
    pub(crate) kind: String,
    pub(crate) description: String,
    pub(crate) amount_minor: i64,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct PartyP {
    pub(crate) id: String,
    pub(crate) full_name: String,
    pub(crate) role: String,
    pub(crate) profit_share_bp: i64,
    pub(crate) is_me: bool,
    pub(crate) capital: Vec<CapitalP>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct BuyoutP {
    pub(crate) seller_party_id: String,
    pub(crate) buyer_party_id: String,
    pub(crate) units: u32,
    pub(crate) units_per_period: u32,
    pub(crate) period_months: u32,
    pub(crate) start: String,
    pub(crate) expected_profit_minor: Option<i64>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub(crate) struct Payload {
    pub(crate) kind: String,
    pub(crate) title: String,
    pub(crate) currency: String,
    pub(crate) parties: Vec<PartyP>,
    pub(crate) duties: Answer<Vec<Duty>>,
    pub(crate) negligence_clause: Option<String>,
    pub(crate) custody: Answer<Custody>,
    pub(crate) exit_clause: Answer<ExitClause>,
    pub(crate) arbiter: Answer<Arbiter>,
    pub(crate) term: Answer<Term>,
    pub(crate) witnesses: Vec<String>,
    pub(crate) buyout: Option<BuyoutP>,
}

impl Payload {
    pub(crate) fn hash(&self) -> Result<String, AppError> {
        let bytes = serde_json::to_vec(self).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        Ok(hex(&Sha256::digest(&bytes)))
    }

    pub(crate) fn kind(&self) -> Result<PartnershipKind, AppError> {
        PartnershipKind::parse(&self.kind).ok_or(AppError::new("CORRUPT_ROW"))
    }

    pub(crate) fn me(&self) -> Option<&PartyP> {
        self.parties.iter().find(|p| p.is_me)
    }

    pub(crate) fn party_name(&self, id: &str) -> String {
        self.parties
            .iter()
            .find(|p| p.id == id)
            .map_or_else(|| id.to_string(), |p| p.full_name.clone())
    }

    pub(crate) fn capital_of(p: &PartyP) -> i64 {
        p.capital.iter().map(|c| c.amount_minor).sum()
    }

    /// Kim imzolashi kerak: barcha tomonlar, guvohlar va hakam (2F.3).
    pub(crate) fn required_signers(&self) -> Vec<(String, &'static str, String)> {
        let mut out: Vec<(String, &'static str, String)> = self
            .parties
            .iter()
            .map(|p| (format!("party:{}", p.id), "PARTY", p.full_name.clone()))
            .collect();
        for (i, w) in self.witnesses.iter().enumerate() {
            out.push((format!("witness:{i}"), "WITNESS", w.clone()));
        }
        if let Some(a) = self.arbiter.value() {
            out.push(("arbiter".into(), "ARBITER", a.full_name.clone()));
        }
        out
    }

    /// 9 savol strukturasi: 1, 2, 4, 5-savollar sheriklik shartlaridan avtomatik yig'iladi.
    fn draft(&self) -> AgreementDraft {
        let parties = self
            .parties
            .iter()
            .map(|p| Party {
                id: p.id.clone(),
                full_name: p.full_name.clone(),
                role: Some(p.role.clone()),
            })
            .collect();
        let mut contributions = Vec::new();
        for p in &self.parties {
            for c in &p.capital {
                contributions.push(Contribution {
                    party_id: p.id.clone(),
                    kind: if c.kind == CapitalKind::Equipment.as_str() {
                        ContributionKind::Goods
                    } else {
                        ContributionKind::Money
                    },
                    description: c.description.clone(),
                    amount_minor: Some(c.amount_minor.to_string()),
                    currency: Some(self.currency.clone()),
                });
            }
            if PartnerRole::parse(&p.role).is_some_and(PartnerRole::works) {
                contributions.push(Contribution {
                    party_id: p.id.clone(),
                    kind: ContributionKind::Labor,
                    description: "LABOR".into(),
                    amount_minor: None,
                    currency: None,
                });
            }
        }
        let has = !self.parties.is_empty();
        let answered = |value| {
            if has {
                Answer::Answered { value }
            } else {
                Answer::Unanswered
            }
        };
        let profit_rule = ProfitRule {
            shares: self
                .parties
                .iter()
                .map(|p| ProfitShare {
                    party_id: p.id.clone(),
                    share_bp: p.profit_share_bp,
                })
                .collect(),
            fixed_amount_minor: None,
        };
        let loss_rule = AgrLossRule {
            kind: match self.kind() {
                Ok(PartnershipKind::Mudaraba) => LossRuleKind::CapitalProviderBears,
                _ => LossRuleKind::ProportionalToCapital,
            },
            note: self.negligence_clause.clone(),
        };
        AgreementDraft {
            parties: answered(parties),
            contributions: if has {
                Answer::Answered {
                    value: contributions,
                }
            } else {
                Answer::Unanswered
            },
            duties: self.duties.clone(),
            profit_rule: if has {
                Answer::Answered { value: profit_rule }
            } else {
                Answer::Unanswered
            },
            loss_rule: if has {
                Answer::Answered { value: loss_rule }
            } else {
                Answer::Unanswered
            },
            custody: self.custody.clone(),
            exit_clause: self.exit_clause.clone(),
            arbiter: self.arbiter.clone(),
            term: self.term.clone(),
        }
    }

    pub(crate) fn rules(&self, cur: Currency) -> Result<RulesResult, AppError> {
        let kind = self.kind()?;
        let partners = self
            .parties
            .iter()
            .map(|p| {
                Ok(PartnerTerms {
                    role: PartnerRole::parse(&p.role).ok_or(AppError::new("CORRUPT_ROW"))?,
                    profit_share_bp: p.profit_share_bp,
                    capital_items: p
                        .capital
                        .iter()
                        .map(|c| {
                            Ok(CapitalItem {
                                kind: CapitalKind::parse(&c.kind)
                                    .ok_or(AppError::new("CORRUPT_ROW"))?,
                                description: c.description.clone(),
                                amount: Money::new(c.amount_minor, cur),
                            })
                        })
                        .collect::<Result<_, AppError>>()?,
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        // 9-savol javobsiz bo'lsa, bu `missing` da ko'rinadi; muddat qoidasi (`TERM_REQUIRED`)
        // faqat javob yoki «tegishli emas» bo'lganda tekshiriladi — zarar ulushlari esa usta
        // davomida ham ko'rinib turadi.
        let duration = match &self.term {
            Answer::Unanswered => Some(1),
            a => a.value().and_then(|t| t.duration_months),
        };
        Ok(check_rules(&RulesInput {
            kind,
            currency: cur,
            partners,
            fixed_return: None,
            loss_rule: kind.loss_rule(),
            duration_months: duration,
        })?)
    }

    pub(crate) fn buyout(
        &self,
        cur: Currency,
    ) -> Result<Option<Result<BuyoutSchedule, String>>, AppError> {
        let Some(b) = &self.buyout else {
            return Ok(None);
        };
        let total: i64 = self.parties.iter().map(Self::capital_of).sum();
        let find = |id: &str| self.parties.iter().find(|p| p.id == id);
        let (Some(seller), Some(buyer)) = (find(&b.seller_party_id), find(&b.buyer_party_id))
        else {
            return Ok(Some(Err("UNKNOWN_PARTY".into())));
        };
        let start = NaiveDate::parse_from_str(&b.start, "%Y-%m-%d")
            .map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let input = BuyoutInput {
            stake: Money::new(Self::capital_of(seller), cur),
            total_capital: Money::new(total, cur),
            buyer_capital: Money::new(Self::capital_of(buyer), cur),
            units: b.units,
            units_per_period: b.units_per_period,
            start,
            period_months: b.period_months,
            expected_profit: b.expected_profit_minor.map(|m| Money::new(m, cur)),
            buyer_share_bp: buyer.profit_share_bp,
        };
        Ok(Some(
            buyout_schedule(&input).map_err(|e| e.code.to_string()),
        ))
    }
}

/// Hisoblangan ko'rinish: tekshiruv, versiya va imzolar.
pub(crate) struct View {
    pub(crate) row: PartnershipRow,
    pub(crate) payload: Payload,
    pub(crate) cur: Currency,
    pub(crate) hash: String,
    pub(crate) rules: RulesResult,
    pub(crate) check: ContractCheckDto,
    pub(crate) buyout: Option<Result<BuyoutSchedule, String>>,
    pub(crate) versions: Vec<VersionRow>,
    /// Joriy matnga mos versiya.
    pub(crate) current: Option<VersionRow>,
    pub(crate) signatures: Vec<SignatureRow>,
}

impl View {
    pub(crate) fn all_signed(&self) -> bool {
        self.current.is_some()
            && self
                .payload
                .required_signers()
                .iter()
                .all(|(k, _, _)| self.signatures.iter().any(|s| &s.signer_key == k))
    }

    fn me_provides_capital(&self) -> bool {
        self.payload
            .me()
            .is_some_and(|m| Payload::capital_of(m) > 0)
    }

    /// Mehnat egasi sifatida boshqa tomon kapitalini qabul qiladi (2E.6).
    fn me_receives_capital(&self) -> bool {
        self.payload.me().is_some_and(|m| {
            PartnerRole::parse(&m.role).is_some_and(PartnerRole::works)
                && self
                    .payload
                    .parties
                    .iter()
                    .any(|p| p.id != m.id && Payload::capital_of(p) > 0)
        })
    }
}

impl App {
    pub(crate) fn partnership_row(
        &self,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<PartnershipRow, AppError> {
        self.db
            .read(|c| repo::get(c, scope, id))?
            .ok_or(AppError::on("NOT_FOUND", "partnershipId"))
    }

    pub(crate) fn load_payload(
        &self,
        scope: &SpaceScope,
        row: &PartnershipRow,
    ) -> Result<Payload, AppError> {
        let json = self
            .db
            .read(|c| agreements::payload(c, scope, &row.agreement_id))?
            .ok_or(AppError::new("CORRUPT_ROW"))?;
        serde_json::from_str(&json).map_err(|_| AppError::new("CORRUPT_ROW"))
    }

    pub(crate) fn partnership_view(
        &self,
        scope: &SpaceScope,
        row: PartnershipRow,
    ) -> Result<View, AppError> {
        let payload = self.load_payload(scope, &row)?;
        let cur = Currency::from_code(&payload.currency)?;
        let hash = payload.hash()?;
        let rules = payload.rules(cur)?;
        let buyout = payload.buyout(cur)?;
        let completeness = check_completeness(AgreementType::Partnership, &payload.draft());
        let mut errors: BTreeSet<String> = completeness
            .errors
            .iter()
            .map(|e| (*e).to_string())
            .collect();
        // 9 savol `MIN_TWO_PARTIES` ni beradi — bir ma'noli kod ikki marta chiqmasin.
        errors.extend(
            rules
                .errors
                .iter()
                .filter(|e| **e != "MIN_TWO_PARTNERS")
                .map(|e| (*e).to_string()),
        );
        if payload.parties.iter().filter(|p| p.is_me).count() != 1 {
            errors.insert("ME_PARTY_REQUIRED".into());
        }
        if let Some(Err(_)) = &buyout {
            errors.insert("BUYOUT_INVALID".into());
        }
        let mut warnings: BTreeSet<String> = completeness
            .warnings
            .iter()
            .chain(rules.warnings.iter())
            .map(|w| (*w).to_string())
            .collect();
        if payload.witnesses.is_empty() {
            warnings.insert("NO_WITNESSES".into());
        }
        let check = ContractCheckDto {
            answered: completeness.answered,
            complete: completeness.complete,
            can_sign: completeness.complete && errors.is_empty(),
            missing: completeness.missing,
            errors: errors.into_iter().collect(),
            warnings: warnings.into_iter().collect(),
        };
        let versions = self
            .db
            .read(|c| repo::versions(c, scope, &row.agreement_id))?;
        let current = versions.last().filter(|v| v.payload_hash == hash).cloned();
        let signatures = match &current {
            Some(v) => self.db.read(|c| repo::signatures(c, scope, &v.id))?,
            None => Vec::new(),
        };
        Ok(View {
            row,
            payload,
            cur,
            hash,
            rules,
            check,
            buyout,
            versions,
            current,
            signatures,
        })
    }

    /// Tayyorgarlik darvozasi: qorovul pul (Kelajagim balansi) / oxirgi to'liq davrlardagi
    /// o'rtacha zarur xarajat (ZARUR + KERAK), foizli qarz va «Qarzdan chiqish» rejimi.
    fn gate(&self, ctx: &Ctx, scope: &SpaceScope) -> Result<GateDto, AppError> {
        let cur = ctx.currency;
        let asset = self.vault_asset(scope)?;
        let balance = Money::new(self.db.read(|c| vault::balance(c, scope, &asset.id))?, cur);
        let cats = self.db.read(|c| categories::list(c, scope))?;
        let today = self.today(ctx);
        let (mut start, _) =
            month_period(today, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
        let mut months = Vec::new();
        for _ in 0..ESSENTIAL_MONTHS {
            let prev = start
                .checked_sub_days(Days::new(1))
                .ok_or(AppError::new("INVALID_PERIOD"))?;
            let (s, e) =
                month_period(prev, ctx.month_start_day).ok_or(AppError::new("INVALID_PERIOD"))?;
            let rows = self
                .db
                .read(|c| expenses::list_between(c, scope, &ymd(s), &ymd(e)))?;
            let mut sum = 0_i64;
            for r in rows.iter().filter(|r| r.currency == cur.code()) {
                let necessity = r.necessity.clone().or_else(|| {
                    cats.iter()
                        .find(|c| c.id == r.category_id)
                        .and_then(|c| c.default_necessity.clone())
                });
                if matches!(necessity.as_deref(), Some("ZARUR" | "KERAK")) {
                    sum = sum
                        .checked_add(r.amount_minor)
                        .ok_or(AppError::new("OVERFLOW"))?;
                }
            }
            months.push(Money::new(sum, cur));
            start = s;
        }
        // Xarajat yozilmagan davrlar o'rtachani buzmasin.
        let history: Vec<Money> = months.into_iter().filter(Money::is_positive).collect();
        let average = if history.is_empty() {
            None
        } else {
            Some(emergency_target(&history, 1)?)
        };
        let coverage = match average {
            Some(a) => Some(coverage_centi_months(balance, a)?),
            None => None,
        };
        let has_interest_debt = self
            .db
            .read(|c| debts::list_debts(c, scope))?
            .iter()
            .any(|d| d.status == "ACTIVE" && row_is_ribo(d));
        let has_payoff_plan = self
            .db
            .read(|c| recovery::budget(c, scope))?
            .is_some_and(|b| b.mode == "DEBT_RECOVERY");
        let policy = GatePolicy::default();
        let r = evaluate_gate(
            GateInput {
                coverage_centi_months: coverage.unwrap_or(0),
                has_interest_debt,
                has_payoff_plan,
            },
            policy,
        );
        Ok(GateDto {
            open: r.open,
            reasons: r.reasons.iter().map(|x| x.code().to_string()).collect(),
            coverage_months: coverage.map(format_percent_bp),
            required_months: FULL_TARGET_MONTHS,
            balance: self.money_dto(ctx, balance),
            monthly_essentials: average.map(|a| self.money_dto(ctx, a)),
            has_interest_debt,
            has_payoff_plan,
        })
    }

    pub(crate) fn adult_members(&self, ctx: &Ctx) -> Result<Vec<household::MemberRow>, AppError> {
        Ok(self
            .db
            .read(|db| household::list_members(db, &ctx.household_id))?
            .into_iter()
            .filter(|m| m.role == MemberRole::Adult.as_str())
            .collect())
    }

    fn consent_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        v: &View,
    ) -> Result<FamilyConsentDto, AppError> {
        let consents = self.db.read(|c| repo::consents(c, scope, &v.row.id))?;
        let adults = self.adult_members(ctx)?;
        let list: Vec<SignoffDto> = adults
            .iter()
            .map(|m| SignoffDto {
                member_id: m.id.clone(),
                name: m.display_name.clone(),
                agreed_on: consents
                    .iter()
                    .find(|c| c.member_id == m.id && Some(c.version_no) == v.row.signed_version)
                    .map(|c| c.agreed_on.clone()),
            })
            .collect();
        let complete = v.row.not_debt_ack_on.is_some()
            && !list.is_empty()
            && list.iter().all(|a| a.agreed_on.is_some());
        Ok(FamilyConsentDto {
            adults: list,
            not_debt_ack_on: v.row.not_debt_ack_on.clone(),
            complete,
        })
    }

    /// Faollashtirishni nima to'sib turibdi (DTO va `activate_partnership` uchun bir xil).
    fn activate_blocker(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        v: &View,
    ) -> Result<Option<&'static str>, AppError> {
        Ok(match v.row.status.as_str() {
            ACTIVE => Some("ALREADY_ACTIVE"),
            CLOSED => Some("PARTNERSHIP_CLOSED"),
            DRAFT => Some("NOT_SIGNED"),
            _ if v.payload.me().is_none() => Some("ME_PARTY_REQUIRED"),
            _ if v.me_provides_capital() && !self.gate(ctx, scope)?.open => Some("GATE_CLOSED"),
            _ if v.me_receives_capital() && v.row.not_debt_ack_on.is_none() => {
                Some("NOT_DEBT_ACK_REQUIRED")
            }
            _ if v.me_receives_capital() && !self.consent_dto(ctx, scope, v)?.complete => {
                Some("FAMILY_CONSENT_REQUIRED")
            }
            _ => None,
        })
    }

    fn buyout_dto(&self, ctx: &Ctx, v: &View) -> Option<BuyoutDto> {
        let b = v.payload.buyout.as_ref()?;
        let m = |x: Money| self.money_dto(ctx, x);
        let (rows, end_date, buyer_profit, error) = match &v.buyout {
            Some(Ok(s)) => (
                s.rows
                    .iter()
                    .map(|r| BuyoutRowDto {
                        period: r.period,
                        date: r.date.format("%d.%m.%Y").to_string(),
                        units: r.units,
                        payment: m(r.payment),
                        remaining: m(r.remaining_stake),
                        seller_bp: i32::try_from(r.seller_bp).unwrap_or(0),
                        seller_percent: pct(r.seller_bp),
                        buyer_bp: i32::try_from(r.buyer_bp).unwrap_or(0),
                        buyer_percent: pct(r.buyer_bp),
                        exceeds_share: r.exceeds_share,
                    })
                    .collect(),
                s.end_date().map(|d| d.format("%d.%m.%Y").to_string()),
                s.buyer_profit.map(m),
                None,
            ),
            Some(Err(code)) => (Vec::new(), None, None, Some(code.clone())),
            None => (Vec::new(), None, None, None),
        };
        Some(BuyoutDto {
            seller_party_id: b.seller_party_id.clone(),
            buyer_party_id: b.buyer_party_id.clone(),
            units: b.units,
            units_per_period: b.units_per_period,
            period_months: b.period_months,
            start: show(&b.start),
            expected_profit: b.expected_profit_minor.map(|x| m(Money::new(x, v.cur))),
            rows,
            end_date,
            buyer_profit,
            error,
        })
    }

    fn partnership_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        v: &View,
    ) -> Result<PartnershipDto, AppError> {
        let m = |x: Money| self.money_dto(ctx, x);
        let parties = v
            .payload
            .parties
            .iter()
            .enumerate()
            .map(|(i, p)| {
                Ok(PartnerDto {
                    id: p.id.clone(),
                    full_name: p.full_name.clone(),
                    role: p.role.clone(),
                    profit_share_bp: bp32(p.profit_share_bp)?,
                    profit_share: pct(p.profit_share_bp),
                    is_me: p.is_me,
                    capital_items: p
                        .capital
                        .iter()
                        .map(|c| CapitalItemDto {
                            kind: c.kind.clone(),
                            description: c.description.clone(),
                            amount: m(Money::new(c.amount_minor, v.cur)),
                        })
                        .collect(),
                    capital: m(Money::new(Payload::capital_of(p), v.cur)),
                    loss_share: v
                        .rules
                        .loss_share_bp
                        .as_ref()
                        .and_then(|l| l.get(i))
                        .map(|bp| pct(*bp)),
                })
            })
            .collect::<Result<Vec<_>, AppError>>()?;
        let total: i64 = v.payload.parties.iter().map(Payload::capital_of).sum();
        let signers = v
            .payload
            .required_signers()
            .into_iter()
            .map(|(key, role, name)| {
                let sig = v.signatures.iter().find(|s| s.signer_key == key);
                SignerDto {
                    key,
                    role: role.to_string(),
                    name,
                    signed_at: sig.map(|s| show(s.signed_at.get(..10).unwrap_or(""))),
                    svg: sig.and_then(|s| {
                        serde_json::from_str::<Vec<Stroke>>(&s.strokes_json)
                            .ok()
                            .map(|st| signature_svg(&st))
                    }),
                }
            })
            .collect();
        let mut history = Vec::new();
        for ver in &v.versions {
            let sigs = self.db.read(|c| repo::signatures(c, scope, &ver.id))?;
            let p: Payload = serde_json::from_str(&ver.payload_json)
                .map_err(|_| AppError::new("CORRUPT_ROW"))?;
            history.push(VersionInfoDto {
                no: no32(ver.version_no)?,
                created_on: show(ver.created_at.get(..10).unwrap_or("")),
                signed: u32::try_from(sigs.len()).unwrap_or(u32::MAX),
                required: u32::try_from(p.required_signers().len()).unwrap_or(u32::MAX),
                in_force: v.row.signed_version == Some(ver.version_no),
                change_note: ver.change_note.clone(),
            });
        }
        let blocker = self.activate_blocker(ctx, scope, v)?;
        let signed_hash = v
            .versions
            .iter()
            .find(|x| Some(x.version_no) == v.row.signed_version)
            .map(|x| x.payload_hash.as_str());
        Ok(PartnershipDto {
            id: v.row.id.clone(),
            agreement_id: v.row.agreement_id.clone(),
            kind: v.row.kind.clone(),
            title: v.row.title.clone(),
            status: v.row.status.clone(),
            currency: v.payload.currency.clone(),
            parties,
            capital_total: m(Money::new(total, v.cur)),
            duties: v.payload.duties.clone(),
            negligence_clause: v.payload.negligence_clause.clone(),
            custody: v.payload.custody.clone(),
            exit_clause: v.payload.exit_clause.clone(),
            arbiter: v.payload.arbiter.clone(),
            term: v.payload.term.clone(),
            witnesses: v.payload.witnesses.clone(),
            buyout: self.buyout_dto(ctx, v),
            check: v.check.clone(),
            version: v.current.as_ref().map(|c| no32(c.version_no)).transpose()?,
            signed_version: v.row.signed_version.map(no32).transpose()?,
            amendment_pending: v.row.status == ACTIVE && signed_hash != Some(v.hash.as_str()),
            signers,
            all_signed: v.all_signed(),
            me_provides_capital: v.me_provides_capital(),
            me_receives_capital: v.me_receives_capital(),
            gate: if v.me_provides_capital() {
                Some(self.gate(ctx, scope)?)
            } else {
                None
            },
            consent: if v.me_receives_capital() {
                Some(self.consent_dto(ctx, scope, v)?)
            } else {
                None
            },
            can_activate: blocker.is_none(),
            activate_blocker: blocker.map(str::to_string),
            history,
            template_review: TEMPLATE_REVIEW.into(),
            hash_code: short_code(&v.hash),
            in_dispute: self.open_dispute(scope, &v.row.id)?.is_some(),
        })
    }

    /// Ustadan kelgan shartnomani tekshirib, saqlanadigan matnga aylantiradi.
    fn parse_partnership(
        &self,
        input: PartnershipInput,
        cur: Currency,
    ) -> Result<Payload, AppError> {
        let kind =
            PartnershipKind::parse(&input.kind).ok_or(AppError::on("INVALID_KIND", "kind"))?;
        if input.parties.len() > MAX_PARTIES {
            return Err(AppError::on("TOO_MANY_PARTIES", "parties"));
        }
        let mut ids = BTreeSet::new();
        let mut parties = Vec::new();
        let mut terms = Vec::new();
        for p in input.parties {
            let id = clean(&p.id);
            if id.is_empty() || id.chars().count() > 20 || !ids.insert(id.clone()) {
                return Err(AppError::on("INVALID_PARTY_ID", "parties"));
            }
            let role = PartnerRole::parse(&p.role).ok_or(AppError::on("INVALID_ROLE", "role"))?;
            if !(0..=BP_ONE).contains(&i64::from(p.profit_share_bp)) {
                return Err(AppError::on("INVALID_BP", "profitShareBp"));
            }
            let mut capital = Vec::new();
            let mut items = Vec::new();
            for c in p.capital {
                let ck =
                    CapitalKind::parse(&c.kind).ok_or(AppError::on("INVALID_KIND", "capital"))?;
                let amount = positive(&c.amount, cur, "capital")?;
                let description = clean(&c.description);
                capital.push(CapitalP {
                    kind: ck.as_str().into(),
                    description: description.clone(),
                    amount_minor: amount.minor(),
                });
                items.push(CapitalItem {
                    kind: ck,
                    description,
                    amount,
                });
            }
            terms.push(PartnerTerms {
                role,
                profit_share_bp: i64::from(p.profit_share_bp),
                capital_items: items,
            });
            parties.push(PartyP {
                id,
                full_name: clean(&p.full_name),
                role: role.as_str().into(),
                profit_share_bp: i64::from(p.profit_share_bp),
                is_me: p.is_me,
                capital,
            });
        }
        if parties.iter().filter(|p| p.is_me).count() > 1 {
            return Err(AppError::on("MULTIPLE_ME", "isMe"));
        }
        // Kafolatli daromad — domen qoidasi (2E.1) hal qiladi: saqlashga ham yo'l yo'q.
        if let Some(f) = clean_opt(input.fixed_return.as_deref()) {
            let fixed = amount_in(&f, cur, "fixedReturn")?;
            let r = check_rules(&RulesInput {
                kind,
                currency: cur,
                partners: terms,
                fixed_return: Some(fixed),
                loss_rule: kind.loss_rule(),
                duration_months: None,
            })?;
            if r.errors.contains(&"GUARANTEED_RETURN_FORBIDDEN") {
                return Err(AppError::on("GUARANTEED_RETURN_FORBIDDEN", "fixedReturn"));
            }
        }
        let known = |id: &str| ids.contains(id);
        let duties = map_answer(input.duties, |list| {
            list.into_iter()
                .enumerate()
                .map(|(i, d)| {
                    let id = clean(&d.id);
                    Duty {
                        id: if id.is_empty() {
                            format!("d{}", i + 1)
                        } else {
                            id
                        },
                        title: clean(&d.title),
                        owner_party_id: clean_opt(d.owner_party_id.as_deref()),
                        breach_clause: clean_opt(d.breach_clause.as_deref()),
                    }
                })
                .collect()
        });
        let custody = map_answer(input.custody, |c| Custody {
            location: clean(&c.location),
            keeper_party_id: clean(&c.keeper_party_id),
            review_every_days: c.review_every_days,
            keeper_device_id: None,
        });
        let exit_clause = map_answer(input.exit_clause, |e| ExitClause {
            notice_days: e.notice_days,
            valuation_method: clean(&e.valuation_method),
            payout_terms: clean(&e.payout_terms),
            asset_split: clean_opt(e.asset_split.as_deref()),
        });
        let arbiter = map_answer(input.arbiter, |a| Arbiter {
            full_name: clean(&a.full_name),
            role: clean_opt(a.role.as_deref()),
            party_id: clean_opt(a.party_id.as_deref()),
        });
        let term = match input.term {
            Answer::Answered { value: t } => Answer::Answered {
                value: Term {
                    effective_from: ymd(date(&t.effective_from, "term.effectiveFrom")?),
                    duration_months: t.duration_months,
                    review_date: ymd(date(&t.review_date, "term.reviewDate")?),
                },
            },
            other => map_answer(other, |t| t),
        };
        let witnesses: Vec<String> = input
            .witnesses
            .iter()
            .filter_map(|w| clean_opt(Some(w)))
            .collect();
        if witnesses.len() > MAX_WITNESSES {
            return Err(AppError::on("TOO_MANY_WITNESSES", "witnesses"));
        }
        let buyout = match input.buyout {
            None => None,
            Some(b) => {
                let (seller, buyer) = (clean(&b.seller_party_id), clean(&b.buyer_party_id));
                if !known(&seller) || !known(&buyer) {
                    return Err(AppError::on("UNKNOWN_PARTY", "buyout"));
                }
                if seller == buyer {
                    return Err(AppError::on("BUYOUT_SAME_PARTY", "buyout"));
                }
                let expected = match clean_opt(b.expected_profit.as_deref()) {
                    None => None,
                    Some(s) => {
                        let m = amount_in(&s, cur, "expectedProfit")?;
                        if m.is_negative() {
                            return Err(AppError::on("INVALID_PROFIT", "expectedProfit"));
                        }
                        Some(m.minor())
                    }
                };
                Some(BuyoutP {
                    seller_party_id: seller,
                    buyer_party_id: buyer,
                    units: b.units,
                    units_per_period: b.units_per_period,
                    period_months: b.period_months,
                    start: ymd(date(&b.start, "buyout.start")?),
                    expected_profit_minor: expected,
                })
            }
        };
        Ok(Payload {
            kind: kind.as_str().into(),
            title: required(&input.title, "title")?,
            currency: cur.code().into(),
            parties,
            duties,
            negligence_clause: clean_opt(input.negligence_clause.as_deref()),
            custody,
            exit_clause,
            arbiter,
            term,
            witnesses,
            buyout,
        })
    }

    pub(crate) fn reload(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        id: &str,
    ) -> Result<PartnershipDto, AppError> {
        let v = self.partnership_view(scope, self.partnership_row(scope, id)?)?;
        self.partnership_dto(ctx, scope, &v)
    }

    // ---- ommaviy use-case'lar ----

    pub fn partnerships(&self, space_id: &str) -> Result<Vec<PartnershipSummaryDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.db
            .read(|c| repo::list(c, &scope))?
            .into_iter()
            .map(|row| {
                let v = self.partnership_view(&scope, row)?;
                let total: i64 = v.payload.parties.iter().map(Payload::capital_of).sum();
                Ok(PartnershipSummaryDto {
                    id: v.row.id.clone(),
                    kind: v.row.kind.clone(),
                    title: v.row.title.clone(),
                    status: v.row.status.clone(),
                    capital_total: self.money_dto(&ctx, Money::new(total, v.cur)),
                    my_role: v.payload.me().map(|m| m.role.clone()),
                    signed_version: v.row.signed_version.map(no32).transpose()?,
                    answered: v.check.answered,
                    in_dispute: self.open_dispute(&scope, &v.row.id)?.is_some(),
                })
            })
            .collect()
    }

    pub fn partnership(&self, space_id: &str, id: &str) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.reload(&ctx, &scope, id)
    }

    /// Tayyorgarlik darvozasi holati (kapital kiritishdan oldin ko'rsatiladi).
    pub fn readiness_gate(&self, space_id: &str) -> Result<GateDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.gate(&ctx, &scope)
    }

    /// Yangi sheriklik — darhol `Agreement(type = PARTNERSHIP)` qoralamasi bilan.
    pub fn create_partnership(
        &self,
        space_id: &str,
        input: PartnershipInput,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let payload = self.parse_partnership(input, ctx.currency)?;
        let json = serde_json::to_string(&payload).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let agreement = agreements::AgreementRow {
            id: self.new_id(),
            agreement_type: "PARTNERSHIP".into(),
            status: DRAFT.into(),
            title: payload.title.clone(),
            keeper_device_id: self.device_id.clone(),
        };
        let row = PartnershipRow {
            id: self.new_id(),
            agreement_id: agreement.id.clone(),
            kind: payload.kind.clone(),
            title: payload.title.clone(),
            status: DRAFT.into(),
            currency: payload.currency.clone(),
            signed_version: None,
            not_debt_ack_on: None,
            gate_json: None,
            activated_on: None,
            closed_on: None,
        };
        let meta = self.meta();
        self.db.write(|tx| {
            agreements::insert(tx, &scope, &agreement, &meta)?;
            agreements::set_payload(tx, &scope, &agreement.id, &json, &meta)?;
            repo::insert(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        self.reload(&ctx, &scope, &row.id)
    }

    /// Shartnoma matnini o'zgartirish. Imzolangan (hali faol bo'lmagan) shartnoma qoralamaga
    /// qaytadi; faol sheriklikda yangi versiya imzolanmaguncha eski versiya kuchda qoladi.
    pub fn update_partnership(
        &self,
        space_id: &str,
        id: &str,
        input: PartnershipInput,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut row = self.partnership_row(&scope, id)?;
        if row.status == CLOSED {
            return Err(AppError::new("PARTNERSHIP_CLOSED"));
        }
        let cur = Currency::from_code(&row.currency)?;
        let payload = self.parse_partnership(input, cur)?;
        if row.status == ACTIVE && payload.kind != row.kind {
            return Err(AppError::on("KIND_LOCKED", "kind"));
        }
        let hash = payload.hash()?;
        let versions = self
            .db
            .read(|c| repo::versions(c, &scope, &row.agreement_id))?;
        let signed_hash = versions
            .iter()
            .find(|v| Some(v.version_no) == row.signed_version)
            .map(|v| v.payload_hash.clone());
        if row.status == SIGNED && signed_hash.as_deref() != Some(hash.as_str()) {
            row.status = DRAFT.into();
            row.signed_version = None;
        }
        row.kind = payload.kind.clone();
        row.title = payload.title.clone();
        let json = serde_json::to_string(&payload).map_err(|_| AppError::new("CORRUPT_ROW"))?;
        let meta = self.meta();
        self.db.write(|tx| {
            agreements::set_payload(tx, &scope, &row.agreement_id, &json, &meta)?;
            agreements::set_status(tx, &scope, &row.agreement_id, &row.status, &meta)?;
            repo::update(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        self.reload(&ctx, &scope, id)
    }

    /// Shu qurilmada imzo. Matn oxirgi versiyadan farq qilsa — yangi versiya yaratiladi
    /// (oldingi versiyaning imzolari yangi matnga o'tmaydi).
    pub fn sign_partnership(
        &self,
        space_id: &str,
        id: &str,
        input: SignInput,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let v = self.partnership_view(&scope, self.partnership_row(&scope, id)?)?;
        if v.row.status == CLOSED {
            return Err(AppError::new("PARTNERSHIP_CLOSED"));
        }
        if !v.check.can_sign {
            return Err(AppError::new("SIGN_BLOCKED"));
        }
        validate_signature(&input.strokes).map_err(|c| AppError::on(c, "strokes"))?;
        let (key, role, name) = v
            .payload
            .required_signers()
            .into_iter()
            .find(|(k, _, _)| *k == input.signer_key)
            .ok_or(AppError::on("UNKNOWN_SIGNER", "signerKey"))?;
        if v.signatures.iter().any(|s| s.signer_key == key) {
            return Err(AppError::on("ALREADY_SIGNED", "signerKey"));
        }
        let meta = self.meta();
        let version = match &v.current {
            Some(c) => c.clone(),
            None => VersionRow {
                id: self.new_id(),
                version_no: v.versions.last().map_or(1, |l| l.version_no + 1),
                payload_json: serde_json::to_string(&v.payload)
                    .map_err(|_| AppError::new("CORRUPT_ROW"))?,
                payload_hash: v.hash.clone(),
                change_note: self.version_note(&scope, &v)?,
                created_at: meta.now.clone(),
            },
        };
        let sig = SignatureRow {
            id: self.new_id(),
            version_id: version.id.clone(),
            signer_key: key.clone(),
            signer_role: role.into(),
            signer_name: name,
            strokes_json: serde_json::to_string(&input.strokes)
                .map_err(|_| AppError::new("CORRUPT_ROW"))?,
            signed_at: meta.now.clone(),
        };
        let complete = v
            .payload
            .required_signers()
            .iter()
            .all(|(k, _, _)| *k == key || v.signatures.iter().any(|s| &s.signer_key == k));
        let mut row = v.row.clone();
        if complete {
            row.signed_version = Some(version.version_no);
            if row.status == DRAFT {
                row.status = SIGNED.into();
            }
        }
        self.db.write(|tx| {
            if v.current.is_none() {
                repo::insert_version(tx, &scope, &row.agreement_id, &version, &meta)?;
            }
            repo::insert_signature(tx, &scope, &sig, &meta)?;
            if complete {
                agreements::set_status(tx, &scope, &row.agreement_id, &row.status, &meta)?;
                repo::update(tx, &scope, &row, &meta)?;
            }
            Ok(())
        })?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        self.reload(&ctx, &scope, id)
    }

    /// Kapital qabul qiluvchi «bu qarz emas» tushuntirishini o'qidi (2E.6).
    pub fn acknowledge_not_debt(
        &self,
        space_id: &str,
        id: &str,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut row = self.partnership_row(&scope, id)?;
        if row.status == CLOSED {
            return Err(AppError::new("PARTNERSHIP_CLOSED"));
        }
        row.not_debt_ack_on = Some(ymd(self.today(&ctx)));
        let meta = self.meta();
        self.db.write(|tx| repo::update(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Partnerships]);
        self.reload(&ctx, &scope, id)
    }

    /// Katta a'zoning roziligi — imzolangan versiya uchun (kapital qabul qilishda, 2E.6).
    pub fn consent_partnership(
        &self,
        space_id: &str,
        id: &str,
        member_id: &str,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let row = self.partnership_row(&scope, id)?;
        let version_no = match (row.status.as_str(), row.signed_version) {
            (SIGNED, Some(n)) => n,
            _ => return Err(AppError::new("NOT_SIGNED")),
        };
        if !self.adult_members(&ctx)?.iter().any(|m| m.id == member_id) {
            return Err(AppError::on("NOT_ADULT_MEMBER", "memberId"));
        }
        let done = self.db.read(|c| repo::consents(c, &scope, id))?;
        if done
            .iter()
            .any(|c| c.member_id == member_id && c.version_no == version_no)
        {
            return self.reload(&ctx, &scope, id);
        }
        let consent = ConsentRow {
            member_id: member_id.into(),
            version_no,
            agreed_on: ymd(self.today(&ctx)),
        };
        let cid = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_consent(tx, &scope, &cid, id, &consent, &meta))?;
        self.publish(Some(space_id), &[Topic::Partnerships]);
        self.reload(&ctx, &scope, id)
    }

    /// Sheriklikni boshlash: faqat to'liq imzolangan shartnoma bilan. Kapital kirituvchi uchun
    /// darvoza, kapital qabul qiluvchi uchun «bu qarz emas» va kattalar roziligi. Kapital
    /// hissalari kelishuv jurnaliga yoziladi (shartnoma xeshi `refs` da).
    pub fn activate_partnership(
        &self,
        space_id: &str,
        id: &str,
    ) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let v = self.partnership_view(&scope, self.partnership_row(&scope, id)?)?;
        if let Some(code) = self.activate_blocker(&ctx, &scope, &v)? {
            return Err(AppError::new(code));
        }
        let gate = if v.me_provides_capital() {
            let g = self.gate(&ctx, &scope)?;
            Some(serde_json::to_string(&g).map_err(|_| AppError::new("CORRUPT_ROW"))?)
        } else {
            None
        };
        let today = self.today(&ctx);
        let effective = v
            .payload
            .term
            .value()
            .map_or_else(|| ymd(today), |t| t.effective_from.clone());
        let version = v.row.signed_version.unwrap_or(1);
        let signed_hash = v
            .versions
            .iter()
            .find(|x| x.version_no == version)
            .map_or_else(|| v.hash.clone(), |x| x.payload_hash.clone());
        let mut entries = Vec::new();
        for p in &v.payload.parties {
            for c in &p.capital {
                entries.push(JournalEntry {
                    id: self.new_id(),
                    agreement_id: v.row.agreement_id.clone(),
                    kind: EntryKind::Contribution,
                    party_id: Some(p.id.clone()),
                    amount: Some(JournalAmount {
                        minor: c.amount_minor,
                        currency: v.payload.currency.clone(),
                    }),
                    date: effective.clone(),
                    note: Some(c.description.clone()).filter(|d| !d.is_empty()),
                    corrects_entry_id: None,
                    refs: vec![
                        format!("contract:v{version}"),
                        format!("sha256:{signed_hash}"),
                    ],
                });
            }
        }
        for e in &entries {
            e.validate()?;
        }
        let mut row = v.row.clone();
        row.status = ACTIVE.into();
        row.activated_on = Some(ymd(today));
        row.gate_json = gate;
        let meta = self.meta();
        self.db.write(|tx| {
            for e in &entries {
                journal::append(tx, &scope, e, &meta)?;
            }
            agreements::set_status(tx, &scope, &row.agreement_id, ACTIVE, &meta)?;
            repo::update(tx, &scope, &row, &meta)
        })?;
        self.publish(
            Some(space_id),
            &[Topic::Partnerships, Topic::Agreements, Topic::Journal],
        );
        self.reload(&ctx, &scope, id)
    }

    pub fn close_partnership(&self, space_id: &str, id: &str) -> Result<PartnershipDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut row = self.partnership_row(&scope, id)?;
        if row.status != ACTIVE {
            return Err(AppError::new("NOT_ACTIVE"));
        }
        // Kassa daftaridagi ochiq davr avval yopilib, taqsimlanishi kerak (U12).
        if self.venture_open_entries(&scope, &row)? > 0 {
            return Err(AppError::new("OPEN_PERIOD_NOT_CLOSED"));
        }
        row.status = CLOSED.into();
        row.closed_on = Some(ymd(self.today(&ctx)));
        let meta = self.meta();
        self.db.write(|tx| {
            agreements::set_status(tx, &scope, &row.agreement_id, CLOSED, &meta)?;
            repo::update(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        self.reload(&ctx, &scope, id)
    }

    /// Faqat hech kim imzolamagan qoralama o'chiriladi (imzolar — dalil).
    pub fn delete_partnership(&self, space_id: &str, id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let row = self.partnership_row(&scope, id)?;
        let versions = self
            .db
            .read(|c| repo::versions(c, &scope, &row.agreement_id))?;
        if row.status != DRAFT || !versions.is_empty() {
            return Err(AppError::new("PARTNERSHIP_HAS_SIGNATURES"));
        }
        let meta = self.meta();
        self.db.write(|tx| repo::delete(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Partnerships, Topic::Agreements]);
        Ok(())
    }

    /// Shartnoma PDF'i: joriy matn, versiya raqami va shu versiyaning imzolari.
    pub fn partnership_pdf(&self, space_id: &str, id: &str) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let v = self.partnership_view(&scope, self.partnership_row(&scope, id)?)?;
        let dto = self.partnership_dto(&ctx, &scope, &v)?;
        let fmt = |minor: i64| format(Money::new(minor, v.cur), ctx.locale);
        let name = |pid: &str| v.payload.party_name(pid);
        let clause =
            |status: &str, reason: Option<String>, rows: Vec<(&str, String)>| ContractClause {
                status: status.into(),
                reason,
                rows: rows
                    .into_iter()
                    .map(|(k, val)| (k.to_string(), val))
                    .collect(),
            };
        fn state<T>(a: &Answer<T>) -> (&'static str, Option<String>) {
            match a {
                Answer::Answered { .. } => ("ANSWERED", None),
                Answer::NotApplicable { reason } => ("NOT_APPLICABLE", Some(reason.clone())),
                Answer::Unanswered => ("UNANSWERED", None),
            }
        }
        let (s, r) = state(&v.payload.custody);
        let custody = clause(
            s,
            r,
            v.payload.custody.value().map_or_else(Vec::new, |c| {
                vec![
                    ("contract.custody.location", c.location.clone()),
                    ("contract.custody.keeper", name(&c.keeper_party_id)),
                    ("contract.custody.review", c.review_every_days.to_string()),
                ]
            }),
        );
        let (s, r) = state(&v.payload.exit_clause);
        let exit = clause(
            s,
            r,
            v.payload.exit_clause.value().map_or_else(Vec::new, |e| {
                let mut rows = vec![
                    ("contract.exit.notice", e.notice_days.to_string()),
                    ("contract.exit.valuation", e.valuation_method.clone()),
                    ("contract.exit.payout", e.payout_terms.clone()),
                ];
                if let Some(a) = &e.asset_split {
                    rows.push(("contract.exit.assets", a.clone()));
                }
                rows
            }),
        );
        let (s, r) = state(&v.payload.arbiter);
        let arbiter = clause(
            s,
            r,
            v.payload.arbiter.value().map_or_else(Vec::new, |a| {
                let mut rows = vec![("contract.arbiter.name", a.full_name.clone())];
                if let Some(x) = &a.role {
                    rows.push(("contract.arbiter.role", x.clone()));
                }
                rows
            }),
        );
        let (s, r) = state(&v.payload.term);
        let term = clause(
            s,
            r,
            v.payload.term.value().map_or_else(Vec::new, |t| {
                let mut rows = vec![("contract.term.from", show(&t.effective_from))];
                if let Some(d) = t.duration_months {
                    rows.push(("contract.term.duration", d.to_string()));
                }
                rows.push(("contract.term.review", show(&t.review_date)));
                rows
            }),
        );
        let (s, r) = state(&v.payload.duties);
        let duties = clause(s, r, Vec::new());
        let duty_rows = v.payload.duties.value().map_or_else(Vec::new, |list| {
            list.iter()
                .map(|d| ContractDuty {
                    title: d.title.clone(),
                    owner: d.owner_party_id.as_deref().map_or_else(String::new, name),
                    breach: d.breach_clause.clone().unwrap_or_default(),
                })
                .collect()
        });
        let buyout = match (&v.payload.buyout, &v.buyout) {
            (Some(b), Some(Ok(sch))) => Some(ContractBuyout {
                seller: name(&b.seller_party_id),
                buyer: name(&b.buyer_party_id),
                rows: sch
                    .rows
                    .iter()
                    .map(|r| ContractBuyoutRow {
                        period: r.period.to_string(),
                        date: r.date.format("%d.%m.%Y").to_string(),
                        payment: fmt(r.payment.minor()),
                        remaining: fmt(r.remaining_stake.minor()),
                        seller: pct(r.seller_bp),
                        buyer: pct(r.buyer_bp),
                    })
                    .collect(),
            }),
            _ => None,
        };
        let doc = PartnershipContract {
            ident: v.row.id.clone(),
            locale: pdf_locale(ctx.locale),
            title: v.row.title.clone(),
            kind: v.row.kind.clone(),
            version: dto.version.map(|n| format!("v{n}")),
            hash_code: dto.hash_code.clone(),
            review_pending: TEMPLATE_REVIEW == "PENDING",
            parties: dto
                .parties
                .iter()
                .map(|p| ContractParty {
                    name: p.full_name.clone(),
                    role: p.role.clone(),
                    capital: p.capital.formatted.clone(),
                    profit_share: p.profit_share.clone(),
                    loss_share: p.loss_share.clone(),
                })
                .collect(),
            capital: v
                .payload
                .parties
                .iter()
                .flat_map(|p| {
                    p.capital.iter().map(|c| ContractCapital {
                        party: p.full_name.clone(),
                        kind: c.kind.clone(),
                        description: c.description.clone(),
                        amount: fmt(c.amount_minor),
                    })
                })
                .collect(),
            duties,
            duty_rows,
            negligence: v.payload.negligence_clause.clone(),
            custody,
            exit,
            buyout,
            arbiter,
            term,
            witnesses: v.payload.witnesses.clone(),
            signers: dto
                .signers
                .iter()
                .map(|s| ContractSigner {
                    role: s.role.clone(),
                    name: s.name.clone(),
                    signed_at: s.signed_at.clone(),
                    svg: s.svg.clone(),
                })
                .collect(),
        };
        let rendered = doc
            .render(engine(), self.today(&ctx))
            .map_err(|e| AppError::new(e.code))?;
        Ok(rendered.pdf)
    }
}

fn map_answer<T, U>(a: Answer<T>, f: impl FnOnce(T) -> U) -> Answer<U> {
    match a {
        Answer::Answered { value } => Answer::Answered { value: f(value) },
        Answer::NotApplicable { reason } => Answer::NotApplicable {
            reason: clean(&reason),
        },
        Answer::Unanswered => Answer::Unanswered,
    }
}
