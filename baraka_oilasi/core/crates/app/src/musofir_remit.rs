//! M2 — «Ikki qirg'oq» (`docs/musofir/SPEC.md` 5, ADR-0004): yuborishning maqsadlari, oila bilan
//! kelishuv (Uy makonidagi oilaviy kelishuv), uyda qabul va maqsad bo'yicha xarajat.
//!
//! Hisob `domain-musofir::remittance` da (vektorlar `mf_remittance`). Uy tomoni use-case'lari
//! musofirning qurilmasida ham, uydagi oila qurilmasida (`HOME`) ham ochiq; shartlar — faqat musofirda.
use std::collections::HashMap;

use baraka_domain_musofir::remittance::{
    check_shares, remittance_book, Purpose, Remittance, Share,
};
use baraka_money::{format_percent_bp, Currency, Money};
use baraka_storage::repo::{categories, expenses, household, incomes, mf};
use baraka_storage::SpaceScope;
use serde::{Deserialize, Serialize};

use crate::app::Ctx;
use crate::events::Topic;
use crate::musofir::parse_percent_bp;
use crate::receipt::{positive, ymd};
use crate::text::clean_opt;
use crate::uy::channel;
use crate::*;

/// Kelishuv shartlari bo'lmasa — hammasi uy xarajatiga.
const DEFAULT_SHARES: [Share; 1] = [Share {
    purpose: Purpose::Household,
    bp: 10_000,
}];
/// Uy makonidagi daromadning manbasi (makon nomi, barcha tillarda bir xil).
const RECEIPT_SOURCE: &str = "Musofir";
const REMITTANCE_TEMPLATE: &str = "REMITTANCE";

#[derive(Serialize, Deserialize)]
struct StoredShare {
    purpose: String,
    bp: i64,
}

fn purpose(s: &str) -> Result<Purpose, AppError> {
    Purpose::parse(s).ok_or(AppError::on("INVALID_PURPOSE", "purpose"))
}

/// Foizli ulushlar → tekshirilgan bp ulushlar (kanonik tartibda).
pub(crate) fn shares_from_input(input: &[MfShareInput]) -> Result<Vec<Share>, AppError> {
    let mut out = Vec::new();
    for s in input {
        out.push(Share {
            purpose: purpose(&s.purpose)?,
            bp: parse_percent_bp(&s.percent)
                .map_err(|_| AppError::on("INVALID_PERCENT", "shares"))?,
        });
    }
    Ok(check_shares(&out)?)
}

fn share_dtos(shares: &[Share]) -> Result<Vec<MfShareDto>, AppError> {
    shares
        .iter()
        .map(|s| {
            Ok(MfShareDto {
                purpose: s.purpose.as_str().to_string(),
                bp: i32::try_from(s.bp).map_err(|_| AppError::new("CORRUPT_ROW"))?,
                percent: format_percent_bp(s.bp),
            })
        })
        .collect()
}

impl App {
    /// Xonadondagi Uy makoni (qabul va xarajat shu yerga yoziladi).
    fn uy_space(&self, ctx: &Ctx) -> Result<Option<SpaceScope>, AppError> {
        Ok(self
            .db
            .read(|c| household::list_spaces(c, &ctx.household_id))?
            .into_iter()
            .find(|s| s.kind == "UY")
            .map(|s| SpaceScope {
                household_id: ctx.household_id.clone(),
                space_id: s.id,
            }))
    }

    fn uy_required(&self, ctx: &Ctx) -> Result<SpaceScope, AppError> {
        self.uy_space(ctx)?
            .ok_or(AppError::new("UY_SPACE_REQUIRED"))
    }

    /// Yuborish uchun standart ulushlar: kelishuv shartlari yoki uy xarajati 100 %.
    pub(crate) fn mf_default_shares(&self, scope: &SpaceScope) -> Result<Vec<Share>, AppError> {
        match self.db.read(|c| mf::terms(c, scope))? {
            Some(t) => {
                let stored: Vec<StoredShare> = serde_json::from_str(&t.shares_json)
                    .map_err(|_| AppError::new("CORRUPT_ROW"))?;
                let shares = stored
                    .iter()
                    .map(|s| {
                        Ok(Share {
                            purpose: purpose(&s.purpose)?,
                            bp: s.bp,
                        })
                    })
                    .collect::<Result<Vec<_>, AppError>>()?;
                Ok(check_shares(&shares)?)
            }
            None => Ok(DEFAULT_SHARES.to_vec()),
        }
    }

