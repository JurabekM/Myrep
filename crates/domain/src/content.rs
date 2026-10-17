//! Kontent modeli: boblar, bloklar, haftalik vazifalar va ularning avtomatik hodisalari (SPEC 1.1, 2C.6).
//!
//! Kontent `spec/content/chapters.json` da (mobil bilan bir xil fayl, sxema — `content_schema.json`).
//! Bu modul faqat tuzilmani va ko'rinish qoidasini beradi; JSON o'qish [`crate::content_parser`] da.

use std::collections::BTreeMap;

/// Ko'p tilli matn: `uz` majburiy (asosiy), `ru` ixtiyoriy (bo'lmasa `uz`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct LocalizedText {
    values: BTreeMap<String, String>,
}

impl LocalizedText {
    /// Matnlarni kalit (`uz`/`ru`) bo'yicha qo'yadi. `uz` bo'lmasa — `None`.
    pub fn new(values: BTreeMap<String, String>) -> Option<Self> {
        values.contains_key(LANG_UZ).then_some(Self { values })
    }

    /// Berilgan til matni; yo'q bo'lsa o'zbekcha.
    pub fn of(&self, language: &str) -> &str {
        self.values
            .get(language)
            .or_else(|| self.values.get(LANG_UZ))
            .map(String::as_str)
            .unwrap_or_default()
    }

    /// Ruscha matn bormi (UI faqat mavjud bo'lsa ruscha ko'rsatadi).
    pub fn has(&self, language: &str) -> bool {
        self.values.contains_key(language)
    }
}

/// O'zbek tili kodi (asosiy).
pub const LANG_UZ: &str = "uz";
/// Rus tili kodi (ikkinchi).
pub const LANG_RU: &str = "ru";

/// Diniy matnni ulamo tekshirganmi (SPEC 3). `Pending` — production'da ko'rsatilmaydi.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ReligiousReviewStatus {
    /// Ulamo tekshiruvidan o'tmagan.
    Pending,
    /// Tasdiqlangan.
    Approved,
}

/// Haftalik vazifani ilova o'zi belgilaydigan hodisa (MVP_PLAN Vazifa 6).
///
/// Kontent JSON'ida `autoComplete` shu [`code`](Self::code) bilan yoziladi; noma'lum kod
/// bobni yaroqsiz qiladi (jimgina e'tiborsiz qolmaydi).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum TaskTrigger {
    /// «Kelajagim» ekrani ochildi.
    VaultOpened,
    /// «Kelajagim»ga pul qo'yildi (daromad ulushi).
    VaultFirstDeposit,
    /// Daromaddan ulush ajratildi.
    IncomeShared,
    /// Oylik audit yakunlandi.
    AuditCompleted,
    /// «Daftar sahifasi»ga qonun yozildi.
    DaftarPageWritten,
    /// Xarajat yozildi.
    ExpenseRecorded,
    /// Obunalar ko'rib chiqildi (keyingi modul).
    SubscriptionsReviewed,
    /// Konvert yaratildi (keyingi modul).
    EnvelopeCreated,
    /// Havas xarajatlari chegarasi oilada kelishildi (keyingi modul).
    HavasLimitAgreed,
    /// Narx solishtirildi (keyingi modul).
    PriceComparisonDone,
    /// Favqulodda jamg'arma maqsadi qo'yildi (keyingi modul).
    EmergencyTargetSet,
    /// Barcha qarzlar ro'yxatga olindi (keyingi modul).
    DebtInventoryCompleted,
    /// Qarzdan chiqish rejasi tuzildi (keyingi modul).
    PayoffPlanCreated,
    /// Taklif tekshirildi (keyingi modul).
    OfferChecked,
    /// Halol tadbirkorlik g'oyasi yozildi (keyingi modul).
    VentureIdeaCreated,
    /// Kelishuv imzolandi (keyingi modul).
    AgreementSigned,
    /// Og'zaki kelishuv yozib olindi (keyingi modul).
    OralAgreementRecorded,
}

