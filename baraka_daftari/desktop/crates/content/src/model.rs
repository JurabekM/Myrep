use serde::{Deserialize, Serialize};

/// Diniy matn ulamo tekshiruvi holati (`religiousReviewStatus`).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ReviewStatus {
    Pending,
    Approved,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "kind", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Block {
    Text {
        id: String,
        text: String,
    },
    /// Oyat, hadis, rivoyat: `source` majburiy; `Approved` bo'lmasa release'da chiqmaydi.
    Religious {
        id: String,
        text: String,
        source: String,
        review_status: ReviewStatus,
    },
}

impl Block {
    #[must_use]
    pub fn id(&self) -> &str {
        match self {
            Self::Text { id, .. } | Self::Religious { id, .. } => id,
        }
    }
}

/// Vazifa qanday bajarilgan hisoblanadi.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[serde(tag = "type", rename_all = "SCREAMING_SNAKE_CASE")]
pub enum TaskTrigger {
    /// Foydalanuvchi o'zi belgilaydi.
    Manual,
    /// Hafta ichida kamida `min` ta daromad kiritilgan.
    IncomeRecorded { min: u32 },
    /// Hafta ichida kamida `min_days` turli kunda «Kelajagim»ga ajratma qilingan.
    AllocationMade { min_days: u32 },
    /// Hafta ichida oylik audit ustasi bilan kamida bitta kategoriya to'ldirilgan.
    AuditCompleted,
    /// Hafta ichida kamida bitta majburiyat qo'shilgan.
    ObligationAdded,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Task {
    pub id: String,
    pub title: String,
    pub trigger: TaskTrigger,
}

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct Chapter {
    pub id: String,
    /// Qaysi qonunga tegishli (1..=7).
    pub law: u8,
    /// Ochilish tartibi (1 dan).
    pub order: u32,
    pub title: String,
    /// `true` — matn litsenziya hal bo'lguncha placeholder.
    pub placeholder: bool,
    pub blocks: Vec<Block>,
    /// «Daftar sahifasi» uchun savol.
    pub page_prompt: String,
    pub tasks: Vec<Task>,
}
