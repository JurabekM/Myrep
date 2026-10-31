package uz.epiradar.engine.model

import java.time.Instant

/** Ma'lumot manbasi. `reliability` — manba ishonchliligi (0..1), xavf bahosida og'irlik sifatida. */
enum class SourceId(
    val title: String,
    val reliability: Double,
    val homepage: String,
) {
    WHO_DON(
        "JSST — Kasallik avj olishi xabarlari (DON)",
        1.0,
        "https://www.who.int/emergencies/disease-outbreak-news",
    ),
    ECDC(
        "ECDC — Epidemiologik yangilanishlar",
        0.95,
        "https://www.ecdc.europa.eu/en/threats-and-outbreaks",
    ),
    CDC_TRAVEL(
        "CDC — Sayohat salomatligi ogohlantirishlari",
        0.9,
        "https://wwwnc.cdc.gov/travel/notices",
    ),
    WHO_FLUNET(
        "JSST FluNet — gripp laboratoriya kuzatuvi",
        1.0,
        "https://www.who.int/tools/flunet",
    ),
}

/**
 * Matndan aniqlanadigan epidemiologik belgi. `weight` — xavf bahosiga qo'shimcha (0..1).
 * Kalit iboralar [uz.epiradar.engine.text.SignalClassifier] da.
 */
enum class SignalFlag(
    val uz: String,
    val weight: Double,
) {
    PHEIC("JSST xalqaro ahamiyatdagi favqulodda holat e'lon qilgan", 0.35),
    UNKNOWN_ETIOLOGY("Sababi noma'lum kasallik", 0.25),
    NOVEL_PATHOGEN("Yangi qo'zg'atuvchi yoki yangi shtamm", 0.25),
    HUMAN_TO_HUMAN("Odamdan odamga yuqish qayd etilgan", 0.15),
    MULTI_COUNTRY("Bir nechta mamlakatga tarqalgan", 0.12),
    IMPORTED("Boshqa mamlakatga olib kirilgan holatlar", 0.10),
    HEALTHCARE_WORKERS("Tibbiyot xodimlari orasida yuqish", 0.10),
    ESCALATING("Tarqalish kengaymoqda", 0.10),
    FIRST_DETECTION("Mamlakatda birinchi marta aniqlangan", 0.08),
    CLUSTER("Kasallanish o'chog'i (klaster)", 0.06),
    DEATHS("O'lim holatlari qayd etilgan", 0.05),
}

/** Bitta manbadan kelgan bitta xabar. */
data class Signal(
    val id: String,
    val source: SourceId,
    val title: String,
    val summary: String,
    val url: String,
    val publishedAt: Instant,
    val countries: List<String>,
    val diseaseId: String,
    val flags: Set<SignalFlag>,
    /** CDC sayohat darajasi (1..4) yoki null. */
    val travelLevel: Int? = null,
)

/** Xavf darajasi — Google zilzila ogohlantirishidagi kabi aniq, tushunarli bosqichlar. */
enum class ThreatLevel(
    val minScore: Int,
    val uz: String,
    val advice: String,
) {
    CALM(0, "Tinch", "Hozircha alohida choralar shart emas. Umumiy gigiyenaga rioya qiling."),
    WATCH(20, "Kuzatuv", "Vaziyatni kuzatib boring. Rasmiy manbalardagi yangilanishlarni o'qing."),
    ADVISORY(
        40,
        "Ogohlik",
        "Ehtiyot choralarini kuchaytiring: qo'l gigiyenasi, emlash holatini tekshiring, safar rejalarini qayta ko'ring.",
    ),
    WARNING(
        60,
        "Xavf",
        "Jiddiy xavf. Rasmiy tavsiyalarga qat'iy amal qiling, gavjum joylardan qoching, alomat bo'lsa shifokorga murojaat qiling.",
    ),
    EMERGENCY(
        80,
        "Favqulodda",
        "Favqulodda vaziyat. Faqat rasmiy ko'rsatmalarga amal qiling, tayyorgarlik ro'yxatini bajaring.",
    ),
    ;

    companion object {
        fun of(score: Int): ThreatLevel = entries.last { score >= it.minScore }

        fun parse(name: String?): ThreatLevel? = entries.firstOrNull { it.name == name }
    }
}

