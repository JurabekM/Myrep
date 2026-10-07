//! Kontent dvigateli (D5). Qissa matnlari litsenziya hal bo'lguncha placeholder.
#![cfg_attr(test, allow(clippy::unwrap_used, clippy::expect_used))]

mod catalog;
mod model;
mod triggers;
mod unlock;

pub use catalog::{Catalog, ContentError, ReleaseMode, VisibleBlock, TASKS_PER_CHAPTER};
pub use model::{Block, Chapter, ReviewStatus, Task, TaskTrigger};
pub use triggers::{trigger_met, WeekFacts};
pub use unlock::{decide, PolicyError, UnlockDecision, UnlockPolicy, WeekResult};
