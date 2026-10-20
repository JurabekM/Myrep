//! D13 xizmati: sheriklik kassa daftari (venture ledger) — davr yozuvlari D8A jurnalida, davr yopish va
//! o'zgarmaslik, avtomatik taqsimot (`partnership::distribute`) va buyout ayirmasi, fors-major, sherik uchun
//! davr hisoboti PDF; «Hunardan ishga» (3 stsenariy, payback). Taklif tekshiruvi — `scam` xizmatida (7-qonun).
//!
//! Biznes puli uy pulidan ajratilgan: ledger xonadon byudjetiga faqat taqsimot yozuvi orqali bog'lanadi.

use domain::DomainError;
use domain::agreement::AgreementStatus;
use domain::interchange;
use domain::journal::{JournalEntry, JournalKind};
use domain::partnership::{PartnershipKind, distribute};
use domain::profit_spike::{SpikeInput, profit_spike_alert};
use domain::review::ensure_distribution_allowed;
use domain::venture::{HustleInput, hustle_scenarios, net_of};
use money::Money;
use serde::{Deserialize, Serialize};
use storage::{
    AgreementRepo, AgreementRow, AttachmentRepo, BuyoutPaymentRow, Database, JournalRepo,
    PartnershipRepo, PartnershipRow, StorageError, StoredEntry, VenturePeriodRow, VentureRepo,
};
use time::format_description::well_known::Iso8601;
use time::{Date, Duration, OffsetDateTime};

use crate::dto::{
    AttachReceiptInputDto, AttachmentDto, ClosePeriodInputDto, ClosedPeriodDto, DistributionRowDto,
    HustleInputDto, HustlePlanDto, HustleScenarioDto, JournalEntryDto, MoneyDto, OpenPeriodDto,
    VentureDto, VentureEntryInputDto,
};
use crate::finance::{self, CURRENCY, DEVICE_ID, UuidV7, date_text, parse_money};
use crate::partnerships;
use crate::session::SessionError;

const DISCLAIMER: &str = "Taʼlimiy material. Fatvo yoki moliyaviy maslahat emas.";

/// Davr yozuvi turlari (ledger).
const VENTURE_KINDS: [JournalKind; 3] = [
    JournalKind::VentureIncome,
    JournalKind::VentureExpense,
    JournalKind::ForceMajeure,
];

/// Saqlanadigan taqsimot qatori (JSON).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
struct StoredDistribution {
    party_id: String,
    name: String,
    share_bp: u64,
    minor: i64,
    buyout_minor: Option<i64>,
}

fn parse_date(text: &str) -> Result<Date, SessionError> {
    Date::parse(text, &Iso8601::DATE).map_err(|_| DomainError::InvalidDay.into())
}

fn add(left: Money, right: Money) -> Result<Money, SessionError> {
    Ok(left.checked_add(right).map_err(DomainError::from)?)
}

fn pretty(date: Date) -> String {
    date.format(&time::macros::format_description!("[day].[month].[year]"))
        .unwrap_or_default()
}

fn kind_label(kind: JournalKind) -> &'static str {
    match kind {
        JournalKind::VentureIncome => "Kirim",
        JournalKind::VentureExpense => "Xarajat",
        JournalKind::ForceMajeure => "Fors-major",
        JournalKind::ProfitDistribution => "Foyda taqsimoti",
        JournalKind::LossDistribution => "Zarar taqsimoti",
        JournalKind::BuyoutPayment => "Buyout to'lovi",
        JournalKind::OpeningBalance => "Boshlang'ich balans",
        JournalKind::Contribution => "Hissa",
        JournalKind::LoanPayment => "Qarz to'lovi",
        JournalKind::Correction => "Tuzatish",
    }
}