impl TaskTrigger {
    /// Barcha hodisalar (kontent tekshiruvi va testlar uchun).
    pub const ALL: [Self; 17] = [
        Self::VaultOpened,
        Self::VaultFirstDeposit,
        Self::IncomeShared,
        Self::AuditCompleted,
        Self::DaftarPageWritten,
        Self::ExpenseRecorded,
        Self::SubscriptionsReviewed,
        Self::EnvelopeCreated,
        Self::HavasLimitAgreed,
        Self::PriceComparisonDone,
        Self::EmergencyTargetSet,
        Self::DebtInventoryCompleted,
        Self::PayoffPlanCreated,
        Self::OfferChecked,
        Self::VentureIdeaCreated,
        Self::AgreementSigned,
        Self::OralAgreementRecorded,
    ];

    /// JSON'dagi barqaror kod.
    pub const fn code(self) -> &'static str {
        match self {
            Self::VaultOpened => "VAULT_OPENED",
            Self::VaultFirstDeposit => "VAULT_FIRST_DEPOSIT",
            Self::IncomeShared => "INCOME_SHARED",
            Self::AuditCompleted => "AUDIT_COMPLETED",
            Self::DaftarPageWritten => "DAFTAR_PAGE_WRITTEN",
            Self::ExpenseRecorded => "EXPENSE_RECORDED",
            Self::SubscriptionsReviewed => "SUBSCRIPTIONS_REVIEWED",
            Self::EnvelopeCreated => "ENVELOPE_CREATED",
            Self::HavasLimitAgreed => "HAVAS_LIMIT_AGREED",
            Self::PriceComparisonDone => "PRICE_COMPARISON_DONE",
            Self::EmergencyTargetSet => "EMERGENCY_TARGET_SET",
            Self::DebtInventoryCompleted => "DEBT_INVENTORY_COMPLETED",
            Self::PayoffPlanCreated => "PAYOFF_PLAN_CREATED",
            Self::OfferChecked => "OFFER_CHECKED",
            Self::VentureIdeaCreated => "VENTURE_IDEA_CREATED",
            Self::AgreementSigned => "AGREEMENT_SIGNED",
            Self::OralAgreementRecorded => "ORAL_AGREEMENT_RECORDED",
        }
    }

    /// Koddan hodisa. Noma'lum kod — `None`.
    pub fn from_code(code: &str) -> Option<Self> {
        Self::ALL.into_iter().find(|trigger| trigger.code() == code)
    }
}

/// Bob matn bloki. Diniy blok ulamo tasdig'i bilan birga keladi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContentBlock {
    /// Oddiy abzats (qissa matni).
    Paragraph(LocalizedText),
    /// Murabbiy (Sobir hoji) so'zi yoki ajratilgan iqtibos.
    Quote(LocalizedText),
    /// Oyat, hadis yoki rivoyat. Manba va ulamo tekshiruvi majburiy.
    Religious {
        /// Matn.
        text: LocalizedText,
        /// Manba (oyat/hadis raqami).
        source: LocalizedText,
        /// Ulamo tekshiruvi holati.
        status: ReligiousReviewStatus,
    },
}

/// Bob qonuni: raqami va matni («Daftar sahifasi» sarlavhasi uchun).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Law {
    /// Qonun raqami (1–5).
    pub number: u32,
    /// Qonun matni.
    pub text: LocalizedText,
}

/// Haftalik vazifa. ID `chapterId.tN` ko'rinishida (masalan, `ch01.t1`).
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct WeeklyTask {
    /// Barqaror ID.
    pub id: String,
    /// Vazifa matni.
    pub text: LocalizedText,
    /// Ilova avtomatik belgilaydigan hodisa; `None` — faqat qo'lda belgilanadi.
    pub trigger: Option<TaskTrigger>,
}

