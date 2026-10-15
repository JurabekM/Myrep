//! 4-qonun use-case'lari (U10): marosim rejalovchisi, stsenariylar, oilaviy muhokama,
//! smeta PDF'i va «to'yona o'rniga jamg'arma» (mehmonlar hissasi).
//!
//! Hisob `domain-uy::ceremony` da (vektor `ceremony_scenarios`); qarzni uzish muddati — U9
//! simulyatori. Qoida: tanlangan stsenariyda qarz bo'lsa, barcha kattalar «Buni qarzsiz qanday
//! o'tkazamiz?» muhokamasiga rozilik bermaguncha reja tasdiqlanmaydi. Muhokamadan keyin reja
//! o'zgarsa — roziliklar bekor bo'ladi; tasdiqlangan reja qulflanadi.
use std::collections::BTreeMap;
use std::sync::OnceLock;

use baraka_domain_common::MemberRole;
use baraka_domain_uy::ceremony::{
    check_confirm, informal_debt_payoff, line_total, scenario_totals, BudgetLine, CeremonyKind,
    CeremonyStatus, FundingSource, LineKind, ScenarioTotals,
};
use baraka_domain_uy::debt::goal_coverage_bp;
use baraka_domain_uy::recovery::RecoverySplit;
use baraka_money::{format, format_percent_bp, Currency, Money};
use baraka_pdf::{
    CeremonyEstimate, EstimateAgreement, EstimateAnswer, EstimateLine, EstimateTotal, PdfEngine,
};
use baraka_storage::repo::ceremonies::{
    self as repo, CeremonyRow, ContributionRow, LineRow, ScenarioRow, SignoffRow,
};
use baraka_storage::repo::{debts, household, recovery};
use baraka_storage::SpaceScope;
use chrono::NaiveDate;

use crate::app::Ctx;
use crate::events::Topic;
use crate::receipt::{amount_in, date, pdf_locale, positive, ymd};
use crate::text::{clean, required};
use crate::*;

/// Muhokama savollari (kalitlar i18n'da: `ceremony.question.*`, `pdf.question.*`).
pub const QUESTIONS: [&str; 4] = ["guests", "days", "cut", "sources"];
const MAX_SCENARIOS: usize = 3;

fn engine() -> &'static PdfEngine {
    static ENGINE: OnceLock<PdfEngine> = OnceLock::new();
    ENGINE.get_or_init(PdfEngine::new)
}

fn show_date(d: &str) -> String {
    NaiveDate::parse_from_str(d, "%Y-%m-%d")
        .map_or_else(|_| d.to_string(), |x| x.format("%d.%m.%Y").to_string())
}

/// Reja o'zgarishining yozuv qismi (tranzaksiya ichida bajariladi).
type WriteOp = Box<
    dyn FnOnce(
        &baraka_storage::Transaction<'_>,
        &baraka_storage::Meta,
    ) -> Result<(), baraka_storage::StorageError>,
>;

/// Hisoblangan stsenariy.
struct Calc {
    row: ScenarioRow,
    lines: Vec<(LineRow, BudgetLine, Money)>,
    totals: ScenarioTotals,
}

impl App {
    fn ceremony_row(&self, scope: &SpaceScope, id: &str) -> Result<CeremonyRow, AppError> {
        self.db
            .read(|c| repo::get_ceremony(c, scope, id))?
            .ok_or(AppError::on("NOT_FOUND", "ceremonyId"))
    }

    fn calc_scenarios(&self, scope: &SpaceScope, c: &CeremonyRow) -> Result<Vec<Calc>, AppError> {
        let cur = Currency::from_code(&c.currency)?;
        self.db
            .read(|db| repo::scenarios(db, scope, &c.id))?
            .into_iter()
            .map(|row| {
                let lines = self
                    .db
                    .read(|db| repo::lines(db, scope, &row.id))?
                    .into_iter()
                    .map(|l| {
                        let b = BudgetLine {
                            kind: LineKind::parse(&l.line_kind)
                                .ok_or(AppError::new("CORRUPT_ROW"))?,
                            amount: Money::new(l.amount_minor, cur),
                            source: FundingSource::parse(&l.source)
                                .ok_or(AppError::new("CORRUPT_ROW"))?,
                        };
                        let t = line_total(&b, row.guests)?;
                        Ok((l, b, t))
                    })
                    .collect::<Result<Vec<_>, AppError>>()?;
                let budget: Vec<BudgetLine> = lines.iter().map(|(_, b, _)| *b).collect();
                let totals = scenario_totals(&budget, row.guests, cur)?;
                Ok(Calc { row, lines, totals })
            })
            .collect()
    }