fn load_pair(
    db: &Database,
    partnership_id: &str,
) -> Result<(PartnershipRow, AgreementRow), SessionError> {
    let partnership = PartnershipRepo::new(db.connection())
        .find(partnership_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let agreement = AgreementRepo::new(db.connection())
        .find(&partnership.agreement_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    Ok((partnership, agreement))
}

fn entry_dto(stored: &StoredEntry) -> JournalEntryDto {
    JournalEntryDto {
        seq: u32::try_from(stored.seq).unwrap_or(u32::MAX),
        kind: stored.entry.kind.code().to_owned(),
        party_id: stored.entry.party_id.clone(),
        amount: MoneyDto::of(stored.entry.amount),
        date: date_text(stored.entry.date),
        note: stored.entry.note.clone(),
        hash: stored.hash.clone(),
    }
}

/// Davr oralig'idagi ledger yozuvlari: `after < date ≤ until`.
fn entries_between(entries: &[StoredEntry], after: Option<Date>, until: Date) -> Vec<&StoredEntry> {
    entries
        .iter()
        .filter(|stored| VENTURE_KINDS.contains(&stored.entry.kind))
        .filter(|stored| after.is_none_or(|a| stored.entry.date > a))
        .filter(|stored| stored.entry.date <= until)
        .collect()
}

fn totals(entries: &[&StoredEntry]) -> Result<(Money, Money), SessionError> {
    let mut income = Money::zero(CURRENCY);
    let mut expense = Money::zero(CURRENCY);
    for stored in entries {
        if stored.entry.kind == JournalKind::VentureIncome {
            income = add(income, stored.entry.amount)?;
        } else {
            expense = add(expense, stored.entry.amount)?;
        }
    }
    Ok((income, expense))
}

fn distribution_dto(json: &str) -> Result<Vec<DistributionRowDto>, SessionError> {
    let stored: Vec<StoredDistribution> =
        serde_json::from_str(json).map_err(|_| StorageError::InvalidData("taqsimot".to_owned()))?;
    Ok(stored
        .into_iter()
        .map(|row| DistributionRowDto {
            party_id: row.party_id,
            name: row.name,
            share_bp: u32::try_from(row.share_bp).unwrap_or(u32::MAX),
            amount: MoneyDto::of(Money::new(row.minor, CURRENCY)),
            buyout_deduction: row
                .buyout_minor
                .map(|m| MoneyDto::of(Money::new(m, CURRENCY))),
        })
        .collect())
}

fn period_dto(row: &VenturePeriodRow) -> Result<ClosedPeriodDto, SessionError> {
    Ok(ClosedPeriodDto {
        id: row.id.clone(),
        start_on: date_text(row.start_on),
        end_on: date_text(row.end_on),
        income: MoneyDto::of(row.income),
        expense: MoneyDto::of(row.expense),
        net: MoneyDto::of(row.net),
        chain_head: row.chain_head.clone(),
        closed_at: date_text(row.closed_at.date()),
        force_majeure_note: row.force_majeure_note.clone(),
        distribution: distribution_dto(&row.distribution_json)?,
    })
}

/// Kassa daftari ko'rinishi: ochiq davr, yopilgan davrlar, «katta foyda» belgisi.
pub fn venture(
    db: &Database,
    now: OffsetDateTime,
    partnership_id: &str,
) -> Result<VentureDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let (partnership, agreement) = load_pair(db, partnership_id)?;
    let periods = VentureRepo::new(db.connection()).list(&partnership.id)?;
    let last_end = periods.last().map(|p| p.end_on);
    let entries = JournalRepo::new(db.connection()).list(&agreement.id)?;
    let open = entries_between(&entries, last_end, ctx.today);
    let (income, expense) = totals(&open)?;
    let net = net_of(income, expense)?;
    let last_three = if periods.len() >= 3 {
        let tail = &periods[periods.len() - 3..];
        Some([
            tail[0].net.minor(),
            tail[1].net.minor(),
            tail[2].net.minor(),
        ])
    } else {
        None
    };
    let spike = profit_spike_alert(SpikeInput {
        plan: None,
        last_three,
        actual: net.minor(),
    });
    let mut closed = Vec::with_capacity(periods.len());
    for row in &periods {
        closed.push(period_dto(row)?);
    }
    let buyout_remaining = partnerships::buyout_dto(db, &partnership)?.map(|b| b.remaining);
    Ok(VentureDto {
        partnership_id: partnership.id.clone(),
        agreement_id: agreement.id.clone(),
        title: agreement.title.clone(),
        status: agreement.status.code().to_owned(),
        can_write: agreement.status == AgreementStatus::Signed
            && interchange::ensure_keeper(&agreement.origin_device_id, DEVICE_ID).is_ok(),
        open: OpenPeriodDto {
            start_on: last_end.map(|d| date_text(d + Duration::days(1))),
            income: MoneyDto::of(income),
            expense: MoneyDto::of(expense),
            net: MoneyDto::of(net),
            entries: open.iter().map(|s| entry_dto(s)).collect(),
        },
        periods: closed,
        spike,
        buyout_remaining: buyout_remaining.filter(|m| m.minor != "0"),
        attachments: AttachmentRepo::new(db.connection())
            .list(&agreement.id)?
            .into_iter()
            .map(|a| AttachmentDto {
                id: a.id,
                seq: u32::try_from(a.seq).unwrap_or(u32::MAX),
                image: a.image,
            })
            .collect(),
    })
}

fn ensure_writable(
    db: &Database,
    partnership_id: &str,
    date: Date,
) -> Result<(PartnershipRow, AgreementRow), SessionError> {
    let (partnership, agreement) = load_pair(db, partnership_id)?;
    if agreement.status != AgreementStatus::Signed {
        return Err(DomainError::AgreementNotSigned.into());
    }
    interchange::ensure_keeper(&agreement.origin_device_id, DEVICE_ID)?;
    if let Some(last) = VentureRepo::new(db.connection()).last_end(&partnership.id)?
        && date <= last
    {
        return Err(DomainError::PeriodClosed.into());
    }
    Ok((partnership, agreement))
}

/// Ledger yozuvi: kirim, xarajat yoki fors-major (dalil izohi bilan). Yopilgan davrga yozib bo'lmaydi.
pub fn add_entry(
    db: &Database,
    now: OffsetDateTime,
    input: VentureEntryInputDto,
) -> Result<VentureDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let kind = JournalKind::from_code(&input.kind).ok_or(DomainError::InvalidRule)?;
    if !VENTURE_KINDS.contains(&kind) {
        return Err(DomainError::InvalidRule.into());
    }
    let date = match input.date.as_deref().filter(|t| !t.trim().is_empty()) {
        Some(text) => parse_date(text)?,
        None => ctx.today,
    };
    if date > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    let (partnership, agreement) = ensure_writable(db, &input.partnership_id, date)?;
    let answers = agreements_answers(&agreement)?;
    if !answers.parties.iter().any(|p| p.id == input.party_id) {
        return Err(StorageError::NotFound.into());
    }
    let amount = parse_money(&input.amount)?;
    if amount.minor() <= 0 {
        return Err(DomainError::AmountNotPositive.into());
    }
    let note = input.note.filter(|n| !n.trim().is_empty());
    if kind == JournalKind::ForceMajeure && note.is_none() {
        return Err(DomainError::ReasonRequired.into());
    }
    JournalRepo::new(db.connection()).append(
        &agreement.household_id,
        &JournalEntry {
            id: domain::IdGen::next_id(&UuidV7),
            agreement_id: agreement.id.clone(),
            kind,
            party_id: input.party_id,
            amount,
            date,
            note,
        },
        now,
        DEVICE_ID,
    )?;
    venture(db, now, &partnership.id)
}

