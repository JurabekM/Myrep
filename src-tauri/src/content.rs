//! D5 kontent dvigateli (SPEC 1.1, 2C.6): boblar, odat asosidagi ochilish, haftalik vazifalar,
//! hodisa bo'yicha avtomatik belgilash va «Daftar sahifasi».
//!
//! Kontent `spec/content/chapters.json` dan kompilyatsiyada joylanadi (fayl — mobil bilan bir xil).
//! Qoidalar `domain`da, saqlash `storage`da; bu yerda ular ulanadi va DTO tayyorlanadi.

use std::collections::{BTreeMap, BTreeSet};
use std::sync::OnceLock;

use domain::calendar::{DateRange, tashkent_date, week_of};
use domain::content::{LANG_RU, LANG_UZ, WeeklyTask};
use domain::content_parser;
use domain::{
    Chapter, ChapterUnlock, ChapterUnlockPolicy, ContentBlock, ContentLoadResult, DaftarPage,
    DomainError, HabitUnlockPolicy, TaskCompletion, TaskTrigger, UnlockContext,
};
use storage::{DaftarPageRepo, Database, StorageError, TaskCompletionRepo};
use time::{Date, OffsetDateTime};
use tracing::error;

use crate::dto::{
    ChapterCardDto, ChapterDto, ContentBlockDto, DaftarPageDto, LawDto, LocalizedDto, TaskDto,
    WeeklyTasksDto,
};
use crate::finance::{self, DEVICE_ID, UuidV7, date_text};
use crate::session::SessionError;

/// Kontent manbasi (kompilyatsiya vaqtida joylanadi).
const CHAPTERS_JSON: &str = include_str!("../../spec/content/chapters.json");

/// Tasdiqlanmagan (`PENDING`) diniy blokni ko'rsatish. Faqat ishlab chiqish (debug) buildida —
/// release'da har doim yashirin (SPEC 3, DESKTOP_PROMPT.md 8).
pub const SHOW_PENDING_RELIGIOUS: bool = cfg!(debug_assertions);

/// Kontent bir marta o'qiladi. Buzuq bob bo'lsa — log'ga yoziladi (matn emas, faqat soni).
fn catalog() -> &'static ContentLoadResult {
    static CATALOG: OnceLock<ContentLoadResult> = OnceLock::new();
    CATALOG.get_or_init(|| {
        let result = content_parser::parse(CHAPTERS_JSON);
        if !result.errors.is_empty() {
            error!(
                xatolar = result.errors.len(),
                "kontentning bir qismi o'qilmadi"
            );
        }
        result
    })
}

/// Bob ochilishi qoidasi (standart: 2 ta vazifa, 7 kun).
fn policy() -> HabitUnlockPolicy {
    HabitUnlockPolicy::default()
}

/// Bir lahzadagi holat: bob ochilishi, joriy bob va bajarilishlar.
struct Snapshot {
    household_id: String,
    today: Date,
    chapters: &'static [Chapter],
    unlocks: Vec<ChapterUnlock>,
    /// Vazifa ID → birinchi bajarilish sanasi (Toshkent).
    first_completed: BTreeMap<String, Date>,
    /// Joriy (eng so'nggi ochilgan) bobning indeksi.
    current: Option<usize>,
}

impl Snapshot {
    fn is_unlocked(&self, index: usize) -> bool {
        self.unlocks
            .get(index)
            .is_some_and(|unlock| unlock.is_unlocked_on(self.today))
    }

    /// Bobni ID bo'yicha topadi (indeks).
    fn index_of(&self, chapter_id: &str) -> Option<usize> {
        self.chapters
            .iter()
            .position(|chapter| chapter.id == chapter_id)
    }

    /// Joriy bobning vazifa egasi — `task_id` shu bobga tegishlimi.
    fn current_task(&self, task_id: &str) -> Option<&WeeklyTask> {
        let chapter = self.chapters.get(self.current?)?;
        chapter.weekly_tasks.iter().find(|task| task.id == task_id)
    }
}

