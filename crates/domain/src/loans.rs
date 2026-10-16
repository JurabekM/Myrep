//! Qarzlar va bergan qarzlar (SPEC 2D.5, DESKTOP_PROMPT D9).
//!
//! * To'lash rejasi majburiy: rejasiz qarz saqlanmaydi (`REPAYMENT_PLAN_REQUIRED`).
//! * Reja summasi qarzga teng bo'lishi shart (foizsiz qarz — «qarzi hasana» standart).
//! * Bergan qarz ([`Receivable`]) da foiz maydoni yo'q — tuzilmaning o'zi foizni taqiqlaydi.
//! * [`borrow_check`] — qarz oldidan oylik yukni daromadga nisbatan baholaydi. Chegaralar — mahsulot qarori
//!   (OPEN_QUESTIONS, «Hal qilingan»).

use money::{Money, round_half_up_div};
use time::Date;

use crate::{DomainError, Meta, validate_name, validate_uuid_v7};

/// To'lash rejasidagi bitta to'lov.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Installment {
    /// To'lov sanasi (Toshkent).
    pub due_on: Date,
    /// Summa (musbat).
    pub amount: Money,
}

/// To'lash rejasi: kamida bitta to'lov, sanalar o'sish tartibida, summa musbat.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct RepaymentPlan {
    installments: Vec<Installment>,
}

impl RepaymentPlan {
    /// Rejani tekshirib yaratadi. Bo'sh reja — `REPAYMENT_PLAN_REQUIRED`.
    pub fn new(installments: Vec<Installment>) -> Result<Self, DomainError> {
        if installments.is_empty() {
            return Err(DomainError::RepaymentPlanRequired);
        }
        let ordered = installments
            .windows(2)
            .all(|pair| pair[0].due_on < pair[1].due_on);
        if !ordered || installments.iter().any(|item| item.amount.minor() <= 0) {
            return Err(DomainError::InvalidRule);
        }
        Ok(Self { installments })
    }

    /// To'lovlar, sana bo'yicha.
    pub fn installments(&self) -> &[Installment] {
        &self.installments
    }

    /// Rejadagi jami summa.
    pub fn total(&self) -> Result<Money, DomainError> {
        let mut total = Money::zero(self.installments[0].amount.currency());
        for item in &self.installments {
            total = total.checked_add(item.amount)?;
        }
        Ok(total)
    }
}