fn agreements_answers(
    agreement: &AgreementRow,
) -> Result<crate::dto::AgreementAnswersDto, SessionError> {
    serde_json::from_str(&agreement.answers_json)
        .map_err(|_| StorageError::InvalidData("kelishuv javoblari".to_owned()).into())
}

/// Davrni yopadi: yakun, taqsimot (foyda/zarar), buyout ayirmasi, jurnal yozuvlari, zanjir boshi.
/// Nizoda (`IN_DISPUTE`) taqsimot bloklanadi; yopilgan davr qayta ochilmaydi.
pub fn close_period(
    db: &Database,
    now: OffsetDateTime,
    input: ClosePeriodInputDto,
) -> Result<VentureDto, SessionError> {
    let ctx = finance::context(db, now)?;
    let end_on = parse_date(&input.end_on)?;
    if end_on > ctx.today {
        return Err(DomainError::InvalidDay.into());
    }
    let (partnership, agreement) = ensure_writable(db, &input.partnership_id, end_on)?;
    ensure_distribution_allowed(agreement.status)?;
    let answers = agreements_answers(&agreement)?;
    let journal = JournalRepo::new(db.connection());
    let all = journal.list(&agreement.id)?;
    let last_end = VentureRepo::new(db.connection()).last_end(&partnership.id)?;
    let entries = entries_between(&all, last_end, end_on);
    let (income, expense) = totals(&entries)?;
    let net = net_of(income, expense)?;
    let start_on = last_end.map_or_else(
        || {
            entries
                .iter()
                .map(|s| s.entry.date)
                .min()
                .or(agreement.effective_from)
                .unwrap_or(end_on)
        },
        |d| d + Duration::days(1),
    );

    let kind = match partnership.kind.as_str() {
        "MUSHARAKA" => PartnershipKind::Musharaka,
        _ => PartnershipKind::Mudaraba,
    };
    let partners = partnerships::partner_inputs(&answers)?;
    let inputs: Vec<_> = partners.iter().map(|(input, _)| input.clone()).collect();
    let shares = distribute(kind, net, &inputs)?;

    // Buyout ayirmasi: mehnat egasining foyda ulushidan navbatdagi bo'lak (qoldiq va ulush bilan cheklangan).
    let worker_index = partners.iter().position(|(_, summary)| {
        if partnership.my_role == "WORKER" {
            summary.is_me
        } else {
            !summary.is_me
        }
    });
    let buyout = partnerships::buyout_dto(db, &partnership)?;
    let mut deduction: Option<(usize, Money)> = None;
    if let (Some(index), Some(buyout)) = (worker_index, &buyout)
        && net.minor() > 0
    {
        let remaining: i64 = buyout.remaining.minor.parse().unwrap_or(0);
        let next: i64 = buyout
            .rows
            .iter()
            .find(|r| !r.paid)
            .and_then(|r| r.amount.minor.parse().ok())
            .unwrap_or(0);
        let share = shares.get(index).map_or(0, |m| m.minor());
        let amount = remaining.min(next).min(share);
        if amount > 0 {
            deduction = Some((index, Money::new(amount, CURRENCY)));
        }
    }

    let mut stored = Vec::with_capacity(partners.len());
    let mut chain_head = all
        .last()
        .map_or_else(|| "0".repeat(64), |s| s.hash.clone());
    for (index, ((_, summary), share)) in partners.iter().zip(shares.iter()).enumerate() {
        let magnitude = share.minor().abs();
        if magnitude > 0 {
            chain_head = journal.append(
                &agreement.household_id,
                &JournalEntry {
                    id: domain::IdGen::next_id(&UuidV7),
                    agreement_id: agreement.id.clone(),
                    kind: if share.minor() > 0 {
                        JournalKind::ProfitDistribution
                    } else {
                        JournalKind::LossDistribution
                    },
                    party_id: summary.party_id.clone(),
                    amount: Money::new(magnitude, CURRENCY),
                    date: end_on,
                    note: Some(format!("Davr yakuni {}", pretty(end_on))),
                },
                now,
                DEVICE_ID,
            )?;
        }
        let buyout_minor = match deduction {
            Some((i, amount)) if i == index => Some(amount.minor()),
            _ => None,
        };
        stored.push(StoredDistribution {
            party_id: summary.party_id.clone(),
            name: summary.name.clone(),
            share_bp: u64::from(summary.share_bp),
            minor: share.minor(),
            buyout_minor,
        });
    }
    if let Some((index, amount)) = deduction
        && let Some((_, summary)) = partners.get(index)
    {
        PartnershipRepo::new(db.connection()).insert_payment(&BuyoutPaymentRow {
            id: domain::IdGen::next_id(&UuidV7),
            partnership_id: partnership.id.clone(),
            amount,
            paid_on: end_on,
            created_at: now,
            origin_device_id: DEVICE_ID.to_owned(),
        })?;
        chain_head = journal.append(
            &agreement.household_id,
            &JournalEntry {
                id: domain::IdGen::next_id(&UuidV7),
                agreement_id: agreement.id.clone(),
                kind: JournalKind::BuyoutPayment,
                party_id: summary.party_id.clone(),
                amount,
                date: end_on,
                note: Some("Buyout ayirmasi (foyda ulushidan)".to_owned()),
            },
            now,
            DEVICE_ID,
        )?;
    }
    VentureRepo::new(db.connection()).insert(&VenturePeriodRow {
        id: domain::IdGen::next_id(&UuidV7),
        household_id: agreement.household_id.clone(),
        partnership_id: partnership.id.clone(),
        start_on,
        end_on,
        income,
        expense,
        net,
        chain_head,
        force_majeure_note: input.force_majeure_note.filter(|n| !n.trim().is_empty()),
        distribution_json: serde_json::to_string(&stored)
            .map_err(|_| StorageError::InvalidData("taqsimot".to_owned()))?,
        closed_at: now,
        origin_device_id: DEVICE_ID.to_owned(),
    })?;
    venture(db, now, &partnership.id)
}