/// Joriy holatni yig'adi: xonadon, Toshkent bugungi sanasi, ochilish va birinchi bajarilishlar.
fn snapshot(db: &Database, now: OffsetDateTime) -> Result<Snapshot, SessionError> {
    let context = finance::context(db, now)?;
    let household = &context.household;
    let today = context.today;
    let chapters = catalog().chapters.as_slice();
    let first_completed: BTreeMap<String, Date> = TaskCompletionRepo::new(db.connection())
        .first_completed_at(&household.id)?
        .into_iter()
        .map(|(task_id, at)| (task_id, tashkent_date(at)))
        .collect();
    let unlock_context = UnlockContext {
        program_start: tashkent_date(household.meta.created_at),
        today,
        first_completed: first_completed.clone(),
    };
    let unlocks = policy().evaluate(chapters, &unlock_context);
    let current = unlocks
        .iter()
        .rposition(|unlock| unlock.is_unlocked_on(today));
    Ok(Snapshot {
        household_id: household.id.clone(),
        today,
        chapters,
        unlocks,
        first_completed,
        current,
    })
}

/// Bu haftaning kalendar oralig'i (jumadan boshlanadi).
fn this_week(today: Date) -> Result<DateRange, SessionError> {
    week_of(today).ok_or(SessionError::Domain(DomainError::InvalidDay))
}

fn localized(text: &domain::content::LocalizedText) -> LocalizedDto {
    LocalizedDto {
        uz: text.of(LANG_UZ).to_owned(),
        ru: text.of(LANG_RU).to_owned(),
    }
}

fn law_dto(chapter: &Chapter) -> LawDto {
    LawDto {
        number: chapter.law.number,
        text: localized(&chapter.law.text),
    }
}

fn block_dto(block: &ContentBlock) -> ContentBlockDto {
    match block {
        ContentBlock::Paragraph(text) => ContentBlockDto::Paragraph {
            text: localized(text),
        },
        ContentBlock::Quote(text) => ContentBlockDto::Quote {
            text: localized(text),
        },
        ContentBlock::Religious {
            text,
            source,
            status,
        } => ContentBlockDto::Religious {
            text: localized(text),
            source: localized(source),
            approved: *status == domain::content::ReligiousReviewStatus::Approved,
        },
    }
}

/// Bobning ko'rsatiladigan bloklari. `show_pending` `false` bo'lsa tasdiqlanmagan diniy blok chiqmaydi.
fn visible_blocks(chapter: &Chapter, show_pending: bool) -> Vec<ContentBlockDto> {
    chapter
        .visible_blocks(show_pending)
        .into_iter()
        .map(block_dto)
        .collect()
}

fn task_dto(task: &WeeklyTask, done: bool) -> TaskDto {
    TaskDto {
        id: task.id.clone(),
        text: localized(&task.text),
        auto_completed: task.trigger.is_some(),
        done,
    }
}

fn page_dto(page: &DaftarPage) -> DaftarPageDto {
    DaftarPageDto {
        chapter_id: page.chapter_id.clone(),
        law_number: page.law_number,
        body: page.body.clone(),
        updated_on: date_text(tashkent_date(page.meta.updated_at)),
    }
}

/// Shu hafta bajarilgan vazifa ID'lari.
fn week_done(
    db: &Database,
    household_id: &str,
    week: DateRange,
) -> Result<BTreeSet<String>, SessionError> {
    Ok(TaskCompletionRepo::new(db.connection())
        .list_for_week(household_id, week.start)?
        .into_iter()
        .map(|completion| completion.task_id)
        .collect())
}