/// Qarz (olingan). Foiz maydoni yo'q: foizli qarz bu yerda ifodalanmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Loan {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Kimdan olingan (nomi).
    pub creditor: String,
    /// Asosiy summa (musbat).
    pub principal: Money,
    /// To'lash rejasi.
    pub plan: RepaymentPlan,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Loan {
    /// Yangi qarz. Reja summasi asosiy qarzga teng bo'lishi shart.
    pub fn create(
        id: &str,
        household_id: &str,
        creditor: &str,
        principal: Money,
        plan: RepaymentPlan,
        now: time::OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if principal.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if plan.total()? != principal {
            return Err(DomainError::PlanMismatch);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            creditor: validate_name(creditor)?,
            principal,
            plan,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Bergan qarz. Foiz maydoni umuman yo'q — bu SPEC 2D.5 talabi (kompilyatsiya darajasida).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Receivable {
    /// UUIDv7.
    pub id: String,
    /// Xonadon (UUIDv7).
    pub household_id: String,
    /// Kimga berilgan (nomi).
    pub debtor: String,
    /// Asosiy summa (musbat).
    pub principal: Money,
    /// Qaytarish rejasi.
    pub plan: RepaymentPlan,
    /// Metama'lumot.
    pub meta: Meta,
}

impl Receivable {
    /// Yangi bergan qarz. Qoidalar [`Loan::create`] bilan bir xil.
    pub fn create(
        id: &str,
        household_id: &str,
        debtor: &str,
        principal: Money,
        plan: RepaymentPlan,
        now: time::OffsetDateTime,
        origin_device_id: &str,
    ) -> Result<Self, DomainError> {
        validate_uuid_v7(id)?;
        validate_uuid_v7(household_id)?;
        if principal.minor() <= 0 {
            return Err(DomainError::AmountNotPositive);
        }
        if plan.total()? != principal {
            return Err(DomainError::PlanMismatch);
        }
        Ok(Self {
            id: id.to_owned(),
            household_id: household_id.to_owned(),
            debtor: validate_name(debtor)?,
            principal,
            plan,
            meta: Meta::created(now, origin_device_id),
        })
    }
}

/// Qarz oldidan tekshiruv natijasi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum BorrowVerdict {
    /// Oylik yuk me'yorida.
    Ok,
    /// Ogohlantirish: yuk daromadning katta qismi.
    Caution,
    /// To'xtash: yuk daromaddan ortiq darajada.
    Stop,
}

/// Oylik yuk ogohlantirish chegarasi: daromadning 30% (bp: 3 000).
pub const CAUTION_SHARE_BP: i128 = 3_000;
/// To'xtash chegarasi: daromadning 50% (bp: 5 000).
pub const STOP_SHARE_BP: i128 = 5_000;

/// Oylik yuk / oylik daromad. Daromad nolga teng yoki manfiy bo'lsa — `STOP`.
pub fn borrow_check(
    monthly_payment: Money,
    monthly_income: Money,
) -> Result<BorrowVerdict, DomainError> {
    if monthly_income.minor() <= 0 {
        return Ok(BorrowVerdict::Stop);
    }
    let share_bp = round_half_up_div(
        i128::from(monthly_payment.minor()) * 10_000,
        i128::from(monthly_income.minor()),
    )?;
    Ok(if share_bp >= STOP_SHARE_BP {
        BorrowVerdict::Stop
    } else if share_bp >= CAUTION_SHARE_BP {
        BorrowVerdict::Caution
    } else {
        BorrowVerdict::Ok
    })
}

/// Sanaga `n` oy qo'shadi; kun oy uzunligidan oshsa, oyning oxirgi kuniga qisqaradi (31 yanvar + 1 oy = 28/29 fevral).
pub fn add_months(date: Date, months: i64) -> Result<Date, DomainError> {
    let total = i64::from(u8::from(date.month())) - 1 + months;
    let year = i32::try_from(i64::from(date.year()) + total.div_euclid(12))
        .map_err(|_| DomainError::InvalidDay)?;
    let month = time::Month::try_from(
        u8::try_from(total.rem_euclid(12) + 1).map_err(|_| DomainError::InvalidDay)?,
    )
    .map_err(|_| DomainError::InvalidDay)?;
    let last_day = time::util::days_in_month(month, year);
    Date::from_calendar_date(year, month, date.day().min(last_day))
        .map_err(|_| DomainError::InvalidDay)
}

/// Teng bo'laklarga bo'lingan reja: `count` ta oylik to'lov, birinchisi `first_due` da.
/// Bo'laklar [`money::allocate`] bilan — yig'indisi aynan asosiy summa.
pub fn equal_plan(
    principal: Money,
    count: u32,
    first_due: Date,
) -> Result<RepaymentPlan, DomainError> {
    if count == 0 || principal.minor() <= 0 {
        return Err(DomainError::RepaymentPlanRequired);
    }
    let ratios = vec![1_u64; usize::try_from(count).map_err(|_| DomainError::InvalidRule)?];
    let parts = money::allocate(principal, &ratios)?;
    let mut installments = Vec::with_capacity(parts.len());
    for (index, amount) in parts.into_iter().enumerate() {
        installments.push(Installment {
            due_on: add_months(
                first_due,
                i64::try_from(index).map_err(|_| DomainError::InvalidRule)?,
            )?,
            amount,
        });
    }
    RepaymentPlan::new(installments)
}

/// «Qarzsiz kun»: barcha rejalarning eng oxirgi to'lov sanasi. Reja yo'q bo'lsa — `None`.
pub fn debt_free_day(plans: &[&RepaymentPlan]) -> Option<Date> {
    plans
        .iter()
        .filter_map(|plan| plan.installments().last().map(|i| i.due_on))
        .max()
}

/// Rejaning keyingi to'lovi (bugundan boshlab birinchi to'lanmagan): to'langan summa reja bo'yicha ketma-ket yopiladi.
pub fn next_installment(plan: &RepaymentPlan, paid: Money) -> Option<Installment> {
    let mut covered = paid.minor();
    for installment in plan.installments() {
        if covered >= installment.amount.minor() {
            covered -= installment.amount.minor();
            continue;
        }
        return Some(Installment {
            due_on: installment.due_on,
            amount: Money::new(
                installment.amount.minor() - covered.max(0),
                installment.amount.currency(),
            ),
        });
    }
    None
}

/// Yopish tartibi strategiyasi (SPEC 2D.6, D10 qoldig'i): qaysi qarzga qo'shimcha to'lov yo'naltiriladi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum PayoffStrategy {
    /// «Qor to'pi»: eng kichik qoldiq avval — tez g'alaba, motivatsiya.
    Snowball,
    /// «Ko'chki»: ustamali qarz avval (eng qimmati), so'ng katta qoldiq — kam ustama.
    Avalanche,
}