/// Sherik uchun davr hisoboti PDF baytlari.
pub fn period_pdf(
    db: &Database,
    now: OffsetDateTime,
    period_id: &str,
) -> Result<Vec<u8>, SessionError> {
    let ctx = finance::context(db, now)?;
    let period = VentureRepo::new(db.connection())
        .find(period_id)?
        .ok_or_else(|| SessionError::from(StorageError::NotFound))?;
    let (partnership, agreement) = load_pair(db, &period.partnership_id)?;
    let answers = agreements_answers(&agreement)?;
    let name_of = |id: &str| -> String {
        answers
            .parties
            .iter()
            .find(|p| p.id == id)
            .map_or_else(|| id.to_owned(), |p| p.name.clone())
    };
    let all = JournalRepo::new(db.connection()).list(&agreement.id)?;
    let previous_end = VentureRepo::new(db.connection())
        .list(&partnership.id)?
        .iter()
        .filter(|p| p.end_on < period.end_on)
        .map(|p| p.end_on)
        .max();
    let entries = entries_between(&all, previous_end, period.end_on)
        .iter()
        .map(|s| {
            [
                pretty(s.entry.date),
                kind_label(s.entry.kind).to_owned(),
                name_of(&s.entry.party_id),
                MoneyDto::of(s.entry.amount).formatted,
            ]
        })
        .collect();
    let distribution = distribution_dto(&period.distribution_json)?
        .into_iter()
        .map(|row| {
            let mut text = row.amount.formatted.clone();
            if let Some(deduction) = row.buyout_deduction {
                text.push_str(&format!(" · buyout ayirmasi {}", deduction.formatted));
            }
            (format!("{} ({} %)", row.name, row.share_bp / 100), text)
        })
        .collect();
    let note = match &period.force_majeure_note {
        Some(text) => format!("Fors-major: {text}. Taqsimot shartnomaning 4–5-bandlari bo'yicha."),
        None => {
            "Fors-major hodisasi yo'q. Taqsimot shartnomaning 4–5-bandlari bo'yicha.".to_owned()
        }
    };
    let report = pdf::PeriodReport {
        title: agreement.title.clone(),
        period: format!("{} — {}", pretty(period.start_on), pretty(period.end_on)),
        generated_on: pretty(ctx.today),
        entries,
        summary: vec![
            ("Kirim".to_owned(), MoneyDto::of(period.income).formatted),
            ("Xarajat".to_owned(), MoneyDto::of(period.expense).formatted),
            (
                if period.net.minor() < 0 {
                    "Zarar"
                } else {
                    "Sof foyda"
                }
                .to_owned(),
                MoneyDto::of(period.net).formatted,
            ),
        ],
        distribution,
        chain_head: period.chain_head.clone(),
        note,
        disclaimer: DISCLAIMER.to_owned(),
    };
    Ok(pdf::render_period_report(&report)?)
}

