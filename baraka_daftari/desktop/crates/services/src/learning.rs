//! Ta'lim yo'li (D5): boblar, haftalik vazifalar, «Daftar sahifasi» va odat asosidagi ochilish.
//! Ritm haftalik (juma): har juma o'tgan haftadagi vazifalar tekshiriladi va shartga qarab yangi bob ochiladi.
use std::collections::BTreeSet;

use content::{
    decide, trigger_met, Catalog, Chapter, ReleaseMode, Task, TaskTrigger, UnlockDecision,
    UnlockPolicy, VisibleBlock, WeekFacts, WeekResult,
};
use domain::{
    week_start, ChapterProgress, DaftarPage, Date, Expense, Income, Meta, Obligation, Setting,
    TaskCompletion, VaultSource, VaultTransaction, VaultTxKind,
};
use storage::{repo, Connection, Database};
use time::Duration;

use crate::{home::WEEK_ANCHOR, local_date, Ctx, Env, ServiceError};

pub const MAX_PAGE_CHARS: usize = 5_000;

const KEY_WINDOW: &str = "unlock.window_weeks";
const KEY_MIN_WEEKS: &str = "unlock.min_satisfied_weeks";
const KEY_MIN_TASKS: &str = "unlock.min_tasks_per_week";

#[derive(Debug, Clone)]
pub struct TaskStatus {
    pub id: String,
    pub title: String,
    pub trigger: TaskTrigger,
    pub done: bool,
    /// `true` — ma'lumotdan avtomatik aniqlangan; `false` — qo'lda belgilangan yoki belgilanmagan.
    pub auto: bool,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ChapterStatus {
    Opened { opened_on: Date },
    Locked,
}

#[derive(Debug, Clone)]
pub struct ChapterEntry {
    pub id: String,
    pub title: String,
    pub law: u8,
    pub order: u32,
    pub status: ChapterStatus,
    pub is_current: bool,
}

#[derive(Debug, Clone)]
pub struct Journey {
    pub chapters: Vec<ChapterEntry>,
    pub current_id: String,
    /// Joriy bob shu hafta ochilgan (yangi bob — juma quvonchi).
    pub opened_this_week: bool,
    pub week_start: Date,
    pub week_tasks: Vec<TaskStatus>,
    /// Keyingi bobga o'tish holati; oxirgi bobda `None`.
    pub unlock: Option<UnlockDecision>,
    pub policy: UnlockPolicy,
}

#[derive(Debug, Clone)]
pub struct ChapterDetail {
    pub id: String,
    pub title: String,
    pub law: u8,
    pub placeholder: bool,
    pub blocks: Vec<VisibleBlock>,
    pub page_prompt: String,
    pub page_body: String,
    pub tasks: Vec<TaskStatus>,
}

/// Ma'lumotlardan haftalik faktlarni bir marta yuklab, istalgan hafta uchun hisoblaydi.
struct Facts {
    incomes: Vec<Date>,
    allocation_days: BTreeSet<Date>,
    audits: Vec<Date>,
    obligations: Vec<Date>,
    manual: Vec<TaskCompletion>,
}

impl Facts {
    fn load(conn: &Connection, ctx: &Ctx) -> Result<Self, ServiceError> {
        let h = &ctx.household_id;
        Ok(Self {
            incomes: repo::list::<Income>(conn, h)?
                .iter()
                .map(|i| i.received_on)
                .collect(),
            allocation_days: repo::list::<VaultTransaction>(conn, h)?
                .into_iter()
                .filter(|t| {
                    t.kind == VaultTxKind::Deposit && t.source == Some(VaultSource::Allocation)
                })
                .map(|t| local_date(t.occurred_at))
                .collect(),
            // Audit faolligi: yozuv yaratilgan yoki qayta kiritilgan (yangilangan) kunlar.
            audits: repo::list::<Expense>(conn, h)?
                .iter()
                .filter(|e| e.audit_month.is_some())
                .flat_map(|e| [local_date(e.meta.created_at), local_date(e.meta.updated_at)])
                .collect(),
            obligations: repo::list::<Obligation>(conn, h)?
                .iter()
                .map(|o| local_date(o.meta.created_at))
                .collect(),
            manual: repo::list::<TaskCompletion>(conn, h)?,
        })
    }

