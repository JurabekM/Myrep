//! Qarz tilxati (SPEC 2D.5): tomonlar, summa, muddat, guvohlar va ikki tomonlama tasdiq.
//! Hujjat — «shaxsiy hisob uchun yozuv»; yuridik kuchi haqida va'da berilmaydi.
use domain::{Date, Debt, LoanReceipt, Member, Meta, ReceiptKind, Receivable};
use money::{format_money, Locale, Money};
use storage::Connection;
use storage::{repo, Database};

use crate::{debts, Ctx, Env, ServiceError};

pub use pdf::ReceiptSignatures;

/// Tilxat uchun tayyor ma'lumot (formatlash va PDF — yuqori qatlamda).
#[derive(Debug, Clone)]
pub struct ReceiptData {
    pub kind: ReceiptKind,
    pub ref_id: String,
    /// Qarz bergan tomon.
    pub lender: String,
    /// Qarz olgan tomon.
    pub borrower: String,
    pub amount: Money,
    pub given_on: Date,
    pub due_on: Option<Date>,
    /// To'lov jadvali (qarz uchun): sana va summa.
    pub schedule: Vec<(Date, Money)>,
    /// Jadval jami asosiydan ko'pmi (ustama bor — foizsiz emas).
    pub has_markup: bool,
    pub reason: Option<String>,
    pub witnesses: Vec<String>,
    pub confirmed_by_counterparty: bool,
}

fn my_name(conn: &Connection, ctx: &Ctx) -> Result<String, ServiceError> {
    Ok(repo::get::<Member>(conn, &ctx.member_id)?
        .map(|m| m.display_name)
        .unwrap_or_default())
}

fn saved(
    conn: &Connection,
    ctx: &Ctx,
    kind: ReceiptKind,
    id: &str,
) -> Result<Option<LoanReceipt>, ServiceError> {
    Ok(repo::list::<LoanReceipt>(conn, &ctx.household_id)?
        .into_iter()
        .find(|r| r.kind == kind && r.ref_id == id))
}

/// # Errors
/// Qarz/berilgan qarz topilmasa.
pub fn data(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    kind: ReceiptKind,
    id: &str,
) -> Result<ReceiptData, ServiceError> {
    let me = my_name(conn, ctx)?;
    let rec = saved(conn, ctx, kind, id)?;
    let (witnesses, confirmed) = rec.map_or((Vec::new(), false), |r| {
        (r.witnesses, r.confirmed_by_counterparty)
    });
    match kind {
        ReceiptKind::Debt => {
            let v = debts::get(conn, env, ctx, id)?;
            let d: &Debt = &v.debt;
            Ok(ReceiptData {
                kind,
                ref_id: id.to_owned(),
                lender: d.creditor.clone(),
                borrower: me,
                amount: d.principal,
                given_on: d.borrowed_on,
                due_on: Some(d.due_date),
                schedule: v.instalments.iter().map(|i| (i.due_on, i.amount)).collect(),
                has_markup: v.has_markup(),
                reason: d.reason.clone(),
                witnesses,
                confirmed_by_counterparty: confirmed,
            })
        }
        ReceiptKind::Receivable => {
            let r = repo::get::<Receivable>(conn, id)?.ok_or(ServiceError::NotFound)?;
            if r.meta.household_id != ctx.household_id {
                return Err(ServiceError::NotFound);
            }
            Ok(ReceiptData {
                kind,
                ref_id: id.to_owned(),
                lender: me,
                borrower: r.debtor,
                amount: r.amount,
                given_on: r.given_on,
                due_on: r.due_on,
                schedule: r.due_on.map(|d| (d, r.amount)).into_iter().collect(),
                has_markup: false,
                reason: r.note,
                witnesses,
                confirmed_by_counterparty: confirmed,
            })
        }
    }
}

/// Guvohlar (eng ko'pi 4) va ikkinchi tomon tasdig'i saqlanadi.
///
/// # Errors
/// Qarz topilmasa.
pub fn save_details(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    kind: ReceiptKind,
    id: &str,
    witnesses: &[String],
    confirmed: bool,
) -> Result<(), ServiceError> {
    // Mavjudligini tekshiramiz.
    data(db.conn(), env, ctx, kind, id)?;
    let witnesses: Vec<String> = witnesses
        .iter()
        .map(|w| w.split_whitespace().collect::<Vec<_>>().join(" "))
        .filter(|w| !w.is_empty())
        .take(4)
        .map(|w| w.chars().take(60).collect())
        .collect();
    match saved(db.conn(), ctx, kind, id)? {
        Some(mut r) => {
            r.witnesses = witnesses;
            r.confirmed_by_counterparty = confirmed;
            repo::update(db.conn(), &r, env.clock.now())?;
        }
        None => repo::insert(
            db.conn(),
            &LoanReceipt {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                kind,
                ref_id: id.to_owned(),
                witnesses,
                confirmed_by_counterparty: confirmed,
            },
        )?,
    }
    Ok(())
}

/// Tilxat PDF'i. Imzolar: PNG baytlari yoki `None` (chop etib qo'lda imzolash uchun bo'sh joy).
///
/// # Errors
/// Qarz topilmasa yoki PDF/imzo rasmi yaroqsiz bo'lsa.
pub fn pdf(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    kind: ReceiptKind,
    id: &str,
    signatures: &pdf::ReceiptSignatures,
) -> Result<Vec<u8>, ServiceError> {
    let d = data(conn, env, ctx, kind, id)?;
    let fm = |m: Money| format_money(m, Locale::Uz);
    let date = |x: Date| domain::date_to_string(x).unwrap_or_default();
    let doc = pdf::LoanReceiptDoc {
        lender: d.lender,
        borrower: d.borrower,
        amount: fm(d.amount),
        given_on: date(d.given_on),
        due_on: d.due_on.map(date),
        reason: d.reason,
        schedule: d.schedule.iter().map(|(dt, m)| (date(*dt), fm(*m))).collect(),
        markup_note: d.has_markup.then(|| {
            "Diqqat: to'lov jadvali jami berilgan summadan ko'p (ustama bor). Ilova foizli qarzni tavsiya qilmaydi.".to_owned()
        }),
        witnesses: d.witnesses,
        confirmed_by_counterparty: d.confirmed_by_counterparty,
        legal_note: "Bu hujjat shaxsiy hisob uchun yozuv; yuridik kuchi haqida va'da berilmaydi. Yuridik shakl kerak bo'lsa, yurist bilan maslashing.".into(),
        disclaimer: "Ta'limiy material. Fatvo yoki moliyaviy maslahat emas.".into(),
    };
    pdf::loan_receipt(&doc, signatures).map_err(|_| {
        ServiceError::Invalid("tilxat PDF'ini yaratib bo'lmadi (imzo rasmini tekshiring)")
    })
}
