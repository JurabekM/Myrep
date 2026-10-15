//! IPC uchun ma'lumot shakllari (DTO). Pul — `minor` (satr, minor birlikda) va tayyor `formatted` matn;
//! frontend pul hisoblamaydi (DESKTOP_PROMPT.md 3.2). Sanalar — `YYYY-MM-DD` satri.

use domain::{Channel, Income, ObligationKind, ShareRule, ShareTarget, habit::HabitStats};
use money::{Locale, Money, format_money};
use serde::{Deserialize, Serialize};
use specta::Type;

/// Pul qiymati: minor birlik (satr), valyuta kodi va ko'rsatish uchun formatlangan matn.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MoneyDto {
    /// Minor birliklar soni (satr: JS sonining 2^53 chegarasidan himoya).
    pub minor: String,
    /// ISO valyuta kodi.
    pub currency: String,
    /// Ko'rsatish uchun matn (`8 000 000 soʻm`).
    pub formatted: String,
}

impl MoneyDto {
    /// Pulni DTO'ga aylantiradi.
    pub fn of(money: Money) -> Self {
        Self {
            minor: money.minor().to_string(),
            currency: money.currency().iso_code().to_owned(),
            formatted: format_money(money, Locale::Uz),
        }
    }
}

/// Kanal (DTO): naqd yoki karta.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ChannelDto {
    /// Naqd pul.
    Cash,
    /// Karta.
    Card,
}

impl From<ChannelDto> for Channel {
    fn from(value: ChannelDto) -> Self {
        match value {
            ChannelDto::Cash => Self::Cash,
            ChannelDto::Card => Self::Card,
        }
    }
}

/// Majburiyat turi (DTO).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ObligationKindDto {
    /// Ijara.
    Rent,
    /// Kredit.
    Credit,
    /// Kommunal.
    Utility,
    /// Telefon.
    Phone,
    /// Yoqilg'i.
    Fuel,
    /// Boshqa.
    Other,
}

impl From<ObligationKindDto> for ObligationKind {
    fn from(value: ObligationKindDto) -> Self {
        match value {
            ObligationKindDto::Rent => Self::Rent,
            ObligationKindDto::Credit => Self::Credit,
            ObligationKindDto::Utility => Self::Utility,
            ObligationKindDto::Phone => Self::Phone,
            ObligationKindDto::Fuel => Self::Fuel,
            ObligationKindDto::Other => Self::Other,
        }
    }
}

/// Ulush rejimi (DTO).
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize, Type)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ShareModeDto {
    /// Daromadning foizi.
    Percent,
    /// Oyiga qat'iy summa.
    Fixed,
}

/// Odat (streak) ko'rsatkichlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HabitDto {
    /// Ketma-ket ajratilgan haftalar.
    pub current_streak_weeks: u32,
    /// Jami ajratilgan haftalar.
    pub total_weeks: u32,
    /// Joriy haftada ajratish bo'lganmi.
    pub this_week_done: bool,
}

impl From<&HabitStats> for HabitDto {
    fn from(stats: &HabitStats) -> Self {
        Self {
            current_streak_weeks: stats.current_streak_weeks,
            total_weeks: stats.total_weeks,
            this_week_done: stats.this_week_done,
        }
    }
}

/// Bosh ekran.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HomeDto {
    /// «O'zingizga to'langan (shu oy)»: shu oy «Kelajagim»ga ajratilgan.
    pub paid_to_self: MoneyDto,
    /// «Kelajagim» balansi.
    pub vault_balance: MoneyDto,
    /// Shu oy daromadi.
    pub income: MoneyDto,
    /// Oy yakuni (+/−): daromad − (xarajat + yozilmagan majburiyat + sof jamg'arma).
    pub month_result: MoneyDto,
    /// Odat ko'rsatkichlari.
    pub habit: HabitDto,
    /// O'tgan oy auditi holati.
    pub audit: AuditStatusDto,
}

/// Audit holati: o'tkazilganmi va qaysi davr.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AuditStatusDto {
    /// Audit yakunlanganmi.
    pub done: bool,
    /// Davr boshi (kiradi).
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
}

/// Daromad yozuvi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeDto {
    /// Identifikator.
    pub id: String,
    /// Manba.
    pub source: String,
    /// Kanal.
    pub channel: ChannelDto,
    /// Summa.
    pub amount: MoneyDto,
    /// Sana.
    pub occurred_on: String,
    /// Izoh.
    pub note: Option<String>,
}