impl PayoffStrategy {
    /// Bazadagi kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::Snowball => "SNOWBALL",
            Self::Avalanche => "AVALANCHE",
        }
    }

    /// Koddan.
    pub fn from_code(code: &str) -> Option<Self> {
        match code {
            "SNOWBALL" => Some(Self::Snowball),
            "AVALANCHE" => Some(Self::Avalanche),
            _ => None,
        }
    }
}

/// Ochiq qarz (simulyatsiya kirishi).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct OpenLoan {
    /// Qoldiq.
    pub outstanding: Money,
    /// Oylik to'lov (reja bo'yicha).
    pub installment: Money,
    /// Ustamali (foizli) qarz.
    pub has_markup: bool,
}

/// Bitta qarz uchun natija.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PayoffStep {
    /// Kirishdagi indeks.
    pub index: usize,
    /// Necha oyda yopiladi (1 dan).
    pub months_to_clear: u32,
}

/// Yopish tartibi natijasi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PayoffOrder {
    /// Strategiya bo'yicha tartib (fokus avval).
    pub order: Vec<PayoffStep>,
    /// Hammasi yopiladigan oy.
    pub total_months: u32,
}

/// Eng ko'p simulyatsiya oylari (100 yil): undan oshsa — to'lovlar qoldiqni kamaytirmayapti.
const MAX_PAYOFF_MONTHS: u32 = 1_200;