/// Bob ro'yxati (ochiq-yopiqlik, ochilish sanasi, kerakli vazifalar).
pub fn list_chapters(
    db: &Database,
    now: OffsetDateTime,
) -> Result<Vec<ChapterCardDto>, SessionError> {
    let snap = snapshot(db, now)?;
    Ok(snap
        .chapters
        .iter()
        .zip(&snap.unlocks)
        .map(|(chapter, unlock)| ChapterCardDto {
            id: chapter.id.clone(),
            order: chapter.order,
            title: localized(&chapter.title),
            unlocked: unlock.is_unlocked_on(snap.today),
            unlock_date: unlock.date.map(date_text),
            tasks_remaining: unlock.tasks_remaining,
            not_before: unlock.not_before.map(date_text),
        })
        .collect())
}

/// Ochiq bob sahifasi. Yopiq bob — [`DomainError::ChapterLocked`].
pub fn get_chapter(
    db: &Database,
    now: OffsetDateTime,
    chapter_id: &str,
) -> Result<ChapterDto, SessionError> {
    let snap = snapshot(db, now)?;
    let index = snap
        .index_of(chapter_id)
        .ok_or(SessionError::Storage(StorageError::NotFound))?;
    if !snap.is_unlocked(index) {
        return Err(DomainError::ChapterLocked.into());
    }
    let page =
        DaftarPageRepo::new(db.connection()).find_for_chapter(&snap.household_id, chapter_id)?;
    let is_current = snap.current == Some(index);
    let done_now = if is_current {
        week_done(db, &snap.household_id, this_week(snap.today)?)?
    } else {
        BTreeSet::new()
    };
    let chapter = &snap.chapters[index];
    Ok(chapter_view(
        chapter,
        is_current,
        &snap.first_completed,
        &done_now,
        page.as_ref(),
        SHOW_PENDING_RELIGIOUS,
    ))
}

/// Bob sahifasi DTO'si. [`get_chapter`] va testlar uchun umumiy.
fn chapter_view(
    chapter: &Chapter,
    is_current: bool,
    first_completed: &BTreeMap<String, Date>,
    done_this_week: &BTreeSet<String>,
    page: Option<&DaftarPage>,
    show_pending: bool,
) -> ChapterDto {
    ChapterDto {
        id: chapter.id.clone(),
        order: chapter.order,
        title: localized(&chapter.title),
        blocks: visible_blocks(chapter, show_pending),
        law: law_dto(chapter),
        weekly_tasks: chapter
            .weekly_tasks
            .iter()
            .map(|task| {
                let done = if is_current {
                    done_this_week.contains(&task.id)
                } else {
                    first_completed.contains_key(&task.id)
                };
                task_dto(task, done)
            })
            .collect(),
        is_current,
        audio_url: chapter.audio_url.clone(),
        daftar_page: page.map(page_dto),
    }
}

/// Joriy bobning shu haftalik vazifalari. Hech bob ochiq bo'lmasa — `None`.
pub fn weekly_tasks(
    db: &Database,
    now: OffsetDateTime,
) -> Result<Option<WeeklyTasksDto>, SessionError> {
    let snap = snapshot(db, now)?;
    let Some(current) = snap.current else {
        return Ok(None);
    };
    let chapter = &snap.chapters[current];
    let week = this_week(snap.today)?;
    let done = week_done(db, &snap.household_id, week)?;
    Ok(Some(WeeklyTasksDto {
        chapter_id: chapter.id.clone(),
        chapter_title: localized(&chapter.title),
        week_start: date_text(week.start),
        tasks: chapter
            .weekly_tasks
            .iter()
            .map(|task| task_dto(task, done.contains(&task.id)))
            .collect(),
    }))
}

/// Joriy bobning vazifasini shu hafta uchun qo'lda belgilaydi yoki bekor qiladi.
pub fn set_task_done(
    db: &Database,
    now: OffsetDateTime,
    task_id: &str,
    done: bool,
) -> Result<Option<WeeklyTasksDto>, SessionError> {
    let snap = snapshot(db, now)?;
    if snap.current_task(task_id).is_none() {
        return Err(DomainError::TaskNotCurrent.into());
    }
    let week = this_week(snap.today)?;
    let completions = TaskCompletionRepo::new(db.connection());
    let existing: Vec<TaskCompletion> = completions
        .list_for_week(&snap.household_id, week.start)?
        .into_iter()
        .filter(|completion| completion.task_id == task_id)
        .collect();
    if done && existing.is_empty() {
        let completion = TaskCompletion::create(
            &domain::IdGen::next_id(&UuidV7),
            &snap.household_id,
            task_id,
            week.start,
            false,
            now,
            DEVICE_ID,
        )?;
        completions.insert(&completion)?;
    } else if !done {
        for completion in &existing {
            completions.soft_delete(&completion.id, now)?;
        }
    }
    weekly_tasks(db, now)
}

