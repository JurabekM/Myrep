//! Odatlar (SPEC 2B.9): foydalanuvchi o'zi belgilagan qimmat/zararli odatlar uchun faqat statistika.
//! «Oyiga X, yiliga Y» — majburlash, ayblash yoki uyaltirish yo'q.
use domain::{habit_projection, Category, Date, Expense, HabitProjection};
use money::Money;
use storage::{repo, Connection};
use time::Duration;

use crate::{sum_money, Ctx, ServiceError};

/// Prognoz uchun oxirgi shuncha kun (4 hafta).
pub const WINDOW_DAYS: u32 = 28;

#[derive(Debug, Clone)]
pub struct HabitStat {
    pub category_id: String,
    pub name: String,
    pub window_total: Money,
    pub projection: HabitProjection,
}

/// # Errors
/// Baza xatosi yoki hisob xatosi.
pub fn stats(conn: &Connection, ctx: &Ctx, today: Date) -> Result<Vec<HabitStat>, ServiceError> {
    let from = today - Duration::days(i64::from(WINDOW_DAYS) - 1);
    let expenses: Vec<Expense> = repo::list::<Expense>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|e| e.spent_on >= from && e.spent_on <= today)
        .collect();
    repo::list::<Category>(conn, &ctx.household_id)?
        .into_iter()
        .filter(|c| c.is_habit)
        .map(|c| {
            let total = sum_money(
                ctx.currency,
                expenses
                    .iter()
                    .filter(|e| e.category_id == c.meta.id)
                    .map(|e| e.amount),
            )?;
            let projection = habit_projection(total, WINDOW_DAYS)
                .map_err(|_| ServiceError::Invalid("prognoz hisoblanmadi"))?;
            Ok(HabitStat {
                category_id: c.meta.id,
                name: c.name,
                window_total: total,
                projection,
            })
        })
        .collect()
}