data class Assessment(
    /** Joylashuvdan qat'i nazar (pandemiya salohiyati) 0..100. */
    val globalScore: Int,
    /** Foydalanuvchi mamlakati uchun 0..100. */
    val personalScore: Int,
    /** Foydalanuvchi mamlakatiga eng yaqin o'choqgacha masofa (km) yoki null. */
    val distanceKm: Int?,
    val reasons: List<String>,
) {
    val globalLevel: ThreatLevel get() = ThreatLevel.of(globalScore)
    val personalLevel: ThreatLevel get() = ThreatLevel.of(personalScore)
}

/** Bir kasallik bo'yicha bir-biriga bog'liq xabarlar to'plami (avj olish hodisasi). */
data class OutbreakEvent(
    val id: String,
    val diseaseId: String,
    val title: String,
    val countries: List<String>,
    val signals: List<Signal>,
    val firstSeen: Instant,
    val lastUpdated: Instant,
    val flags: Set<SignalFlag>,
    val travelLevel: Int?,
    val assessment: Assessment,
)

data class TrendPoint(
    val weekStart: String,
    val value: Double,
    val tested: Int,
)

data class Anomaly(
    val weekStart: String,
    val value: Double,
    val expected: Double,
    val threshold: Double,
    val method: String,
)

enum class TrendStatus(
    val uz: String,
) {
    NORMAL("Me'yorda"),
    RISING("O'sish kuzatilmoqda"),
    UNUSUAL("Mavsum me'yoridan yuqori"),
    NO_DATA("Ma'lumot yetarli emas"),
}

data class TrendSeries(
    val id: String,
    val country: String,
    val title: String,
    val unit: String,
    val points: List<TrendPoint>,
    val anomalies: List<Anomaly>,
    val status: TrendStatus,
    /** Oxirgi haftalarda inson organizmida A(H5)/A(H7N9) qush grippi topilgan haftalar. */
    val novelFluWeeks: List<String>,
    val note: String,
)

data class SourceStatus(
    val source: SourceId,
    val ok: Boolean,
    val itemCount: Int,
    val fetchedAt: Instant,
    val error: String?,
    /** Manba ishlamadi — oldingi muvaffaqiyatli ma'lumot ishlatildi. */
    val stale: Boolean,
)

data class Snapshot(
    val generatedAt: Instant,
    val country: String,
    val globalScore: Int,
    val personalScore: Int,
    val signals: List<Signal>,
    val events: List<OutbreakEvent>,
    val trends: List<TrendSeries>,
    val trendsFetchedAt: Instant?,
    val sources: List<SourceStatus>,
) {
    val globalLevel: ThreatLevel get() = ThreatLevel.of(globalScore)
    val personalLevel: ThreatLevel get() = ThreatLevel.of(personalScore)
}

data class Settings(
    val country: String = "UZB",
    val notificationsEnabled: Boolean = true,
    val alertThreshold: ThreatLevel = ThreatLevel.ADVISORY,
    val syncHours: Int = 3,
    /** Kuzatuv ro'yxati (sayohat yo'nalishlari, qarindoshlar yashaydigan mamlakatlar). */
    val watchCountries: List<String> = emptyList(),
    val checklistDone: List<String> = emptyList(),
    val onboardingDone: Boolean = false,
    /** Standart — dark; light mavzu ixtiyoriy (Myrep UI qoidasi). */
    val lightTheme: Boolean = false,
) {
    companion object {
        val SYNC_CHOICES = listOf(1, 3, 6, 12, 24)
    }
}