/// Ilova hodisasi: joriy bobning shu hodisaga bog'liq vazifalari avtomatik belgilanadi.
/// Shu hafta allaqachon bajarilgan vazifalar qayta yozilmaydi. Joriy bob bo'lmasa — hech narsa qilinmaydi.
pub fn record_event(
    db: &Database,
    now: OffsetDateTime,
    trigger: TaskTrigger,
) -> Result<(), SessionError> {
    let snap = snapshot(db, now)?;
    let Some(current) = snap.current else {
        return Ok(());
    };
    let week = this_week(snap.today)?;
    let done = week_done(db, &snap.household_id, week)?;
    let completions = TaskCompletionRepo::new(db.connection());
    for task in &snap.chapters[current].weekly_tasks {
        if task.trigger != Some(trigger) || done.contains(&task.id) {
            continue;
        }
        let completion = TaskCompletion::create(
            &domain::IdGen::next_id(&UuidV7),
            &snap.household_id,
            &task.id,
            week.start,
            true,
            now,
            DEVICE_ID,
        )?;
        completions.insert(&completion)?;
    }
    Ok(())
}

/// «Daftar sahifasi»ni saqlaydi (bob uchun bitta, yangilanadi). Vazifa `DAFTAR_PAGE_WRITTEN` hodisasi bilan
/// belgilanadi. Yopiq bob — [`DomainError::ChapterLocked`].
pub fn save_daftar_page(
    db: &Database,
    now: OffsetDateTime,
    chapter_id: &str,
    body: &str,
) -> Result<DaftarPageDto, SessionError> {
    let snap = snapshot(db, now)?;
    let index = snap
        .index_of(chapter_id)
        .ok_or(SessionError::Storage(StorageError::NotFound))?;
    if !snap.is_unlocked(index) {
        return Err(DomainError::ChapterLocked.into());
    }
    let chapter = &snap.chapters[index];
    let pages = DaftarPageRepo::new(db.connection());
    let saved = match pages.find_for_chapter(&snap.household_id, chapter_id)? {
        Some(existing) => {
            let edited = existing.with_body(body, now)?;
            pages.update_body(&edited)?;
            edited
        }
        None => {
            let page = DaftarPage::create(
                &domain::IdGen::next_id(&UuidV7),
                &snap.household_id,
                chapter_id,
                chapter.law.number,
                body,
                now,
                DEVICE_ID,
            )?;
            pages.insert(&page)?;
            page
        }
    };
    record_event(db, now, TaskTrigger::DaftarPageWritten)?;
    Ok(page_dto(&saved))
}

#[cfg(test)]
mod tests {
    #![allow(clippy::expect_used, clippy::unwrap_used)]

    use domain::Household;
    use security::SecretKey;
    use storage::HouseholdRepo;
    use time::macros::datetime;

    use super::*;

    fn fresh() -> Database {
        Database::open_in_memory(&SecretKey::from_array([3; 32])).expect("xotirada baza")
    }

    /// Dastur 2026-10-01 (payshanba) da boshlangan xonadon.
    fn started(db: &Database) {
        let created = datetime!(2026-10-01 06:00 UTC);
        let household = Household::create(
            &domain::IdGen::next_id(&UuidV7),
            "Asosiy daftar",
            created,
            DEVICE_ID,
        )
        .expect("xonadon");
        HouseholdRepo::new(db.connection())
            .insert(&household)
            .expect("qo'shilsin");
    }