    fn week(&self, ws: Date) -> WeekFacts {
        let end = ws + Duration::days(6);
        let in_week = |d: &Date| *d >= ws && *d <= end;
        let count =
            |v: &[Date]| u32::try_from(v.iter().filter(|d| in_week(d)).count()).unwrap_or(u32::MAX);
        WeekFacts {
            income_count: count(&self.incomes),
            allocation_days: u32::try_from(
                self.allocation_days.iter().filter(|d| in_week(d)).count(),
            )
            .unwrap_or(u32::MAX),
            audit_completed: self.audits.iter().any(in_week),
            obligations_added: count(&self.obligations),
        }
    }

    fn task_status(&self, task: &Task, ws: Date) -> TaskStatus {
        let manual = self
            .manual
            .iter()
            .any(|m| m.task_id == task.id && m.week_start == ws);
        let auto = !manual && trigger_met(task.trigger, &self.week(ws));
        TaskStatus {
            id: task.id.clone(),
            title: task.title.clone(),
            trigger: task.trigger,
            done: manual || auto,
            auto,
        }
    }

    fn done_count(&self, chapter: &Chapter, ws: Date) -> u32 {
        let n = chapter
            .tasks
            .iter()
            .filter(|t| self.task_status(t, ws).done)
            .count();
        u32::try_from(n).unwrap_or(u32::MAX)
    }
}

pub(crate) fn setting(
    conn: &Connection,
    ctx: &Ctx,
    key: &str,
) -> Result<Option<Setting>, ServiceError> {
    Ok(repo::list::<Setting>(conn, &ctx.household_id)?
        .into_iter()
        .find(|s| s.key == key))
}

pub(crate) fn put_setting(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    key: &str,
    value: &str,
) -> Result<(), ServiceError> {
    match setting(conn, ctx, key)? {
        Some(mut s) => {
            s.value = value.to_owned();
            repo::update(conn, &s, env.clock.now())?;
        }
        None => repo::insert(
            conn,
            &Setting {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                key: key.to_owned(),
                value: value.to_owned(),
            },
        )?,
    }
    Ok(())
}

/// Saqlangan siyosat (yo'q yoki buzilgan bo'lsa standart: 3 hafta / 2 hafta / 2 vazifa).
///
/// # Errors
/// Baza xatosi.
pub fn policy(conn: &Connection, ctx: &Ctx) -> Result<UnlockPolicy, ServiceError> {
    let get = |key: &str| -> Result<Option<u32>, ServiceError> {
        Ok(setting(conn, ctx, key)?.and_then(|s| s.value.parse().ok()))
    };
    let d = UnlockPolicy::DEFAULT;
    Ok(UnlockPolicy::new(
        get(KEY_WINDOW)?.unwrap_or(d.window_weeks()),
        get(KEY_MIN_WEEKS)?.unwrap_or(d.min_satisfied_weeks()),
        get(KEY_MIN_TASKS)?.unwrap_or(d.min_tasks_per_week()),
    )
    .unwrap_or(d))
}

/// # Errors
/// Qiymatlar chegaradan chiqsa yoki baza xatosi.
pub fn set_policy(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    window_weeks: u32,
    min_satisfied_weeks: u32,
    min_tasks_per_week: u32,
) -> Result<(), ServiceError> {
    UnlockPolicy::new(window_weeks, min_satisfied_weeks, min_tasks_per_week)
        .map_err(|_| ServiceError::Invalid("ochilish sharti chegaradan chiqdi"))?;
    db.transaction::<(), ServiceError>(|tx| {
        put_setting(tx, env, ctx, KEY_WINDOW, &window_weeks.to_string())?;
        put_setting(
            tx,
            env,
            ctx,
            KEY_MIN_WEEKS,
            &min_satisfied_weeks.to_string(),
        )?;
        put_setting(tx, env, ctx, KEY_MIN_TASKS, &min_tasks_per_week.to_string())
    })
}

fn opened(conn: &Connection, ctx: &Ctx) -> Result<Vec<ChapterProgress>, ServiceError> {
    Ok(repo::list::<ChapterProgress>(conn, &ctx.household_id)?)
}

fn open_chapter(
    conn: &Connection,
    env: &Env<'_>,
    ctx: &Ctx,
    chapter_id: &str,
    opened_on: Date,
) -> Result<(), ServiceError> {
    repo::insert(
        conn,
        &ChapterProgress {
            meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
            chapter_id: chapter_id.to_owned(),
            opened_on,
        },
    )?;
    Ok(())
}

/// Ochilishni baholaydi va kerak bo'lsa keyingi bobni ochadi (haftada ko'pi bilan bittasi).
fn advance(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    catalog: &Catalog,
) -> Result<(), ServiceError> {
    let this_week = week_start(local_date(env.clock.now()), WEEK_ANCHOR);
    let today = local_date(env.clock.now());
    let policy = policy(db.conn(), ctx)?;
    let progress = opened(db.conn(), ctx)?;

    let Some(first) = catalog.first() else {
        return Ok(());
    };
    if progress.is_empty() {
        return db.transaction::<(), ServiceError>(|tx| {
            open_chapter(tx, env, ctx, &first.id, this_week)
        });
    }
    let Some((current, entry)) = progress
        .iter()
        .filter_map(|p| catalog.chapter(&p.chapter_id).map(|c| (c, p)))
        .max_by_key(|(c, _)| c.order)
    else {
        return Ok(());
    };
    let Some(next) = catalog.next_after(&current.id) else {
        return Ok(());
    };
    if progress.iter().any(|p| p.chapter_id == next.id) {
        return Ok(());
    }

    let facts = Facts::load(db.conn(), ctx)?;
    let mut results = Vec::new();
    let mut w = week_start(entry.opened_on, WEEK_ANCHOR);
    while w < this_week {
        results.push(WeekResult {
            week_start: w,
            completed_tasks: facts.done_count(current, w),
        });
        w += Duration::days(7);
    }
    if decide(policy, entry.opened_on, today, WEEK_ANCHOR, &results) == UnlockDecision::Unlocked {
        db.transaction::<(), ServiceError>(|tx| open_chapter(tx, env, ctx, &next.id, this_week))?;
    }
    Ok(())
}

/// Yo'l holati. Kerak bo'lsa birinchi/keyingi bobni ochadi.
///
/// # Errors
/// Baza xatosi yoki kontent bo'sh bo'lsa.
pub fn journey(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    catalog: &Catalog,
) -> Result<Journey, ServiceError> {
    advance(db, env, ctx, catalog)?;

    let today = local_date(env.clock.now());
    let this_week = week_start(today, WEEK_ANCHOR);
    let progress = opened(db.conn(), ctx)?;
    let current = progress
        .iter()
        .filter_map(|p| catalog.chapter(&p.chapter_id).map(|c| (c, p)))
        .max_by_key(|(c, _)| c.order)
        .ok_or(ServiceError::NotFound)?;
    let (current_ch, current_p) = current;
    let facts = Facts::load(db.conn(), ctx)?;
    let policy = policy(db.conn(), ctx)?;

    let unlock = catalog.next_after(&current_ch.id).map(|_| {
        let mut results = Vec::new();
        let mut w = week_start(current_p.opened_on, WEEK_ANCHOR);
        while w < this_week {
            results.push(WeekResult {
                week_start: w,
                completed_tasks: facts.done_count(current_ch, w),
            });
            w += Duration::days(7);
        }
        decide(policy, current_p.opened_on, today, WEEK_ANCHOR, &results)
    });

    let chapters = catalog
        .chapters()
        .iter()
        .map(|c| ChapterEntry {
            id: c.id.clone(),
            title: c.title.clone(),
            law: c.law,
            order: c.order,
            status: progress.iter().find(|p| p.chapter_id == c.id).map_or(
                ChapterStatus::Locked,
                |p| ChapterStatus::Opened {
                    opened_on: p.opened_on,
                },
            ),
            is_current: c.id == current_ch.id,
        })
        .collect();
    let week_tasks: Vec<TaskStatus> = current_ch
        .tasks
        .iter()
        .map(|t| facts.task_status(t, this_week))
        .collect();

    Ok(Journey {
        chapters,
        current_id: current_ch.id.clone(),
        opened_this_week: week_start(current_p.opened_on, WEEK_ANCHOR) == this_week,
        week_start: this_week,
        week_tasks,
        unlock,
        policy,
    })
}

fn ensure_opened(conn: &Connection, ctx: &Ctx, chapter_id: &str) -> Result<(), ServiceError> {
    if opened(conn, ctx)?
        .iter()
        .any(|p| p.chapter_id == chapter_id)
    {
        Ok(())
    } else {
        Err(ServiceError::Invalid("bu bob hali ochilmagan"))
    }
}

fn page(
    conn: &Connection,
    ctx: &Ctx,
    chapter_id: &str,
) -> Result<Option<DaftarPage>, ServiceError> {
    Ok(repo::list::<DaftarPage>(conn, &ctx.household_id)?
        .into_iter()
        .find(|p| p.chapter_id == chapter_id))
}

/// Faqat ochilgan bob. Diniy bloklar `mode` ga qarab filtrlanadi.
///
/// # Errors
/// Bob topilmasa yoki hali ochilmagan bo'lsa.
pub fn chapter_detail(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    catalog: &Catalog,
    chapter_id: &str,
    mode: ReleaseMode,
) -> Result<ChapterDetail, ServiceError> {
    advance(db, env, ctx, catalog)?;
    let chapter = catalog.chapter(chapter_id).ok_or(ServiceError::NotFound)?;
    ensure_opened(db.conn(), ctx, chapter_id)?;
    let this_week = week_start(local_date(env.clock.now()), WEEK_ANCHOR);
    let facts = Facts::load(db.conn(), ctx)?;
    Ok(ChapterDetail {
        id: chapter.id.clone(),
        title: chapter.title.clone(),
        law: chapter.law,
        placeholder: chapter.placeholder,
        blocks: Catalog::visible_blocks(chapter, mode),
        page_prompt: chapter.page_prompt.clone(),
        page_body: page(db.conn(), ctx, chapter_id)?
            .map(|p| p.body)
            .unwrap_or_default(),
        tasks: chapter
            .tasks
            .iter()
            .map(|t| facts.task_status(t, this_week))
            .collect(),
    })
}

/// Qo'lda belgilanadigan (`Manual`) vazifani shu hafta uchun belgilaydi/olib tashlaydi.
///
/// # Errors
/// Bob ochilmagan, vazifa topilmasa yoki avtomatik bo'lsa.
pub fn set_task_done(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    catalog: &Catalog,
    chapter_id: &str,
    task_id: &str,
    done: bool,
) -> Result<(), ServiceError> {
    let chapter = catalog.chapter(chapter_id).ok_or(ServiceError::NotFound)?;
    ensure_opened(db.conn(), ctx, chapter_id)?;
    let task = chapter
        .tasks
        .iter()
        .find(|t| t.id == task_id)
        .ok_or(ServiceError::NotFound)?;
    if task.trigger != TaskTrigger::Manual {
        return Err(ServiceError::Invalid("bu vazifa avtomatik aniqlanadi"));
    }
    let ws = week_start(local_date(env.clock.now()), WEEK_ANCHOR);
    let existing = repo::list::<TaskCompletion>(db.conn(), &ctx.household_id)?
        .into_iter()
        .find(|c| c.task_id == task_id && c.week_start == ws);
    match (existing, done) {
        (None, true) => repo::insert(
            db.conn(),
            &TaskCompletion {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                chapter_id: chapter_id.to_owned(),
                task_id: task_id.to_owned(),
                week_start: ws,
                completed_at: env.clock.now(),
            },
        )?,
        (Some(c), false) => {
            repo::soft_delete::<TaskCompletion>(db.conn(), &c.meta.id, env.clock.now())?
        }
        _ => {}
    }
    Ok(())
}

/// «Daftar sahifasi»ni saqlaydi (bo'sh matn ham mumkin: sahifa tozalanadi).
///
/// # Errors
/// Bob ochilmagan yoki matn juda uzun bo'lsa.
pub fn save_page(
    db: &mut Database,
    env: &Env<'_>,
    ctx: &Ctx,
    catalog: &Catalog,
    chapter_id: &str,
    body: &str,
) -> Result<(), ServiceError> {
    catalog.chapter(chapter_id).ok_or(ServiceError::NotFound)?;
    ensure_opened(db.conn(), ctx, chapter_id)?;
    if body.chars().count() > MAX_PAGE_CHARS {
        return Err(ServiceError::Invalid("sahifa juda uzun (5000 belgigacha)"));
    }
    match page(db.conn(), ctx, chapter_id)? {
        Some(mut p) => {
            p.body = body.to_owned();
            repo::update(db.conn(), &p, env.clock.now())?;
        }
        None => repo::insert(
            db.conn(),
            &DaftarPage {
                meta: Meta::new(env.ids, env.clock, &ctx.household_id, env.device_id),
                chapter_id: chapter_id.to_owned(),
                body: body.to_owned(),
            },
        )?,
    }
    Ok(())
}