/// Oyma-oy simulyatsiya: har qarz o'z to'lovini oladi, qo'shimcha summa fokus qarzga; yopilgan qarzning
/// to'lovi keyingi fokusga qo'shiladi («rollover»). Fokus oy o'rtasida yopilsa, ortgan summa keyingisiga o'tadi.
/// Hamma hisob butun sonlarda (minor).
pub fn payoff_order(
    strategy: PayoffStrategy,
    loans: &[OpenLoan],
    extra: Money,
) -> Result<PayoffOrder, DomainError> {
    if loans.is_empty() {
        return Ok(PayoffOrder {
            order: Vec::new(),
            total_months: 0,
        });
    }
    let mut order: Vec<usize> = (0..loans.len()).collect();
    match strategy {
        PayoffStrategy::Snowball => {
            order.sort_by_key(|&i| (loans[i].outstanding.minor(), i));
        }
        PayoffStrategy::Avalanche => {
            order.sort_by_key(|&i| (!loans[i].has_markup, -loans[i].outstanding.minor(), i));
        }
    }
    let mut remaining: Vec<i64> = loans.iter().map(|l| l.outstanding.minor().max(0)).collect();
    let mut cleared_month: Vec<u32> = vec![0; loans.len()];
    let extra_minor = extra.minor().max(0);
    let mut month: u32 = 0;
    while remaining.iter().any(|r| *r > 0) {
        month += 1;
        if month > MAX_PAYOFF_MONTHS {
            return Err(DomainError::InvalidRule);
        }
        // Yopilgan qarzlarning to'lovlari + qo'shimcha — fokusga.
        let mut pool: i64 = extra_minor;
        for (i, loan) in loans.iter().enumerate() {
            if remaining[i] == 0 {
                pool = pool.saturating_add(loan.installment.minor().max(0));
            }
        }
        // Avval har qarz o'z to'lovini oladi.
        let before: i64 = remaining.iter().sum();
        for (i, loan) in loans.iter().enumerate() {
            if remaining[i] > 0 {
                let pay = loan.installment.minor().max(0).min(remaining[i]);
                remaining[i] -= pay;
            }
        }
        // So'ng qo'shimcha summa tartib bo'yicha fokusga, ortgani keyingisiga.
        for &i in &order {
            if pool == 0 {
                break;
            }
            if remaining[i] > 0 {
                let pay = pool.min(remaining[i]);
                remaining[i] -= pay;
                pool -= pay;
            }
        }
        for i in 0..loans.len() {
            if remaining[i] == 0 && cleared_month[i] == 0 {
                cleared_month[i] = month;
            }
        }
        if remaining.iter().sum::<i64>() == before {
            return Err(DomainError::InvalidRule);
        }
    }
    Ok(PayoffOrder {
        order: order
            .into_iter()
            .map(|index| PayoffStep {
                index,
                months_to_clear: cleared_month[index],
            })
            .collect(),
        total_months: month,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;
    use time::macros::date;

    fn uzs(minor: i64) -> Money {
        Money::new(minor, Currency::Uzs)
    }

    #[test]
    fn oy_qoshish_kunni_qisqartiradi() {
        assert_eq!(
            add_months(date!(2026 - 01 - 31), 1).expect("sana"),
            date!(2026 - 02 - 28)
        );
        assert_eq!(
            add_months(date!(2026 - 11 - 15), 2).expect("sana"),
            date!(2027 - 01 - 15)
        );
    }

    #[test]
    fn teng_reja_yigindisi_asosiy_summaga_teng() {
        let plan = equal_plan(uzs(100), 3, date!(2026 - 10 - 20)).expect("reja");
        let amounts: Vec<i64> = plan
            .installments()
            .iter()
            .map(|i| i.amount.minor())
            .collect();
        assert_eq!(amounts, vec![34, 33, 33]);
        assert_eq!(plan.total().expect("jami"), uzs(100));
        assert_eq!(plan.installments()[2].due_on, date!(2026 - 12 - 20));
        assert_eq!(debt_free_day(&[&plan]), Some(date!(2026 - 12 - 20)));
    }

    #[test]
    fn keyingi_tolov_tolangan_summadan_keyin() {
        let plan = equal_plan(uzs(300), 3, date!(2026 - 10 - 20)).expect("reja");
        let next = next_installment(&plan, uzs(150)).expect("keyingi");
        assert_eq!(next.due_on, date!(2026 - 11 - 20));
        assert_eq!(next.amount, uzs(50));
        assert_eq!(next_installment(&plan, uzs(300)), None);
    }

    #[test]
    fn rejasiz_qarz_saqlanmaydi() {
        assert!(matches!(
            equal_plan(uzs(100), 0, date!(2026 - 10 - 20)),
            Err(DomainError::RepaymentPlanRequired)
        ));
        assert!(matches!(
            RepaymentPlan::new(Vec::new()),
            Err(DomainError::RepaymentPlanRequired)
        ));
    }

    #[test]
    fn yuk_chegaralari() {
        assert_eq!(
            borrow_check(uzs(29), uzs(100)).expect("ok"),
            BorrowVerdict::Ok
        );
        assert_eq!(
            borrow_check(uzs(30), uzs(100)).expect("ok"),
            BorrowVerdict::Caution
        );
        assert_eq!(
            borrow_check(uzs(50), uzs(100)).expect("ok"),
            BorrowVerdict::Stop
        );
        assert_eq!(
            borrow_check(uzs(1), uzs(0)).expect("ok"),
            BorrowVerdict::Stop
        );
    }
}