    /// «Ikki qirg'oq» shartlari va oilaviy kelishuv holati (faqat musofirning qurilmasida).
    pub fn mf_terms(&self, space_id: &str) -> Result<MfTermsDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let terms = self.db.read(|c| mf::terms(c, &scope))?;
        let uy = self.uy_space(&ctx)?;
        let agreement = match (&terms, &uy) {
            (Some(t), Some(uy)) => match &t.agreement_id {
                Some(id) => self
                    .family_agreements(&uy.space_id)?
                    .into_iter()
                    .find(|a| &a.id == id),
                None => None,
            },
            _ => None,
        };
        Ok(MfTermsDto {
            shares: match &terms {
                Some(_) => share_dtos(&self.mf_default_shares(&scope)?)?,
                None => Vec::new(),
            },
            receiver_member_id: terms.and_then(|t| t.receiver_member_id),
            agreement,
            uy_space_id: uy.map(|u| u.space_id),
        })
    }

    /// Shartlarni saqlaydi va Uy makonidagi oilaviy kelishuvni yaratadi yoki yangilaydi (matn
    /// o'zgarsa — kattalar qayta tasdiqlaydi).
    pub fn mf_set_terms(
        &self,
        space_id: &str,
        input: MfTermsInput,
    ) -> Result<MfTermsDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_scope(&ctx, space_id)?;
        let shares = shares_from_input(&input.shares)?;
        let uy = self.uy_required(&ctx)?;
        if let Some(m) = &input.receiver_member_id {
            let members = self
                .db
                .read(|c| household::list_members(c, &ctx.household_id))?;
            if !members.iter().any(|x| &x.id == m) {
                return Err(AppError::on("NOT_FOUND", "receiverMemberId"));
            }
        }
        let family = FamilyAgreementInput {
            template_key: REMITTANCE_TEMPLATE.into(),
            title: input.title,
            items: input.items,
            review_date: None,
        };
        let existing = self
            .db
            .read(|c| mf::terms(c, &scope))?
            .and_then(|t| t.agreement_id)
            .filter(|id| {
                self.family_agreements(&uy.space_id)
                    .map(|l| l.iter().any(|a| &a.id == id))
                    .unwrap_or(false)
            });
        let agreement = match existing {
            Some(id) => self.update_family_agreement(&uy.space_id, &id, family)?,
            None => self.create_family_agreement(&uy.space_id, family)?,
        };
        let stored: Vec<StoredShare> = shares
            .iter()
            .map(|s| StoredShare {
                purpose: s.purpose.as_str().into(),
                bp: s.bp,
            })
            .collect();
        let row = mf::MfTermsRow {
            shares_json: serde_json::to_string(&stored)
                .map_err(|_| AppError::new("CORRUPT_ROW"))?,
            receiver_member_id: input.receiver_member_id,
            agreement_id: Some(agreement.id),
        };
        let id = self.new_id();
        let meta = self.meta();
        self.db
            .write(|tx| mf::upsert_terms(tx, &scope, &id, &row, &meta))?;
        self.publish(Some(space_id), &[Topic::Musofir, Topic::Agreements]);
        self.mf_terms(space_id)
    }

    /// Ikkala qirg'oq uchun umumiy ko'rinish: yuborishlar (qabul holati bilan), maqsadlar qoldig'i va
    /// maqsad bo'yicha xarajatlar. Uydagi oila qurilmasida ham ochiq.
    pub fn mf_two_shores(&self, space_id: &str) -> Result<MfTwoShoresDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_space_check(&ctx, space_id)?;
        let home = ctx.currency;
        let d = |m: Money| self.money_dto(&ctx, m);
        let money_of = |minor: i64, code: &str| -> Result<Money, AppError> {
            Ok(Money::new(
                minor,
                Currency::from_code(code).map_err(|_| AppError::new("CORRUPT_ROW"))?,
            ))
        };
        let moves = self.db.read(|c| mf::sent_home(c, &scope))?;
        let parts = self.db.read(|c| mf::parts(c, &scope))?;
        let receipts = self.db.read(|c| mf::receipts(c, &scope))?;
        let members = self
            .db
            .read(|c| household::list_members(c, &ctx.household_id))?;
        let mut shares_of: HashMap<String, Vec<Share>> = HashMap::new();
        for p in &parts {
            shares_of.entry(p.move_id.clone()).or_default().push(Share {
                purpose: purpose(&p.purpose)?,
                bp: p.share_bp,
            });
        }
        let mut rems = Vec::new();
        let mut dtos = Vec::new();
        for m in &moves {
            // Maqsadlarsiz eski yuborish (M1) — uy xarajati 100 %.
            let shares = match shares_of.get(&m.id) {
                Some(s) => check_shares(s)?,
                None => DEFAULT_SHARES.to_vec(),
            };
            let receipt = receipts.iter().find(|r| r.move_id == m.id);
            let received = match receipt {
                Some(r) if r.currency == home.code() => Some(Money::new(r.received_minor, home)),
                _ => None,
            };
            rems.push(Remittance {
                received,
                shares: shares.clone(),
            });
            let expected = match (m.received_minor, m.received_currency.as_deref()) {
                (Some(v), Some(c)) => Some(d(money_of(v, c)?)),
                _ => None,
            };
            dtos.push(MfRemittanceDto {
                move_id: m.id.clone(),
                sent: d(money_of(m.amount_minor, &m.currency)?),
                sent_on: m.occurred_on.clone(),
                note: m.note.clone(),
                shares: share_dtos(&shares)?,
                expected,
                receipt: receipt
                    .map(|r| -> Result<MfReceiptDto, AppError> {
                        Ok(MfReceiptDto {
                            received: d(money_of(r.received_minor, &r.currency)?),
                            received_on: r.received_on.clone(),
                            member_id: r.member_id.clone(),
                            member_name: r
                                .member_id
                                .as_ref()
                                .and_then(|id| members.iter().find(|x| &x.id == id))
                                .map(|x| x.display_name.clone()),
                            note: r.note.clone(),
                        })
                    })
                    .transpose()?,
                allocation: Vec::new(),
            });
        }
        let spends = self.db.read(|c| mf::spends(c, &scope))?;
        let spend_pairs = spends
            .iter()
            .filter(|s| s.currency == home.code())
            .map(|s| Ok((purpose(&s.purpose)?, Money::new(s.amount_minor, home))))
            .collect::<Result<Vec<_>, AppError>>()?;
        let book = remittance_book(home, &rems, &spend_pairs)?;
        for (dto, alloc) in dtos.iter_mut().zip(&book.allocations) {
            if let Some(parts) = alloc {
                dto.allocation = parts
                    .iter()
                    .map(|(p, m)| MfPurposeAmountDto {
                        purpose: p.as_str().to_string(),
                        amount: d(*m),
                    })
                    .collect();
            }
        }
        Ok(MfTwoShoresDto {
            uy_space_id: self.uy_space(&ctx)?.map(|u| u.space_id),
            remittances: dtos,
            purposes: book
                .purposes
                .iter()
                .map(|p| MfPurposeDto {
                    purpose: p.purpose.as_str().to_string(),
                    received: d(p.received),
                    spent: d(p.spent),
                    balance: d(p.balance),
                    overspent: p.overspent,
                })
                .collect(),
            received: d(book.received),
            spent: d(book.spent),
            balance: d(book.balance),
            pending: u32::try_from(book.pending).unwrap_or(u32::MAX),
            overspent: book.overspent,
            spends: spends
                .into_iter()
                .map(|s| {
                    Ok(MfSpendDto {
                        amount: d(money_of(s.amount_minor, &s.currency)?),
                        expense_id: s.expense_id,
                        purpose: s.purpose,
                        category_id: s.category_id,
                        occurred_on: s.occurred_on,
                        note: s.note,
                    })
                })
                .collect::<Result<_, AppError>>()?,
        })
    }

    /// Uyda qabul: haqiqatda olingan summa (uy valyutasida) — Uy makonida daromad bo'lib tushadi
    /// (bitta tranzaksiyada).
    pub fn mf_confirm_receipt(
        &self,
        space_id: &str,
        move_id: &str,
        input: MfReceiptInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_space_check(&ctx, space_id)?;
        let uy = self.uy_required(&ctx)?;
        if !self
            .db
            .read(|c| mf::sent_home(c, &scope))?
            .iter()
            .any(|m| m.id == move_id)
        {
            return Err(AppError::on("NOT_FOUND", "moveId"));
        }
        if self
            .db
            .read(|c| mf::receipts(c, &scope))?
            .iter()
            .any(|r| r.move_id == move_id)
        {
            return Err(AppError::on("ALREADY_RECEIVED", "moveId"));
        }
        let amount = positive(&input.received, ctx.currency, "received")?;
        let ch = channel(&input.channel)?;
        if let Some(m) = &input.member_id {
            let members = self
                .db
                .read(|c| household::list_members(c, &ctx.household_id))?;
            if !members.iter().any(|x| &x.id == m) {
                return Err(AppError::on("NOT_FOUND", "memberId"));
            }
        }
        let date = self.date_or_today(&ctx, input.received_on.as_deref(), "receivedOn")?;
        let note = clean_opt(input.note.as_deref());
        let receipt_id = self.new_id();
        let income = incomes::IncomeRow {
            id: self.new_id(),
            member_id: input.member_id.clone(),
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            source: RECEIPT_SOURCE.into(),
            channel: ch.as_str().to_string(),
            source_type: None,
            occurred_on: ymd(date),
            note: note.clone(),
        };
        let receipt = mf::MfReceiptRow {
            id: receipt_id.clone(),
            move_id: move_id.to_string(),
            income_id: income.id.clone(),
            member_id: input.member_id,
            received_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            received_on: ymd(date),
            note,
        };
        let meta = self.meta();
        self.db.write(|tx| {
            incomes::insert_with_transfer(tx, &uy, &income, &receipt_id, &meta)?;
            mf::insert_receipt(tx, &scope, &receipt, &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Musofir, Topic::Incomes]);
        self.mf_two_shores(space_id)
    }

    /// Uy makonidagi xarajat — maqsad belgisi bilan (bitta tranzaksiyada). Maqsaddan ortiq sarf
    /// taqiqlanmaydi (ogohlantirish — ko'rinishda).
    pub fn mf_record_spend(
        &self,
        space_id: &str,
        input: MfSpendInput,
    ) -> Result<MfTwoShoresDto, AppError> {
        let ctx = self.ctx()?;
        let scope = self.mf_space_check(&ctx, space_id)?;
        let uy = self.uy_required(&ctx)?;
        let p = purpose(&input.purpose)?;
        let amount = positive(&input.amount, ctx.currency, "amount")?;
        let ch = channel(&input.channel)?;
        let category = self
            .db
            .read(|c| categories::get(c, &uy, &input.category_id))?
            .ok_or(AppError::on("NOT_FOUND", "categoryId"))?;
        let date = self.date_or_today(&ctx, input.occurred_on.as_deref(), "occurredOn")?;
        let row = expenses::ExpenseRow {
            id: self.new_id(),
            category_id: category.id,
            member_id: None,
            amount_minor: amount.minor(),
            currency: amount.currency().code().to_string(),
            channel: ch.as_str().to_string(),
            occurred_on: ymd(date),
            necessity: category.default_necessity,
            obligation_id: None,
            is_gift: false,
            is_ostentation: false,
            funded_by_debt: false,
            note: clean_opt(input.note.as_deref()),
        };
        let spend_id = self.new_id();
        let meta = self.meta();
        self.db.write(|tx| {
            expenses::insert(tx, &uy, &row, &meta)?;
            mf::insert_spend(tx, &scope, &spend_id, &row.id, p.as_str(), &meta)
        })?;
        self.publish(Some(space_id), &[Topic::Musofir, Topic::Expenses]);
        self.mf_two_shores(space_id)
    }
}