    fn at(day: u8) -> OffsetDateTime {
        time::Date::from_calendar_date(2026, time::Month::October, day)
            .expect("sana")
            .with_hms(6, 0, 0)
            .expect("vaqt")
            .assume_utc()
    }

    /// Ko'rinadigan blokda tasdiqlanmagan diniy blok bormi.
    fn has_pending_block(chapter: &ChapterDto) -> bool {
        chapter.blocks.iter().any(|block| {
            matches!(
                block,
                ContentBlockDto::Religious {
                    approved: false,
                    ..
                }
            )
        })
    }

    #[test]
    fn birinchi_bob_ochiq_qolganlari_yopiq() {
        let db = fresh();
        started(&db);
        let cards = list_chapters(&db, at(1)).expect("ro'yxat");
        assert_eq!(cards.len(), 7);
        assert!(cards[0].unlocked);
        assert!(cards[1..].iter().all(|card| !card.unlocked));
        assert_eq!(cards[1].tasks_remaining, 2);
    }

    #[test]
    fn yopiq_bob_sahifasi_ochilmaydi() {
        let db = fresh();
        started(&db);
        let err = get_chapter(&db, at(1), "ch02").expect_err("yopiq");
        assert!(matches!(
            err,
            SessionError::Domain(DomainError::ChapterLocked)
        ));
    }

    #[test]
    fn release_da_pending_diniy_blok_korinmaydi() {
        // Haqiqiy kontent: har bobda PENDING diniy blok bor. Release ko'rinishi (show_pending = false).
        let chapter = &catalog().chapters[0];
        let view = chapter_view(
            chapter,
            true,
            &BTreeMap::new(),
            &BTreeSet::new(),
            None,
            false,
        );
        assert!(!has_pending_block(&view));
        assert!(
            view.blocks
                .iter()
                .all(|block| !matches!(block, ContentBlockDto::Religious { .. }))
        );
    }

    /// Release buildda butun oqim (`get_chapter`) tasdiqlanmagan diniy blokni chiqarmaydi.
    /// Faqat `cargo test --release` da ishlaydi (SHOW_PENDING_RELIGIOUS = false).
    #[cfg(not(debug_assertions))]
    #[test]
    fn release_buildda_get_chapter_pending_blokni_chiqarmaydi() {
        let db = fresh();
        started(&db);
        let chapter = get_chapter(&db, at(1), "ch01").expect("ochiq bob");
        assert!(!has_pending_block(&chapter));
    }

    #[test]
    fn debug_rejimda_pending_diniy_blok_korinadi() {
        // Ishlab chiqish ko'rinishi: tekshiruv uchun pending blok chiqadi, lekin tasdiqlanmagan deb belgilanadi.
        let chapter = &catalog().chapters[0];
        let view = chapter_view(
            chapter,
            true,
            &BTreeMap::new(),
            &BTreeSet::new(),
            None,
            true,
        );
        assert!(view.blocks.iter().any(|block| {
            matches!(
                block,
                ContentBlockDto::Religious {
                    approved: false,
                    ..
                }
            )
        }));
    }

    #[test]
    fn haqiqiy_kontentda_yetti_bob_va_ucha_vazifa() {
        let result = catalog();
        assert!(result.errors.is_empty(), "xatolar: {:?}", result.errors);
        assert_eq!(result.chapters.len(), 7);
        assert!(result.chapters.iter().all(|c| c.weekly_tasks.len() == 3));
    }

    #[test]
    fn ikki_vazifa_bajarilsa_ikkinchi_bob_kun_sharti_bilan_ochiladi() {
        let db = fresh();
        started(&db);
        set_task_done(&db, at(2), "ch01.t1", true).expect("belgilansin");
        set_task_done(&db, at(3), "ch01.t2", true).expect("belgilansin");
        // Kun sharti 1-oktabr + 7 = 8-oktabr; vazifalar 3-da bajarildi → 8-oktabr.
        let before = list_chapters(&db, at(7)).expect("ro'yxat");
        assert!(!before[1].unlocked);
        assert_eq!(before[1].not_before.as_deref(), Some("2026-10-08"));
        let after = list_chapters(&db, at(8)).expect("ro'yxat");
        assert!(after[1].unlocked);
    }

