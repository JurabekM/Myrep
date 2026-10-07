//! D5 commandlari: boblar, haftalik vazifalar, «Daftar sahifasi», ochilish sharti.

use content::{Catalog, ReleaseMode, TaskTrigger, UnlockDecision, UnlockPolicy};
use domain::date_to_string;
use serde::{Deserialize, Serialize};
use services::{
    learning::{self, ChapterStatus, TaskStatus},
    ServiceError,
};
use specta::Type;
use tauri::State;

use crate::commands::{with_session, AppSession, CommandError};

fn catalog() -> Result<&'static Catalog, ServiceError> {
    Catalog::bundled().map_err(|_| ServiceError::Invalid("kontent yuklanmadi"))
}

fn u32_of(n: usize) -> u32 {
    u32::try_from(n).unwrap_or(u32::MAX)
}

#[derive(Debug, Serialize, Type)]
pub struct TaskDto {
    pub id: String,
    pub title: String,
    pub done: bool,
    /// Ma'lumotdan avtomatik aniqlangan.
    pub auto_detected: bool,
    /// Foydalanuvchi qo'lda belgilaydigan vazifa.
    pub manual: bool,
}

fn task_dto(t: &TaskStatus) -> TaskDto {
    TaskDto {
        id: t.id.clone(),
        title: t.title.clone(),
        done: t.done,
        auto_detected: t.auto,
        manual: t.trigger == TaskTrigger::Manual,
    }
}

#[derive(Debug, Serialize, Type)]
pub struct ChapterEntryDto {
    pub id: String,
    pub title: String,
    pub law: u32,
    pub order: u32,
    pub opened: bool,
    pub opened_on: Option<String>,
    pub is_current: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct UnlockDto {
    pub unlocked: bool,
    pub satisfied_weeks: u32,
    pub needed_weeks: u32,
    /// Hali birorta ham hafta tugamagan bo'lsa 0.
    pub weeks_in_window: u32,
}

#[derive(Debug, Serialize, Type)]
pub struct PolicyDto {
    pub window_weeks: u32,
    pub min_satisfied_weeks: u32,
    pub min_tasks_per_week: u32,
}

fn policy_dto(p: UnlockPolicy) -> PolicyDto {
    PolicyDto {
        window_weeks: p.window_weeks(),
        min_satisfied_weeks: p.min_satisfied_weeks(),
        min_tasks_per_week: p.min_tasks_per_week(),
    }
}

#[derive(Debug, Serialize, Type)]
pub struct JourneyDto {
    pub chapters: Vec<ChapterEntryDto>,
    pub current_id: String,
    pub current_title: String,
    pub opened_this_week: bool,
    pub week_start: String,
    pub week_tasks: Vec<TaskDto>,
    pub week_done: u32,
    pub unlock: Option<UnlockDto>,
    pub policy: PolicyDto,
}

#[derive(Debug, Serialize, Type)]
pub struct BlockDto {
    pub id: String,
    pub text: String,
    pub source: Option<String>,
    /// Ulamo tekshiruvidan o'tmagan (faqat ishlab chiqish rejimida ko'rinadi).
    pub unreviewed: bool,
}

#[derive(Debug, Serialize, Type)]
pub struct ChapterDetailDto {
    pub id: String,
    pub title: String,
    pub law: u32,
    pub placeholder: bool,
    pub blocks: Vec<BlockDto>,
    pub page_prompt: String,
    pub page_body: String,
    pub tasks: Vec<TaskDto>,
}

#[tauri::command]
#[specta::specta]
pub fn journey(state: State<'_, AppSession>) -> Result<JourneyDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let cat = catalog()?;
            let j = learning::journey(db, env, ctx, cat)?;
            let current_title = cat
                .chapter(&j.current_id)
                .map(|c| c.title.clone())
                .unwrap_or_default();
            Ok(JourneyDto {
                chapters: j
                    .chapters
                    .iter()
                    .map(|c| ChapterEntryDto {
                        id: c.id.clone(),
                        title: c.title.clone(),
                        law: u32::from(c.law),
                        order: c.order,
                        opened: matches!(c.status, ChapterStatus::Opened { .. }),
                        opened_on: match c.status {
                            ChapterStatus::Opened { opened_on } => date_to_string(opened_on).ok(),
                            ChapterStatus::Locked => None,
                        },
                        is_current: c.is_current,
                    })
                    .collect(),
                current_id: j.current_id,
                current_title,
                opened_this_week: j.opened_this_week,
                week_start: date_to_string(j.week_start).unwrap_or_default(),
                week_done: u32_of(j.week_tasks.iter().filter(|t| t.done).count()),
                week_tasks: j.week_tasks.iter().map(task_dto).collect(),
                unlock: j.unlock.map(|u| match u {
                    UnlockDecision::Unlocked => UnlockDto {
                        unlocked: true,
                        satisfied_weeks: 0,
                        needed_weeks: 0,
                        weeks_in_window: 0,
                    },
                    UnlockDecision::Locked {
                        satisfied_weeks,
                        needed_weeks,
                        weeks_in_window,
                    } => UnlockDto {
                        unlocked: false,
                        satisfied_weeks,
                        needed_weeks,
                        weeks_in_window,
                    },
                }),
                policy: policy_dto(j.policy),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn chapter_detail(
    id: String,
    state: State<'_, AppSession>,
) -> Result<ChapterDetailDto, CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            let d =
                learning::chapter_detail(db, env, ctx, catalog()?, &id, ReleaseMode::for_build())?;
            Ok(ChapterDetailDto {
                id: d.id,
                title: d.title,
                law: u32::from(d.law),
                placeholder: d.placeholder,
                blocks: d
                    .blocks
                    .into_iter()
                    .map(|b| BlockDto {
                        id: b.id,
                        text: b.text,
                        source: b.source,
                        unreviewed: b.unreviewed,
                    })
                    .collect(),
                page_prompt: d.page_prompt,
                page_body: d.page_body,
                tasks: d.tasks.iter().map(task_dto).collect(),
            })
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn set_task_done(
    chapter_id: String,
    task_id: String,
    done: bool,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            learning::set_task_done(db, env, ctx, catalog()?, &chapter_id, &task_id, done)
        })
    })
}

#[tauri::command]
#[specta::specta]
pub fn save_page(
    chapter_id: String,
    body: String,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| learning::save_page(db, env, ctx, catalog()?, &chapter_id, &body))
    })
}

#[derive(Debug, Deserialize, Type)]
pub struct PolicyInput {
    pub window_weeks: u32,
    pub min_satisfied_weeks: u32,
    pub min_tasks_per_week: u32,
}

#[tauri::command]
#[specta::specta]
pub fn set_unlock_policy(
    input: PolicyInput,
    state: State<'_, AppSession>,
) -> Result<(), CommandError> {
    with_session(&state, |s| {
        s.run(|db, env, ctx| {
            learning::set_policy(
                db,
                env,
                ctx,
                input.window_weeks,
                input.min_satisfied_weeks,
                input.min_tasks_per_week,
            )
        })
    })
}