/// «Hunardan ishga»: uch stsenariy (saqlanmaydi).
pub fn hustle(input: HustleInputDto) -> Result<HustlePlanDto, SessionError> {
    let scenarios = hustle_scenarios(&HustleInput {
        capex: parse_money(&input.capex)?,
        monthly_income: parse_money(&input.monthly_income)?,
        monthly_expense: parse_money(&input.monthly_expense)?,
        my_share_bp: u64::from(input.my_share_bp),
    })?;
    Ok(HustlePlanDto {
        scenarios: scenarios
            .iter()
            .map(|s| HustleScenarioDto {
                name: s.name.code().to_owned(),
                income: MoneyDto::of(s.income),
                expense: MoneyDto::of(s.expense),
                net: MoneyDto::of(s.net),
                my_net: MoneyDto::of(s.my_net),
                payback_months: s.payback_months,
            })
            .collect(),
    })
}

/// Chek rasmi hajmi chegarasi (data URL belgilar): ~2 MB rasm.
const MAX_ATTACHMENT_CHARS: usize = 2_800_000;

/// Ledger yozuviga chek rasmini biriktiradi (yozuvning o'zi o'zgarmaydi — alohida jadval).
pub fn attach_receipt(
    db: &Database,
    now: OffsetDateTime,
    input: AttachReceiptInputDto,
) -> Result<VentureDto, SessionError> {
    let (partnership, agreement) = load_pair(db, &input.partnership_id)?;
    if !input.image.starts_with("data:image/") || input.image.len() > MAX_ATTACHMENT_CHARS {
        return Err(DomainError::AttachmentInvalid.into());
    }
    let entries = JournalRepo::new(db.connection()).list(&agreement.id)?;
    let seq = i64::from(input.seq);
    if !entries.iter().any(|e| e.seq == seq) {
        return Err(StorageError::NotFound.into());
    }
    AttachmentRepo::new(db.connection()).insert(
        &domain::IdGen::next_id(&UuidV7),
        &agreement.household_id,
        &agreement.id,
        seq,
        &input.image,
        now,
        DEVICE_ID,
    )?;
    venture(db, now, &partnership.id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agreements;
    use crate::dto::{
        AgreementAnswersDto, ContributionDto, DutyDto, PartnershipInputDto, PartyDto,
        ProfitShareDto, SaveAnswersInputDto, SignInputDto, SignatureInputDto,
    };
    use security::SecretKey;
    use time::macros::datetime;

    const NOW: OffsetDateTime = datetime!(2026-12-01 06:00 UTC);
    const PNG: &str = "data:image/png;base64,iVBORw0KGgo=";

    fn database() -> Database {
        Database::open_in_memory(&SecretKey::from_array([91; 32])).expect("xotirada baza")
    }

    fn answers() -> AgreementAnswersDto {
        let mut a = AgreementAnswersDto::empty();
        a.parties = vec![
            PartyDto {
                id: "P1".into(),
                name: "Anvar Karimov".into(),
                role: "mehnat".into(),
                relation: String::new(),
                is_me: true,
            },
            PartyDto {
                id: "P2".into(),
                name: "Dilshod Rahimov".into(),
                role: "kapital".into(),
                relation: String::new(),
                is_me: false,
            },
        ];
        a.contributions = vec![
            ContributionDto {
                party_id: "P1".into(),
                kind: "labor".into(),
                amount: String::new(),
                description: "tikuvchilik".into(),
            },
            ContributionDto {
                party_id: "P2".into(),
                kind: "money".into(),
                amount: "5 000 000".into(),
                description: "overlock".into(),
            },
        ];
        a.duties = vec![DutyDto {
            id: "d1".into(),
            title: "Tikish".into(),
            owner_party_id: Some("P1".into()),
            breach_clause: "1 kun ichida xabar".into(),
        }];
        a.profit_shares = vec![
            ProfitShareDto {
                party_id: "P1".into(),
                share_bp: 6_000,
            },
            ProfitShareDto {
                party_id: "P2".into(),
                share_bp: 4_000,
            },
        ];
        a.loss_text = "Zarar kapital egasida".into();
        a.custody_location = "Sex kassasi".into();
        a.keeper_party_id = Some("P1".into());
        a.exit_valuation = "Oxirgi ko'rik bo'yicha".into();
        a.exit_payout = "3 oy ichida".into();
        a.arbiter_name = "Sobir hoji".into();
        a.arbiter_role = "mahalla oqsoqoli".into();
        a.review_date = "2027-10-01".into();
        a
    }

    /// Imzolangan mudaraba sherikligi (mehnat egasi, rozilik bilan).
    fn signed_partnership(db: &Database) -> String {
        let view = partnerships::create(
            db,
            NOW,
            PartnershipInputDto {
                title: "Tikuv sexi".into(),
                kind: "MUDARABA".into(),
                my_role: "WORKER".into(),
                gate_override: None,
            },
        )
        .expect("sheriklik");
        let item = view.items[0].clone();
        partnerships::consent(
            db,
            NOW,
            crate::dto::ConsentInputDto {
                id: item.id.clone(),
                member_name: "Nodira".into(),
            },
        )
        .expect("rozilik");
        agreements::save_answers(
            db,
            NOW,
            SaveAnswersInputDto {
                id: item.agreement_id.clone(),
                version: 1,
                answers: answers(),
            },
        )
        .expect("javoblar");
        for (party, role) in [("P1", "PARTY"), ("P2", "PARTY"), ("ARBITER", "ARBITER")] {
            agreements::add_signature(
                db,
                NOW,
                SignatureInputDto {
                    agreement_id: item.agreement_id.clone(),
                    party_id: party.into(),
                    role: role.into(),
                    image: PNG.into(),
                },
            )
            .expect("imzo");
        }
        agreements::sign(
            db,
            NOW,
            SignInputDto {
                agreement_id: item.agreement_id.clone(),
                effective_from: Some("2026-11-01".into()),
                opening_balance_party_id: None,
                opening_balance_amount: None,
            },
        )
        .expect("imzolandi");
        item.id
    }

    fn entry(partnership_id: &str, kind: &str, amount: &str, date: &str) -> VentureEntryInputDto {
        VentureEntryInputDto {
            partnership_id: partnership_id.into(),
            kind: kind.into(),
            party_id: "P1".into(),
            amount: amount.into(),
            date: Some(date.into()),
            note: if kind == "FORCE_MAJEURE" {
                Some("omborni suv bosdi".into())
            } else {
                None
            },
        }
    }

    #[test]
    fn davr_yopiladi_taqsimlanadi_va_yopilgan_davrga_yozib_bolmaydi() {
        let db = database();
        let id = signed_partnership(&db);
        add_entry(
            &db,
            NOW,
            entry(&id, "VENTURE_INCOME", "6 000 000", "2026-11-05"),
        )
        .expect("kirim");
        let view = add_entry(
            &db,
            NOW,
            entry(&id, "VENTURE_EXPENSE", "2 500 000", "2026-11-12"),
        )
        .expect("xarajat");
        assert_eq!(view.open.net.minor, "350000000");
        assert!(view.can_write);

        let view = close_period(
            &db,
            NOW,
            ClosePeriodInputDto {
                partnership_id: id.clone(),
                end_on: "2026-11-30".into(),
                force_majeure_note: None,
            },
        )
        .expect("yopildi");
        assert_eq!(view.periods.len(), 1);
        let period = &view.periods[0];
        assert_eq!(period.net.minor, "350000000");
        assert_eq!(period.distribution[0].amount.minor, "210000000", "P1 60 %");
        assert_eq!(period.distribution[1].amount.minor, "140000000", "P2 40 %");
        assert_eq!(period.chain_head.len(), 64);
        assert_eq!(view.open.entries.len(), 0, "yangi davr bo'sh");
        assert_eq!(view.open.start_on.as_deref(), Some("2026-12-01"));

        // Yopilgan davrga yozuv — rad.
        assert!(matches!(
            add_entry(
                &db,
                NOW,
                entry(&id, "VENTURE_INCOME", "1 000", "2026-11-20")
            ),
            Err(SessionError::Domain(DomainError::PeriodClosed))
        ));
        // PDF chiqadi.
        let bytes = period_pdf(&db, NOW, &period.id).expect("pdf");
        assert!(bytes.starts_with(b"%PDF-"));
    }

    #[test]
    fn zarar_kapital_egasiga_fors_major_bilan_va_buyout_ayirmasi() {
        let db = database();
        let id = signed_partnership(&db);
        partnerships::set_buyout(
            &db,
            NOW,
            crate::dto::BuyoutInputDto {
                id: id.clone(),
                total: "3 000 000".into(),
                months: 3,
                start_on: "2026-11-30".into(),
            },
        )
        .expect("buyout");
        // 1-davr: zarar (fors-major) — mudarabada kapital egasi ko'taradi.
        add_entry(
            &db,
            NOW,
            entry(&id, "VENTURE_INCOME", "1 000 000", "2026-11-05"),
        )
        .expect("kirim");
        add_entry(
            &db,
            NOW,
            entry(&id, "FORCE_MAJEURE", "3 000 000", "2026-11-06"),
        )
        .expect("fors-major");
        let view = close_period(
            &db,
            NOW,
            ClosePeriodInputDto {
                partnership_id: id.clone(),
                end_on: "2026-11-15".into(),
                force_majeure_note: Some("omborni suv bosdi".into()),
            },
        )
        .expect("yopildi");
        let period = &view.periods[0];
        assert_eq!(period.net.minor, "-200000000");
        assert_eq!(
            period.distribution[0].amount.minor, "0",
            "mehnat egasi zarar ko'tarmaydi"
        );
        assert_eq!(period.distribution[1].amount.minor, "-200000000");
        assert!(period.distribution[0].buyout_deduction.is_none());
        // 2-davr: foyda 5 000 000 → P1 3 000 000, buyout bo'lagi 1 000 000 ayriladi.
        add_entry(
            &db,
            NOW,
            entry(&id, "VENTURE_INCOME", "5 000 000", "2026-11-20"),
        )
        .expect("kirim");
        let view = close_period(
            &db,
            NOW,
            ClosePeriodInputDto {
                partnership_id: id.clone(),
                end_on: "2026-11-30".into(),
                force_majeure_note: None,
            },
        )
        .expect("yopildi");
        let period = &view.periods[1];
        assert_eq!(period.distribution[0].amount.minor, "300000000");
        assert_eq!(
            period.distribution[0]
                .buyout_deduction
                .as_ref()
                .map(|m| m.minor.as_str()),
            Some("100000000")
        );
        assert_eq!(
            view.buyout_remaining.as_ref().map(|m| m.minor.as_str()),
            Some("200000000")
        );
    }

    #[test]
    fn hunardan_ishga_uch_stsenariy() {
        let plan = hustle(HustleInputDto {
            capex: "8 000 000".into(),
            monthly_income: "6 000 000".into(),
            monthly_expense: "4 000 000".into(),
            my_share_bp: 6_000,
        })
        .expect("reja");
        assert_eq!(plan.scenarios[1].payback_months, Some(7));
        assert_eq!(plan.scenarios[0].payback_months, None);
    }
}