    #[test]
    fn bajarilgan_bob_belgi_olinsa_ham_ochiq_qoladi() {
        let db = fresh();
        started(&db);
        set_task_done(&db, at(2), "ch01.t1", true).expect("belgilansin");
        set_task_done(&db, at(2), "ch01.t2", true).expect("belgilansin");
        // Belgilar 2-oktabr haftasida qo'yilgan; 3-oktabrda (shu hafta) olib tashlanadi.
        set_task_done(&db, at(3), "ch01.t1", false).expect("olinsin");
        set_task_done(&db, at(3), "ch01.t2", false).expect("olinsin");
        // Ochilish tarixi saqlanadi: 9-oktabrda ham 2-bob ochiq.
        let cards = list_chapters(&db, at(9)).expect("ro'yxat");
        assert!(cards[1].unlocked);
    }

    #[test]
    fn hodisa_joriy_bobning_vazifasini_belgilaydi() {
        let db = fresh();
        started(&db);
        record_event(&db, at(2), TaskTrigger::VaultOpened).expect("hodisa");
        let weekly = weekly_tasks(&db, at(2))
            .expect("o'qilsin")
            .expect("joriy bob");
        assert_eq!(weekly.chapter_id, "ch01");
        let first = weekly
            .tasks
            .iter()
            .find(|task| task.id == "ch01.t1")
            .expect("t1");
        assert!(first.done && first.auto_completed);
    }

    #[test]
    fn hodisa_qayta_yozilmaydi() {
        let db = fresh();
        started(&db);
        record_event(&db, at(2), TaskTrigger::VaultOpened).expect("hodisa");
        record_event(&db, at(3), TaskTrigger::VaultOpened).expect("hodisa");
        let household = finance::context(&db, at(3)).expect("kontekst").household.id;
        let week = this_week(at(3).date()).expect("hafta");
        let rows = TaskCompletionRepo::new(db.connection())
            .list_for_week(&household, week.start)
            .expect("o'qilsin");
        assert_eq!(rows.len(), 1);
    }

    #[test]
    fn daftar_sahifasi_saqlanadi_va_vazifani_belgilaydi() {
        let db = fresh();
        started(&db);
        // DAFTAR_PAGE_WRITTEN hodisasi faqat 5-bobning uchinchi vazifasida (ch05.t3); 1-bobda yo'q.
        // Shuning uchun sahifa saqlanadi, lekin joriy bobning vazifalari belgilanmaydi.
        let page = save_daftar_page(&db, at(2), "ch01", "  Birinchi qonun  ").expect("saqlansin");
        assert_eq!(page.body, "Birinchi qonun");
        let again = save_daftar_page(&db, at(3), "ch01", "Yangi matn").expect("yangilansin");
        assert_eq!(again.body, "Yangi matn");
        let weekly = weekly_tasks(&db, at(3)).expect("o'qilsin").expect("joriy");
        assert!(weekly.tasks.iter().all(|task| !task.done));
    }

    #[test]
    fn bosh_daftar_sahifasi_rad_etiladi() {
        let db = fresh();
        started(&db);
        let err = save_daftar_page(&db, at(2), "ch01", "   ").expect_err("bo'sh");
        assert!(matches!(
            err,
            SessionError::Domain(DomainError::BodyRequired)
        ));
    }

    #[test]
    fn joriy_bobdan_tashqari_vazifa_belgilanmaydi() {
        let db = fresh();
        started(&db);
        let err = set_task_done(&db, at(2), "ch02.t1", true).expect_err("joriy emas");
        assert!(matches!(
            err,
            SessionError::Domain(DomainError::TaskNotCurrent)
        ));
    }
}