impl IncomeDto {
    /// Daromadni DTO'ga aylantiradi.
    pub fn of(income: &Income) -> Self {
        Self {
            id: income.id.clone(),
            source: income.source.clone(),
            channel: match income.channel {
                Channel::Cash => ChannelDto::Cash,
                Channel::Card => ChannelDto::Card,
            },
            amount: MoneyDto::of(income.amount),
            occurred_on: crate::finance::date_text(income.occurred_on),
            note: income.note.clone(),
        }
    }
}

/// Daromad kiritilgandan keyingi natija: yozuv va ulush taklifi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeOutcomeDto {
    /// Saqlangan daromad.
    pub income: IncomeDto,
    /// «Shundan X so'm — kelajagingiz uchun». `null` — taklif yo'q.
    pub share_suggestion: Option<MoneyDto>,
}

/// Daromad kiritish ma'lumoti (forma).
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct IncomeInputDto {
    /// Summa matni (masalan, `150 000`).
    pub amount: String,
    /// Manba.
    pub source: String,
    /// Kanal.
    pub channel: ChannelDto,
    /// Izoh.
    pub note: Option<String>,
}

/// «Kelajagim» yozuvi (tarix).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct VaultEntryDto {
    /// Identifikator.
    pub id: String,
    /// Tur: `INITIAL`, `INCOME_SHARE` yoki `WITHDRAWAL`.
    pub kind: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Sana.
    pub occurred_on: String,
    /// Pul olish sababi (faqat `WITHDRAWAL`).
    pub reason: Option<String>,
    /// Manba daromad (faqat `INCOME_SHARE`).
    pub income_id: Option<String>,
}

/// Ulush qoidasi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ShareRuleDto {
    /// Rejim.
    pub mode: ShareModeDto,
    /// Foiz (bp), faqat `PERCENT` rejimida.
    pub basis_points: Option<u32>,
    /// Oylik summa, faqat `FIXED` rejimida.
    pub fixed_amount: Option<MoneyDto>,
    /// Progressiv rejim.
    pub progressive: bool,
}

impl ShareRuleDto {
    /// Qoidani DTO'ga aylantiradi.
    pub fn of(rule: &ShareRule) -> Self {
        match rule.target {
            ShareTarget::Percent(bp) => Self {
                mode: ShareModeDto::Percent,
                basis_points: u32::try_from(bp).ok(),
                fixed_amount: None,
                progressive: rule.progressive,
            },
            ShareTarget::Fixed(amount) => Self {
                mode: ShareModeDto::Fixed,
                basis_points: None,
                fixed_amount: Some(MoneyDto::of(amount)),
                progressive: rule.progressive,
            },
        }
    }
}

/// «Kelajagim» ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct VaultDto {
    /// Balans.
    pub balance: MoneyDto,
    /// Shu oy ajratilgan summa.
    pub saved_this_month: MoneyDto,
    /// Boshlang'ich balans kiritilganmi.
    pub has_initial: bool,
    /// Ulush qoidasi.
    pub rule: ShareRuleDto,
    /// Odat.
    pub habit: HabitDto,
    /// Progressiv taklif: yangi ulush (bp). `null` — taklif yo'q.
    pub progression_offer_bp: Option<u32>,
    /// Oxirgi yozuvlar, eng yangisi birinchi.
    pub history: Vec<VaultEntryDto>,
}

/// Qoida kiritish ma'lumoti.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ShareRuleInputDto {
    /// Rejim.
    pub mode: ShareModeDto,
    /// Foiz (bp), `PERCENT` uchun.
    pub basis_points: Option<u32>,
    /// Oylik summa matni, `FIXED` uchun.
    pub fixed_amount: Option<String>,
    /// Progressiv rejim.
    pub progressive: bool,
}

/// Majburiyat va audit qatori.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationLineDto {
    /// Nomi.
    pub title: String,
    /// Tur kodi.
    pub kind: String,
    /// Oylik summa.
    pub amount: MoneyDto,
    /// Kategoriyada yozilgan qism.
    pub recorded: MoneyDto,
    /// Yozilmagan qism.
    pub remainder: MoneyDto,
}

/// Kategoriya bo'yicha shu oy xarajatlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CategorySpentDto {
    /// Kategoriya identifikatori; `null` — kategoriyasiz.
    pub category_id: Option<String>,
    /// Nomi; `null` — kategoriyasiz.
    pub name: Option<String>,
    /// Tizim kaliti (standart kategoriya bo'lsa).
    pub system_key: Option<String>,
    /// Summa.
    pub amount: MoneyDto,
}

/// Kategoriya.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct CategoryDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Tizim kaliti (standart bo'lsa).
    pub system_key: Option<String>,
    /// Toifa kodi: `ZARUR | KERAK | HAVAS`.
    pub necessity: String,
}