    /// Qarzni uzish uchun oylik ajratma: qo'lda yozilgani, bo'lmasa daromadning qo'shimcha
    /// to'lov ulushi (rejim ulushlari yoki standart 70/20/10).
    fn capacity(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        c: &CeremonyRow,
        cur: Currency,
    ) -> Result<(Money, &'static str), AppError> {
        if let Some(m) = c.monthly_capacity_minor {
            return Ok((Money::new(m, cur), "MANUAL"));
        }
        if cur != ctx.currency {
            return Ok((Money::zero(cur), "NONE"));
        }
        let split = self.db.read(|db| recovery::budget(db, scope))?.map_or_else(
            RecoverySplit::default,
            |b| RecoverySplit {
                household_bp: b.household_bp,
                extra_debt_bp: b.extra_debt_bp,
                savings_bp: b.savings_bp,
            },
        );
        let part = split.apply(self.monthly_income(ctx, scope)?)?.extra_debt;
        Ok(if part.is_positive() {
            (part, "INCOME_SHARE")
        } else {
            (part, "NONE")
        })
    }

    fn adults(&self, ctx: &Ctx) -> Result<Vec<household::MemberRow>, AppError> {
        Ok(self
            .db
            .read(|db| household::list_members(db, &ctx.household_id))?
            .into_iter()
            .filter(|m| m.role == MemberRole::Adult.as_str())
            .collect())
    }

    fn answers(c: &CeremonyRow) -> BTreeMap<String, String> {
        c.discussion_json
            .as_deref()
            .and_then(|j| serde_json::from_str(j).ok())
            .unwrap_or_default()
    }

    fn ceremony_dto(
        &self,
        ctx: &Ctx,
        scope: &SpaceScope,
        c: &CeremonyRow,
    ) -> Result<CeremonyDto, AppError> {
        let cur = Currency::from_code(&c.currency)?;
        let calcs = self.calc_scenarios(scope, c)?;
        let (capacity, source) = self.capacity(ctx, scope, c, cur)?;
        let start = match c.planned_on.as_deref() {
            Some(d) => date(d, "plannedOn")?,
            None => self.today(ctx),
        };
        let max = calcs
            .iter()
            .map(|x| x.totals.total.minor())
            .max()
            .unwrap_or(0);
        let goals = self.db.read(|db| debts::list_goals(db, scope))?;
        let d = |m: Money| self.money_dto(ctx, m);
        let mut scenarios = Vec::new();
        for x in &calcs {
            let pay = informal_debt_payoff(x.totals.debt, start, capacity)?;
            let saved = Money::new(max, cur).checked_sub(x.totals.total)?;
            let goal_equivalents = if saved.is_positive() {
                goals
                    .iter()
                    .filter(|g| g.currency == cur.code())
                    .map(|g| {
                        Ok(GoalEquivalentDto {
                            goal_id: g.id.clone(),
                            title: g.title.clone(),
                            percent: format_percent_bp(goal_coverage_bp(
                                saved,
                                Money::new(g.target_minor, cur),
                            )?),
                        })
                    })
                    .collect::<Result<Vec<_>, AppError>>()?
            } else {
                Vec::new()
            };
            scenarios.push(ScenarioDto {
                id: x.row.id.clone(),
                name: x.row.name.clone(),
                guests: i32::try_from(x.row.guests).map_err(|_| AppError::new("CORRUPT_ROW"))?,
                selected: c.selected_scenario_id.as_deref() == Some(x.row.id.as_str()),
                lines: x
                    .lines
                    .iter()
                    .map(|(l, b, t)| CeremonyLineDto {
                        id: l.id.clone(),
                        title: l.title.clone(),
                        kind: l.line_kind.clone(),
                        amount: d(b.amount),
                        total: d(*t),
                        source: l.source.clone(),
                    })
                    .collect(),
                total: d(x.totals.total),
                by_source: SourceTotalsDto {
                    savings: d(x.totals.savings),
                    family: d(x.totals.family),
                    expected_gifts: d(x.totals.expected_gifts),
                    debt: d(x.totals.debt),
                },
                has_debt: x.totals.debt.is_positive(),
                payoff_months: pay.map(|p| p.0),
                payoff_date: pay.and_then(|p| p.1).map(ymd),
                not_repayable: pay.is_none(),
                saved_vs_max: d(saved),
                goal_equivalents,
            });
        }
        let selected = calcs
            .iter()
            .find(|x| c.selected_scenario_id.as_deref() == Some(x.row.id.as_str()));
        let has_debt = selected.is_some_and(|x| x.totals.debt.is_positive());
        let status = CeremonyStatus::parse(&c.status).ok_or(AppError::new("CORRUPT_ROW"))?;
        let signed = self.db.read(|db| repo::signoffs(db, scope, &c.id))?;
        let adults = self.adults(ctx)?;
        let answers = Self::answers(c);
        let blocker = match selected {
            None => Some("NO_SCENARIO_SELECTED".to_string()),
            Some(_) => check_confirm(status, has_debt)
                .err()
                .map(|e| e.code.to_string()),
        };
        Ok(CeremonyDto {
            id: c.id.clone(),
            kind: c.kind.clone(),
            title: c.title.clone(),
            planned_on: c.planned_on.clone(),
            status: c.status.clone(),
            monthly_capacity: d(capacity),
            capacity_source: source.to_string(),
            discussion: DiscussionDto {
                required: has_debt,
                answers: QUESTIONS
                    .iter()
                    .map(|k| DiscussionAnswerDto {
                        key: (*k).to_string(),
                        note: answers.get(*k).cloned().unwrap_or_default(),
                    })
                    .collect(),
                complete: status == CeremonyStatus::Discussed
                    || (status == CeremonyStatus::Confirmed && has_debt),
                adults: adults
                    .iter()
                    .map(|m| SignoffDto {
                        member_id: m.id.clone(),
                        name: m.display_name.clone(),
                        agreed_on: signed
                            .iter()
                            .find(|s| s.member_id == m.id)
                            .map(|s| s.agreed_on.clone()),
                    })
                    .collect(),
            },
            can_confirm: blocker.is_none(),
            confirm_blocker: blocker,
            gifts_warning: calcs.iter().any(|x| x.totals.expected_gifts.is_positive()),
            scenarios,
        })
    }