/// Bob: qissa, qonun va aniq 3 ta haftalik vazifa.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Chapter {
    /// Barqaror ID (kichik harf va raqam).
    pub id: String,
    /// Ochilish tartibi: 1, 2, 3 …
    pub order: u32,
    /// Sarlavha.
    pub title: LocalizedText,
    /// Bloklar (kamida bittasi).
    pub blocks: Vec<ContentBlock>,
    /// Qonun.
    pub law: Law,
    /// Aniq 3 ta vazifa.
    pub weekly_tasks: Vec<WeeklyTask>,
    /// Audio (https), bo'lmasa `None`.
    pub audio_url: Option<String>,
}

impl Chapter {
    /// Ko'rsatiladigan bloklar. Tasdiqlanmagan (`Pending`) diniy blok faqat [`show_pending`](Self::visible_blocks)
    /// `true` bo'lganda chiqadi — release'da hech qachon.
    pub fn visible_blocks(&self, show_pending: bool) -> Vec<&ContentBlock> {
        self.blocks
            .iter()
            .filter(|block| match block {
                ContentBlock::Religious { status, .. } => {
                    *status == ReligiousReviewStatus::Approved || show_pending
                }
                ContentBlock::Paragraph(_) | ContentBlock::Quote(_) => true,
            })
            .collect()
    }
}

/// Kontentni yuklash natijasi: yaroqli boblar va topilgan xatolar.
/// Buzuq bob o'tkazib yuboriladi, ilova yiqilmaydi.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ContentLoadResult {
    /// `order` bo'yicha tartiblangan.
    pub chapters: Vec<Chapter>,
    /// Xato xabarlari (sabab bilan).
    pub errors: Vec<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    fn text(uz: &str) -> LocalizedText {
        LocalizedText::new(BTreeMap::from([(LANG_UZ.to_owned(), uz.to_owned())])).expect("uz bor")
    }

    #[test]
    fn matn_tilsiz_bolsa_ozbekcha_qaytadi() {
        let t = text("Salom");
        assert_eq!(t.of(LANG_RU), "Salom");
        assert!(!t.has(LANG_RU));
    }

    #[test]
    fn uz_bolmasa_matn_yaratilmaydi() {
        let only_ru = BTreeMap::from([(LANG_RU.to_owned(), "Привет".to_owned())]);
        assert!(LocalizedText::new(only_ru).is_none());
    }

    #[test]
    fn trigger_kodi_ikki_tomonlama_mos() {
        for trigger in TaskTrigger::ALL {
            assert_eq!(TaskTrigger::from_code(trigger.code()), Some(trigger));
        }
        assert_eq!(TaskTrigger::from_code("NOMA_LUM"), None);
    }

    #[test]
    fn pending_diniy_blok_relizda_korinmaydi() {
        let chapter = Chapter {
            id: "ch01".to_owned(),
            order: 1,
            title: text("1-bob"),
            blocks: vec![
                ContentBlock::Paragraph(text("Matn")),
                ContentBlock::Religious {
                    text: text("Oyat"),
                    source: text("Manba"),
                    status: ReligiousReviewStatus::Pending,
                },
            ],
            law: Law {
                number: 1,
                text: text("Qonun"),
            },
            weekly_tasks: Vec::new(),
            audio_url: None,
        };
        assert_eq!(chapter.visible_blocks(false).len(), 1);
        assert_eq!(chapter.visible_blocks(true).len(), 2);
    }

    #[test]
    fn tasdiqlangan_diniy_blok_korinadi() {
        let chapter = Chapter {
            id: "ch01".to_owned(),
            order: 1,
            title: text("1-bob"),
            blocks: vec![ContentBlock::Religious {
                text: text("Oyat"),
                source: text("Manba"),
                status: ReligiousReviewStatus::Approved,
            }],
            law: Law {
                number: 1,
                text: text("Qonun"),
            },
            weekly_tasks: Vec::new(),
            audio_url: None,
        };
        assert_eq!(chapter.visible_blocks(false).len(), 1);
    }
}