/// Oylik audit ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AuditDto {
    /// Davr boshi.
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
    /// Audit yakunlanganmi.
    pub done: bool,
    /// Daromad.
    pub income: MoneyDto,
    /// Yozilgan xarajatlar.
    pub expenses: MoneyDto,
    /// Majburiyatlar jami.
    pub obligations_total: MoneyDto,
    /// Yozilmagan majburiyatlar.
    pub obligations_unrecorded: MoneyDto,
    /// Sof jamg'arma.
    pub net_savings: MoneyDto,
    /// Izohsiz qolgan summa.
    pub unexplained: MoneyDto,
    /// Majburiyatlar qatorlari.
    pub lines: Vec<ObligationLineDto>,
    /// Kategoriyalar bo'yicha xarajatlar.
    pub spent: Vec<CategorySpentDto>,
    /// Xarajat kiritish uchun kategoriyalar.
    pub categories: Vec<CategoryDto>,
}

/// «Kimning puli?» bo'lagi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct OwnerPartDto {
    /// Egasi kodi (`LANDLORD`, `BANK`, `SHOP`, `UTILITIES`, `FUEL`, `SELF`, `SADAQA`, `OTHER`, `UNEXPLAINED`).
    pub owner: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Jamdagi ulushi, basis points (1 % = 100 bp). Frontend shu qiymat bo'yicha bo'lak kengligini chizadi.
    pub share_bp: u32,
}

/// «Kimning puli?» ekrani.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WhoseMoneyDto {
    /// Davr boshi.
    pub period_start: String,
    /// Davr oxiri (kirmaydi).
    pub period_end: String,
    /// Jami (barcha bo'laklar yig'indisi).
    pub total: MoneyDto,
    /// Egalar bo'yicha bo'laklar (faqat musbat).
    pub parts: Vec<OwnerPartDto>,
}

/// Majburiyat.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub title: String,
    /// Tur kodi.
    pub kind: String,
    /// Oylik summa.
    pub amount: MoneyDto,
    /// To'lov kuni.
    pub due_day: Option<u8>,
    /// Faolmi.
    pub active: bool,
}

/// Majburiyat kiritish ma'lumoti.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ObligationInputDto {
    /// Nomi.
    pub title: String,
    /// Turi.
    pub kind: ObligationKindDto,
    /// Oylik summa matni.
    pub amount: String,
    /// To'lov kuni (1..31).
    pub due_day: Option<u8>,
}

/// Nasiya.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct DebtDto {
    /// Identifikator.
    pub id: String,
    /// Kimga qarzdor (do'kon).
    pub creditor: String,
    /// Asl summa.
    pub principal: MoneyDto,
    /// Qoldiq.
    pub outstanding: MoneyDto,
    /// Olingan sana.
    pub incurred_on: String,
    /// Izoh.
    pub note: Option<String>,
}

/// Ko'p tilli matn: ikkala til ham doim to'ldirilgan (ruscha yo'q bo'lsa o'zbekcha nusxa).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LocalizedDto {
    /// O'zbekcha (asosiy).
    pub uz: String,
    /// Ruscha (yo'q bo'lsa — o'zbekcha).
    pub ru: String,
}

/// Bob qonuni (sarlavha va matn).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct LawDto {
    /// Qonun raqami.
    pub number: u32,
    /// Qonun matni.
    pub text: LocalizedDto,
}

/// Bob bloki. Diniy blok release'da faqat tasdiqlangan holda keladi (`approved` har doim `true`).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(tag = "type", rename_all = "camelCase")]
pub enum ContentBlockDto {
    /// Oddiy abzats.
    Paragraph {
        /// Matn.
        text: LocalizedDto,
    },
    /// Iqtibos.
    Quote {
        /// Matn.
        text: LocalizedDto,
    },
    /// Oyat yoki hadis. `approved` `false` faqat ishlab chiqish (debug) rejimida chiqadi.
    Religious {
        /// Matn.
        text: LocalizedDto,
        /// Manba.
        source: LocalizedDto,
        /// Ulamo tasdiqlaganmi.
        approved: bool,
    },
}

/// Haftalik vazifa.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TaskDto {
    /// Vazifa ID (`ch01.t1`).
    pub id: String,
    /// Vazifa matni.
    pub text: LocalizedDto,
    /// Ilova avtomatik belgilaydi (ko'rsatma uchun).
    pub auto_completed: bool,
    /// Bajarilganmi.
    pub done: bool,
}