    pub fn ceremonies(&self, space_id: &str) -> Result<Vec<CeremonySummaryDto>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        self.db
            .read(|db| repo::list_ceremonies(db, &scope))?
            .into_iter()
            .map(|c| {
                let calcs = self.calc_scenarios(&scope, &c)?;
                let pick = calcs
                    .iter()
                    .find(|x| c.selected_scenario_id.as_deref() == Some(x.row.id.as_str()))
                    .or(calcs.first());
                Ok(CeremonySummaryDto {
                    total: pick.map(|x| self.money_dto(&ctx, x.totals.total)),
                    has_debt: pick.is_some_and(|x| x.totals.debt.is_positive()),
                    id: c.id,
                    kind: c.kind,
                    title: c.title,
                    planned_on: c.planned_on,
                    status: c.status,
                })
            })
            .collect()
    }

    pub fn ceremony(&self, space_id: &str, ceremony_id: &str) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        self.ceremony_dto(&ctx, &scope, &c)
    }

    fn planned_on(s: Option<&str>) -> Result<Option<String>, AppError> {
        match s.map(str::trim) {
            None | Some("") => Ok(None),
            Some(d) => Ok(Some(ymd(date(d, "plannedOn")?))),
        }
    }

    fn guests(g: i32) -> Result<i64, AppError> {
        if g < 0 {
            Err(AppError::on("INVALID_GUESTS", "guests"))
        } else {
            Ok(i64::from(g))
        }
    }

    /// Yangi marosim rejasi va uning birinchi stsenariysi (avtomatik tanlanadi).
    pub fn create_ceremony(
        &self,
        space_id: &str,
        input: NewCeremonyInput,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let kind = CeremonyKind::parse(&input.kind).ok_or(AppError::on("INVALID_KIND", "kind"))?;
        let scenario = ScenarioRow {
            id: self.new_id(),
            ceremony_id: String::new(),
            name: required(&input.scenario_name, "scenarioName")?,
            guests: Self::guests(input.guests)?,
            sort_order: 0,
        };
        let row = CeremonyRow {
            id: self.new_id(),
            kind: kind.as_str().to_string(),
            title: required(&input.title, "title")?,
            planned_on: Self::planned_on(input.planned_on.as_deref())?,
            status: CeremonyStatus::Draft.as_str().to_string(),
            selected_scenario_id: Some(scenario.id.clone()),
            currency: ctx.currency.code().to_string(),
            monthly_capacity_minor: None,
            discussion_json: None,
        };
        let scenario = ScenarioRow {
            ceremony_id: row.id.clone(),
            ..scenario
        };
        let meta = self.meta();
        self.db.write(|tx| {
            repo::insert_ceremony(tx, &scope, &row, &meta)?;
            repo::insert_scenario(tx, &scope, &scenario, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Reja o'zgarishidan oldin: tasdiqlangan reja qulf; muhokama qilingan bo'lsa — qoralamaga
    /// qaytadi va roziliklar bekor qilinadi (o'zgarishlar bilan birga, bitta tranzaksiyada).
    fn editable(c: &CeremonyRow) -> Result<CeremonyRow, AppError> {
        match CeremonyStatus::parse(&c.status) {
            Some(CeremonyStatus::Confirmed) => Err(AppError::new("CEREMONY_LOCKED")),
            Some(_) => Ok(CeremonyRow {
                status: CeremonyStatus::Draft.as_str().to_string(),
                ..c.clone()
            }),
            None => Err(AppError::new("CORRUPT_ROW")),
        }
    }

    /// `f` — reja o'zgarishi; undan keyin holat qoralamaga qaytadi va roziliklar o'chadi.
    fn change_plan(
        &self,
        space_id: &str,
        ceremony_id: &str,
        f: impl FnOnce(&Ctx, &SpaceScope, &mut CeremonyRow) -> Result<WriteOp, AppError>,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let mut row = Self::editable(&self.ceremony_row(&scope, ceremony_id)?)?;
        let op = f(&ctx, &scope, &mut row)?;
        let meta = self.meta();
        self.db.write(|tx| {
            op(tx, &meta)?;
            repo::update_ceremony(tx, &scope, &row, &meta)?;
            repo::clear_signoffs(tx, &scope, &row.id, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Nom, sana va qarzni uzish uchun oylik ajratma. Reja (qatorlar) o'zgarmaydi — muhokama
    /// bekor qilinmaydi; tasdiqlangan rejada ham o'zgartirish mumkin.
    pub fn update_ceremony(
        &self,
        space_id: &str,
        ceremony_id: &str,
        input: CeremonyUpdateInput,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        let cur = Currency::from_code(&c.currency)?;
        let capacity = match input.monthly_capacity.as_deref().map(str::trim) {
            None | Some("") => None,
            Some(s) => {
                let m = amount_in(s, cur, "monthlyCapacity")?;
                if m.is_negative() {
                    return Err(AppError::on("AMOUNT_NEGATIVE", "monthlyCapacity"));
                }
                Some(m.minor())
            }
        };
        let row = CeremonyRow {
            title: required(&input.title, "title")?,
            planned_on: Self::planned_on(input.planned_on.as_deref())?,
            monthly_capacity_minor: capacity,
            ..c
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::update_ceremony(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Yangi stsenariy (ko'pi bilan 3 ta); `copy_from` bo'lsa, qatorlar nusxalanadi.
    pub fn add_scenario(
        &self,
        space_id: &str,
        ceremony_id: &str,
        input: ScenarioInput,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            let existing = self.db.read(|db| repo::scenarios(db, scope, &row.id))?;
            if existing.len() >= MAX_SCENARIOS {
                return Err(AppError::new("TOO_MANY_SCENARIOS"));
            }
            let sc = ScenarioRow {
                id: self.new_id(),
                ceremony_id: row.id.clone(),
                name: required(&input.name, "name")?,
                guests: Self::guests(input.guests)?,
                sort_order: i64::try_from(existing.len()).unwrap_or(0),
            };
            let copies: Vec<LineRow> = match input.copy_from.as_deref() {
                Some(from) => {
                    if !existing.iter().any(|e| e.id == from) {
                        return Err(AppError::on("NOT_FOUND", "copyFrom"));
                    }
                    self.db
                        .read(|db| repo::lines(db, scope, from))?
                        .into_iter()
                        .map(|l| LineRow {
                            id: self.new_id(),
                            scenario_id: sc.id.clone(),
                            ..l
                        })
                        .collect()
                }
                None => Vec::new(),
            };
            let scope = scope.clone();
            Ok(Box::new(move |tx, meta| {
                repo::insert_scenario(tx, &scope, &sc, meta)?;
                for l in &copies {
                    repo::insert_line(tx, &scope, l, meta)?;
                }
                Ok(())
            }))
        })
    }

    pub fn update_scenario(
        &self,
        space_id: &str,
        ceremony_id: &str,
        scenario_id: &str,
        input: ScenarioInput,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            let sc = self
                .db
                .read(|db| repo::scenarios(db, scope, &row.id))?
                .into_iter()
                .find(|s| s.id == scenario_id)
                .ok_or(AppError::on("NOT_FOUND", "scenarioId"))?;
            let sc = ScenarioRow {
                name: required(&input.name, "name")?,
                guests: Self::guests(input.guests)?,
                ..sc
            };
            let scope = scope.clone();
            Ok(Box::new(move |tx, meta| {
                repo::update_scenario(tx, &scope, &sc, meta)
            }))
        })
    }

    pub fn delete_scenario(
        &self,
        space_id: &str,
        ceremony_id: &str,
        scenario_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            let all = self.db.read(|db| repo::scenarios(db, scope, &row.id))?;
            if !all.iter().any(|s| s.id == scenario_id) {
                return Err(AppError::on("NOT_FOUND", "scenarioId"));
            }
            let rest: Vec<&ScenarioRow> = all.iter().filter(|s| s.id != scenario_id).collect();
            if rest.is_empty() {
                return Err(AppError::new("LAST_SCENARIO"));
            }
            if row.selected_scenario_id.as_deref() == Some(scenario_id) {
                row.selected_scenario_id = rest.first().map(|s| s.id.clone());
            }
            let scope = scope.clone();
            let id = scenario_id.to_string();
            Ok(Box::new(move |tx, meta| {
                repo::delete_scenario(tx, &scope, &id, meta)
            }))
        })
    }

    pub fn select_scenario(
        &self,
        space_id: &str,
        ceremony_id: &str,
        scenario_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            if !self
                .db
                .read(|db| repo::scenarios(db, scope, &row.id))?
                .iter()
                .any(|s| s.id == scenario_id)
            {
                return Err(AppError::on("NOT_FOUND", "scenarioId"));
            }
            row.selected_scenario_id = Some(scenario_id.to_string());
            Ok(Box::new(|_, _| Ok(())))
        })
    }

    pub fn add_ceremony_line(
        &self,
        space_id: &str,
        ceremony_id: &str,
        scenario_id: &str,
        input: NewCeremonyLineInput,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            if !self
                .db
                .read(|db| repo::scenarios(db, scope, &row.id))?
                .iter()
                .any(|s| s.id == scenario_id)
            {
                return Err(AppError::on("NOT_FOUND", "scenarioId"));
            }
            let cur = Currency::from_code(&row.currency)?;
            let kind =
                LineKind::parse(&input.kind).ok_or(AppError::on("INVALID_LINE_KIND", "kind"))?;
            let source = FundingSource::parse(&input.source)
                .ok_or(AppError::on("INVALID_SOURCE", "source"))?;
            let l = LineRow {
                id: self.new_id(),
                scenario_id: scenario_id.to_string(),
                title: required(&input.title, "title")?,
                line_kind: kind.as_str().to_string(),
                amount_minor: positive(&input.amount, cur, "amount")?.minor(),
                currency: cur.code().to_string(),
                source: source.as_str().to_string(),
            };
            let scope = scope.clone();
            Ok(Box::new(move |tx, meta| {
                repo::insert_line(tx, &scope, &l, meta)
            }))
        })
    }

    pub fn delete_ceremony_line(
        &self,
        space_id: &str,
        ceremony_id: &str,
        line_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        self.change_plan(space_id, ceremony_id, |_, scope, row| {
            if self
                .db
                .read(|db| repo::line_ceremony(db, scope, line_id))?
                .as_deref()
                != Some(row.id.as_str())
            {
                return Err(AppError::on("NOT_FOUND", "lineId"));
            }
            let scope = scope.clone();
            let id = line_id.to_string();
            Ok(Box::new(move |tx, meta| {
                repo::delete_line(tx, &scope, &id, meta)
            }))
        })
    }

    /// «Buni qarzsiz qanday o'tkazamiz?» savollariga javoblar (rozilikni bekor qilmaydi).
    pub fn save_discussion(
        &self,
        space_id: &str,
        ceremony_id: &str,
        answers: Vec<DiscussionAnswerDto>,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        if c.status == CeremonyStatus::Confirmed.as_str() {
            return Err(AppError::new("CEREMONY_LOCKED"));
        }
        let mut map = Self::answers(&c);
        for a in answers {
            if !QUESTIONS.contains(&a.key.as_str()) {
                return Err(AppError::on("INVALID_QUESTION", "key"));
            }
            let note = clean(&a.note);
            if note.is_empty() {
                map.remove(&a.key);
            } else {
                map.insert(a.key, note);
            }
        }
        let row = CeremonyRow {
            discussion_json: Some(
                serde_json::to_string(&map).map_err(|_| AppError::new("SERIALIZE"))?,
            ),
            ..c
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::update_ceremony(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Katta a'zoning roziligi. Kamida bitta savolga javob bo'lishi shart; barcha kattalar
    /// rozi bo'lganda reja `DISCUSSED` bo'ladi.
    pub fn agree_discussion(
        &self,
        space_id: &str,
        ceremony_id: &str,
        member_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        if c.status != CeremonyStatus::Draft.as_str() {
            return Err(AppError::new("CEREMONY_LOCKED"));
        }
        if c.selected_scenario_id.is_none() {
            return Err(AppError::new("NO_SCENARIO_SELECTED"));
        }
        if Self::answers(&c).is_empty() {
            return Err(AppError::on("DISCUSSION_EMPTY", "answers"));
        }
        let adults = self.adults(&ctx)?;
        if !adults.iter().any(|m| m.id == member_id) {
            return Err(AppError::on("NOT_ADULT_MEMBER", "memberId"));
        }
        let signed = self.db.read(|db| repo::signoffs(db, &scope, &c.id))?;
        let today = ymd(self.today(&ctx));
        let new = (!signed.iter().any(|s| s.member_id == member_id)).then(|| SignoffRow {
            id: self.new_id(),
            member_id: member_id.to_string(),
            agreed_on: today,
        });
        let all = adults
            .iter()
            .all(|m| m.id == member_id || signed.iter().any(|s| s.member_id == m.id));
        let row = if all {
            CeremonyRow {
                status: CeremonyStatus::Discussed.as_str().to_string(),
                ..c
            }
        } else {
            c
        };
        let meta = self.meta();
        self.db.write(|tx| {
            if let Some(n) = &new {
                repo::insert_signoff(tx, &scope, &row.id, n, &meta)?;
            }
            repo::update_ceremony(tx, &scope, &row, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Tasdiqlash: tanlangan stsenariyda qarz bo'lsa, faqat `DISCUSSED` dan.
    pub fn confirm_ceremony(
        &self,
        space_id: &str,
        ceremony_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        let dto = self.ceremony_dto(&ctx, &scope, &c)?;
        if let Some(code) = dto.confirm_blocker {
            return Err(AppError::new(&code));
        }
        let row = CeremonyRow {
            status: CeremonyStatus::Confirmed.as_str().to_string(),
            ..c
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::update_ceremony(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    /// Tasdiqlangan rejani qayta ochish: qoralamaga qaytadi, roziliklar bekor bo'ladi.
    pub fn reopen_ceremony(
        &self,
        space_id: &str,
        ceremony_id: &str,
    ) -> Result<CeremonyDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let row = CeremonyRow {
            status: CeremonyStatus::Draft.as_str().to_string(),
            ..self.ceremony_row(&scope, ceremony_id)?
        };
        let meta = self.meta();
        self.db.write(|tx| {
            repo::update_ceremony(tx, &scope, &row, &meta)?;
            repo::clear_signoffs(tx, &scope, &row.id, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        self.ceremony_dto(&ctx, &scope, &row)
    }

    pub fn delete_ceremony(&self, space_id: &str, ceremony_id: &str) -> Result<(), AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let meta = self.meta();
        self.db
            .write(|tx| repo::delete_ceremony(tx, &scope, ceremony_id, &meta))?;
        self.publish(Some(space_id), &[Topic::Ceremonies]);
        Ok(())
    }

    /// Chop etiladigan smeta: tanlangan (bo'lmasa — birinchi) stsenariy.
    pub fn ceremony_estimate_pdf(
        &self,
        space_id: &str,
        ceremony_id: &str,
    ) -> Result<Vec<u8>, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let c = self.ceremony_row(&scope, ceremony_id)?;
        let dto = self.ceremony_dto(&ctx, &scope, &c)?;
        let calcs = self.calc_scenarios(&scope, &c)?;
        let pick = calcs
            .iter()
            .find(|x| c.selected_scenario_id.as_deref() == Some(x.row.id.as_str()))
            .or(calcs.first())
            .ok_or(AppError::new("NO_SCENARIO_SELECTED"))?;
        let sdto = dto
            .scenarios
            .iter()
            .find(|s| s.id == pick.row.id)
            .ok_or(AppError::new("NOT_FOUND"))?;
        let f = |m: Money| format(m, ctx.locale);
        let names: BTreeMap<String, String> = self
            .db
            .read(|db| household::list_members(db, &ctx.household_id))?
            .into_iter()
            .map(|m| (m.id, m.display_name))
            .collect();
        let estimate = CeremonyEstimate {
            ident: format!("ceremony-{}", c.id),
            locale: pdf_locale(ctx.locale),
            kind: c.kind.clone(),
            title: c.title.clone(),
            date: c.planned_on.as_deref().map(show_date),
            status: c.status.clone(),
            scenario: pick.row.name.clone(),
            guests: pick.row.guests.to_string(),
            lines: pick
                .lines
                .iter()
                .map(|(l, b, t)| EstimateLine {
                    title: l.title.clone(),
                    kind: l.line_kind.clone(),
                    unit: f(b.amount),
                    guests: pick.row.guests.to_string(),
                    amount: f(*t),
                    source: l.source.clone(),
                })
                .collect(),
            totals: FundingSource::ALL
                .iter()
                .map(|s| EstimateTotal {
                    source: s.as_str().to_string(),
                    amount: f(pick.totals.by(*s)),
                })
                .collect(),
            total: f(pick.totals.total),
            payoff_months: sdto
                .payoff_months
                .filter(|_| sdto.has_debt)
                .map(|m| m.to_string()),
            payoff_date: sdto.payoff_date.as_deref().map(show_date),
            answers: dto
                .discussion
                .answers
                .iter()
                .filter(|a| !a.note.is_empty())
                .map(|a| EstimateAnswer {
                    key: a.key.clone(),
                    note: a.note.clone(),
                })
                .collect(),
            agreed: dto
                .discussion
                .adults
                .iter()
                .filter_map(|a| {
                    a.agreed_on.as_deref().map(|d| EstimateAgreement {
                        name: a.name.clone(),
                        date: show_date(d),
                    })
                })
                .collect(),
            adults: dto
                .discussion
                .adults
                .iter()
                .map(|a| names.get(&a.member_id).cloned().unwrap_or_default())
                .collect(),
        };
        let r = estimate
            .render(engine(), self.today(&ctx))
            .map_err(|e| AppError::new(e.code))?;
        Ok(r.pdf)
    }

    /// To'yona o'rniga jamg'arma: mehmon yoki qarindosh hissasi (MVP'da qo'lda yoziladi).
    pub fn add_goal_contribution(
        &self,
        space_id: &str,
        goal_id: &str,
        input: NewGoalContributionInput,
    ) -> Result<GoalDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.scope(&ctx, space_id)?;
        let goal = self
            .db
            .read(|db| debts::list_goals(db, &scope))?
            .into_iter()
            .find(|g| g.id == goal_id)
            .ok_or(AppError::on("NOT_FOUND", "goalId"))?;
        let cur = Currency::from_code(&goal.currency)?;
        let given_on = match input.given_on.as_deref().map(str::trim) {
            None | Some("") => self.today(&ctx),
            Some(d) => date(d, "givenOn")?,
        };
        let row = ContributionRow {
            id: self.new_id(),
            goal_id: goal.id.clone(),
            contributor: required(&input.contributor, "contributor")?,
            amount_minor: positive(&input.amount, cur, "amount")?.minor(),
            currency: cur.code().to_string(),
            given_on: ymd(given_on),
        };
        let meta = self.meta();
        self.db
            .write(|tx| repo::insert_contribution(tx, &scope, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Debts]);
        self.goal_dto(&ctx, &scope, goal)
    }
}