/// Bob kartochkasi (ro'yxat uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ChapterCardDto {
    /// Bob ID.
    pub id: String,
    /// Tartib raqami (1..5).
    pub order: u32,
    /// Sarlavha.
    pub title: LocalizedDto,
    /// Hozir ochiqmi.
    pub unlocked: bool,
    /// Ochilish sanasi (`YYYY-MM-DD`), aniq bo'lsa.
    pub unlock_date: Option<String>,
    /// Oldingi bobdan yana nechta vazifa kerak (yopiq bob uchun).
    pub tasks_remaining: u32,
    /// Kun sharti bo'yicha eng erta sana (aniq bo'lsa).
    pub not_before: Option<String>,
}

/// «Daftar sahifasi»: foydalanuvchining o'z so'zlari.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct DaftarPageDto {
    /// Bob ID.
    pub chapter_id: String,
    /// Qonun raqami.
    pub law_number: u32,
    /// Matn.
    pub body: String,
    /// Oxirgi yangilanish sanasi (Toshkent, `YYYY-MM-DD`).
    pub updated_on: String,
}

/// Bob sahifasi (ochiq bob uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ChapterDto {
    /// Bob ID.
    pub id: String,
    /// Tartib raqami.
    pub order: u32,
    /// Sarlavha.
    pub title: LocalizedDto,
    /// Bloklar (diniy bloklar release'da tasdiqlangani bilan).
    pub blocks: Vec<ContentBlockDto>,
    /// Qonun.
    pub law: LawDto,
    /// Haftalik vazifalar. Joriy bob uchun — shu haftaniki; boshqa bob uchun — bir marta bajarilgan bo'lsa `done`.
    pub weekly_tasks: Vec<TaskDto>,
    /// Hozirgi (eng so'nggi ochilgan) bob mi — vazifalarni shu hafta belgilash mumkin.
    pub is_current: bool,
    /// Audio (https), bo'lsa.
    pub audio_url: Option<String>,
    /// «Daftar sahifasi», yozilgan bo'lsa.
    pub daftar_page: Option<DaftarPageDto>,
}

/// Joriy bobning shu haftalik vazifalari (bosh sahifa va bob sahifasi uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WeeklyTasksDto {
    /// Joriy bob ID.
    pub chapter_id: String,
    /// Joriy bob sarlavhasi.
    pub chapter_title: LocalizedDto,
    /// Hafta boshi (juma, `YYYY-MM-DD`).
    pub week_start: String,
    /// Vazifalar.
    pub tasks: Vec<TaskDto>,
}

/// Xarajat yozuvi (ro'yxat va qo'shish natijasi).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ExpenseDto {
    /// Identifikator.
    pub id: String,
    /// Sana (`YYYY-MM-DD`, Toshkent).
    pub occurred_on: String,
    /// Summa.
    pub amount: MoneyDto,
    /// Kategoriya nomi (bo'lsa).
    pub category_name: Option<String>,
    /// Toifa kodi: `ZARUR | KERAK | HAVAS`.
    pub necessity: String,
    /// Izoh.
    pub note: Option<String>,
    /// Sovg'a: havas hisobiga kirmaydi.
    pub is_gift: bool,
    /// Obro' xarajati.
    pub is_ostentation: bool,
    /// Qarz bilan qilingan (qizil bayroq).
    pub funded_by_debt: bool,
}

/// Xarajat qo'shish formasi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct ExpenseInputDto {
    /// Sana (`YYYY-MM-DD`, shu hafta ichida). Yo'q bo'lsa — bugun.
    pub occurred_on: Option<String>,
    /// Summa matni (masalan, `150 000`).
    pub amount: String,
    /// Kategoriya (bo'lsa). Toifa kategoriyadan olinadi.
    pub category_id: Option<String>,
    /// Izoh.
    pub note: Option<String>,
    /// Sovg'a.
    pub is_gift: bool,
    /// Obro' xarajati.
    pub is_ostentation: bool,
    /// Qarz bilan qilingan.
    pub funded_by_debt: bool,
}

/// Oylik xulosa: uch toifa va belgilar bo'yicha jamlanma.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MonthSummaryDto {
    /// Joriy hafta boshi (juma, `YYYY-MM-DD`) — hafta varag'i uchun.
    pub week_start: String,
    /// Bugun (Toshkent, `YYYY-MM-DD`).
    pub today: String,
    /// Davr boshi (`YYYY-MM-DD`).
    pub period_start: String,
    /// Davr oxiri (kirmaydi, `YYYY-MM-DD`).
    pub period_end: String,
    /// `ZARUR` toifadagi xarajatlar.
    pub zarur: MoneyDto,
    /// `KERAK` toifadagi xarajatlar.
    pub kerak: MoneyDto,
    /// Havas hisobi: `HAVAS`, sovg'a va sadaqa bo'lmagan xarajatlar.
    pub havas: MoneyDto,
    /// Sadaqa (havas hisobiga kirmaydi).
    pub sadaqa: MoneyDto,
    /// Sovg'alar (havas hisobiga kirmaydi).
    pub gifts: MoneyDto,
    /// Obro' xarajatlari (isrof tahlilida alohida).
    pub ostentation: MoneyDto,
    /// Qarz bilan qilingan xarajatlar (qizil bayroq).
    pub funded_by_debt: MoneyDto,
}

/// Kattaning havas chegarasiga roziligi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct AdultConsentDto {
    /// A'zo identifikatori.
    pub member_id: String,
    /// Ismi.
    pub name: String,
    /// Rozilik bergan mi.
    pub consented: bool,
    /// PIN o'rnatilganmi (rozilik uchun kerak).
    pub has_pin: bool,
}

/// Havas chegarasi holati (ekran uchun).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct HavasLimitDto {
    /// Oylik chegara (o'rnatilmagan bo'lsa — `null`).
    pub limit: Option<MoneyDto>,
    /// Shu oy havas sarfi.
    pub spent: MoneyDto,
    /// Daraja: `OK | WARNING | REACHED` (faqat faol chegarada yumshoq ogohlantirish).
    pub level: String,
    /// Chegara faolmi: barcha kattalar rozi bo'lgan.
    pub active: bool,
    /// Kattalar va ularning roziligi.
    pub adults: Vec<AdultConsentDto>,
}

/// Oila a'zosi.
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MemberDto {
    /// Identifikator.
    pub id: String,
    /// Ismi.
    pub name: String,
    /// Rol: `ADULT | CHILD`.
    pub role: String,
    /// PIN o'rnatilganmi.
    pub has_pin: bool,
}

/// Oila a'zosini qo'shish formasi. Kattaga PIN majburiy.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct MemberInputDto {
    /// Ismi.
    pub name: String,
    /// Rol: `ADULT | CHILD`.
    pub role: String,
    /// PIN (6 raqam). Faqat kattalar uchun.
    pub pin: Option<String>,
}

/// Juma shirinligi (rejalashtirilgan ritual).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TreatDto {
    /// Identifikator.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Odatiy summa.
    pub amount: MoneyDto,
    /// Hafta kuni: 0 dushanba … 6 yakshanba.
    pub weekday: u8,
    /// Bugun ritual kunimi.
    pub due_today: bool,
}

/// Juma shirinligini qo'shish formasi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct TreatInputDto {
    /// Nomi.
    pub name: String,
    /// Summa matni.
    pub amount: String,
    /// Hafta kuni: 0 dushanba … 6 yakshanba.
    pub weekday: u8,
}

/// Odat statistikasi: oyiga va yiliga jami (ayblov yo'q — SPEC 2B.9).
#[derive(Debug, Clone, PartialEq, Eq, Serialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct OdatHabitDto {
    /// Kategoriya identifikatori.
    pub id: String,
    /// Nomi.
    pub name: String,
    /// Joriy oy jami.
    pub monthly: MoneyDto,
    /// Joriy yil jami.
    pub yearly: MoneyDto,
    /// Yil ichidagi yozuvlar soni.
    pub entries_this_year: u32,
}

/// Pul olish ma'lumoti (forma). PIN alohida argument sifatida keladi.
#[derive(Debug, Clone, PartialEq, Eq, Deserialize, Type)]
#[serde(rename_all = "camelCase")]
pub struct WithdrawInputDto {
    /// Summa matni.
    pub amount: String,
    /// Sabab (majburiy).
    pub reason: String,
}

#[cfg(test)]
mod tests {
    use super::*;
    use money::Currency;

    #[test]
    fn pul_dto_minor_satr_va_formatlangan_matn() {
        let dto = MoneyDto::of(Money::new(800_000_000, Currency::Uzs));
        assert_eq!(dto.minor, "800000000");
        assert_eq!(dto.currency, "UZS");
        assert!(dto.formatted.contains("8"), "{}", dto.formatted);
    }

    #[test]
    fn ulush_qoidasi_dto_shakli() {
        let percent = ShareRuleDto::of(&ShareRule::default_rule());
        assert_eq!(percent.mode, ShareModeDto::Percent);
        assert_eq!(percent.basis_points, Some(500));
        assert_eq!(percent.fixed_amount, None);
    }
}
