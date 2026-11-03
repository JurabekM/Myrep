package uz.havoradar.engine.model

import java.time.Instant
import java.time.LocalDate
import java.time.LocalDateTime

/** Ma'lumot manbasi (ikkalasi ham Open-Meteo orqali, API kaliti kerak emas). */
enum class SourceId(
    val title: String,
    val homepage: String,
) {
    WEATHER(
        "Open-Meteo — ob-havo prognozi (milliy meteorologiya xizmatlari modellari)",
        "https://open-meteo.com/en/docs",
    ),
    AIR(
        "Open-Meteo — havo sifati (Copernicus CAMS modeli)",
        "https://open-meteo.com/en/docs/air-quality-api",
    ),
}

/** Xavf darajasi — EpiRadar bilan bir xil 5 bosqich (ranglar ham bir xil). */
enum class RiskLevel(
    val minScore: Int,
    val uz: String,
    val advice: String,
) {
    CALM(0, "Xavfsiz", "Alohida choralar shart emas."),
    WATCH(20, "Kuzatuv", "Sezgir guruhlar ehtiyot bo'lsin, prognozni kuzatib boring."),
    ADVISORY(40, "Ehtiyot", "Ochiq havoda uzoq va og'ir jismoniy ishni kamaytiring; sezgir guruhlar alohida ehtiyot bo'lsin."),
    WARNING(60, "Xavfli", "Sog'liq uchun jiddiy xavf: eng og'ir soatlarda tashqarida bo'lmang, yaqinlaringiz holatidan xabar oling."),
    EMERGENCY(80, "Favqulodda", "Hayot uchun xavfli sharoit: barcha ehtiyot choralarini ko'ring, zaif yaqinlaringizni yolg'iz qoldirmang."),
    ;

    companion object {
        fun of(score: Int): RiskLevel = entries.last { score >= it.minScore }

        fun parse(name: String?): RiskLevel? = entries.firstOrNull { it.name == name }
    }
}

enum class Hazard(
    val uz: String,
) {
    HEAT("Issiqlik"),
    AIR("Havo sifati"),
}

/**
 * Sezgir guruhlar (JSST, CDC, AQSh EPA ro'yxatlari asosida). `heat`/`air` — shu xavfga sezgirlik.
 * Profil faqat qurilmada saqlanadi.
 */
enum class Vulnerability(
    val uz: String,
    val heat: Boolean,
    val air: Boolean,
) {
    ELDERLY("65 yoshdan kattalar", true, true),
    CHILD("Yosh bolalar", true, true),
    PREGNANT("Homiladorlik", true, true),
    HEART("Yurak-qon tomir kasalligi yoki gipertoniya", true, true),
    LUNG("Astma yoki surunkali o'pka kasalligi", true, true),
    DIABETES("Qandli diabet", true, false),
    OUTDOOR("Ochiq havoda ishlash yoki sport", true, true),
}

/** JSST quyosh UV indeksi toifalari. */
enum class UvCategory(
    val min: Double,
    val uz: String,
    val advice: String,
) {
    LOW(0.0, "Past", "Himoya shart emas."),
    MODERATE(3.0, "O'rtacha", "Himoya kerak: tushlik paytida soyada turing, bosh kiyim va quyosh ko'zoynagi taqing, quyoshdan himoya kremi surting."),
    HIGH(6.0, "Yuqori", "Himoya kerak: tushlik paytida soyada turing, yopiq kiyim, bosh kiyim, ko'zoynak va quyoshdan himoya kremi."),
    VERY_HIGH(8.0, "Juda yuqori", "Qo'shimcha himoya: tushlik soatlarida tashqarida bo'lmang; soya, kiyim, bosh kiyim va krem majburiy."),
    EXTREME(11.0, "Haddan tashqari", "Qo'shimcha himoya: tushlik soatlarida tashqarida bo'lmang; soya, kiyim, bosh kiyim va krem majburiy."),
    ;

    companion object {
        fun of(uv: Double): UvCategory = entries.last { uv >= it.min }
    }
}

data class Place(
    val id: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    /** O'zbekistondan tashqarida (qarindoshlar, ish, ziyorat). */
    val abroad: Boolean,
)

/** Soatlik ob-havo qatori (joyning mahalliy vaqtida, Open-Meteo `timezone=auto`). */
data class WeatherSeries(
    val placeId: String,
    val fetchedAt: Instant,
    val utcOffsetSeconds: Int,
    val times: List<LocalDateTime>,
    val temp: List<Double?>,
    val humidity: List<Double?>,
    val uv: List<Double?>,
)

/** Soatlik havo sifati qatori, µg/m³. */
data class AirSeries(
    val placeId: String,
    val fetchedAt: Instant,
    val utcOffsetSeconds: Int,
    val times: List<LocalDateTime>,
    val pm25: List<Double?>,
    val pm10: List<Double?>,
    val ozone: List<Double?>,
    val no2: List<Double?>,
    val dust: List<Double?>,
)

data class SourceStatus(
    val source: SourceId,
    val ok: Boolean,
    val fetchedAt: Instant,
    val error: String?,
    /** Manba ishlamadi — oldingi muvaffaqiyatli prognoz ishlatildi. */
    val stale: Boolean,
)

/** Saqlanadigan xom holat: baholar har safar shundan qayta hisoblanadi (profil o'zgarsa ham tarmoqsiz). */
data class StoredState(
    val generatedAt: Instant,
    val weather: List<WeatherSeries>,
    val air: List<AirSeries>,
    val sources: List<SourceStatus>,
)

/** Bitta xavf bo'yicha baho: `base` — umumiy aholi uchun, `personal` — profilingiz bilan. */
data class HazardAssessment(
    val hazard: Hazard,
    val baseScore: Int,
    val personalScore: Int,
    val reasons: List<String>,
    val advice: List<String>,
) {
    val baseLevel: RiskLevel get() = RiskLevel.of(baseScore)
    val personalLevel: RiskLevel get() = RiskLevel.of(personalScore)
}

/** Kunlik havo sifati ko'rsatkichlari (µg/m³). */
data class AirDay(
    val pm25Mean: Double?,
    val pm10Mean: Double?,
    val ozoneMax8h: Double?,
    val no2Mean: Double?,
    val no2Max: Double?,
    /** Chang ulushi PM10 da (0..1). */
    val dustShare: Double?,
    /** Eng ifloslangan soat (PM2.5 bo'yicha). */
    val worstHour: Int?,
)

data class DayReport(
    val date: LocalDate,
    val tempMax: Double?,
    val tempMin: Double?,
    /** Issiqlik ko'rsatkichi (NWS issiqlik indeksi va havo haroratining kattasi), °C. */
    val feelsMax: Double?,
    val feelsPeakHour: Int?,
    val uvMax: Double?,
    val air: AirDay?,
    val heatRisk: HazardAssessment?,
    val airRisk: HazardAssessment?,
) {
    val personalScore: Int? get() = listOfNotNull(heatRisk?.personalScore, airRisk?.personalScore).maxOrNull()
    val baseScore: Int? get() = listOfNotNull(heatRisk?.baseScore, airRisk?.baseScore).maxOrNull()

    fun risk(h: Hazard): HazardAssessment? = if (h == Hazard.HEAT) heatRisk else airRisk
}

data class HourPoint(
    val time: LocalDateTime,
    val temp: Double?,
    val feels: Double?,
    val humidity: Double?,
    val uv: Double?,
    val pm25: Double?,
    val pm10: Double?,
)

data class PlaceReport(
    val place: Place,
    val localNow: LocalDateTime,
    val current: HourPoint?,
    val days: List<DayReport>,
    /** Hozirdan boshlab 48 soat (grafik uchun). */
    val hours: List<HourPoint>,
    val weatherFetchedAt: Instant?,
    val airFetchedAt: Instant?,
) {
    val today: DayReport? get() = days.firstOrNull { it.date == localNow.toLocalDate() }
}

data class Snapshot(
    val generatedAt: Instant,
    val profile: Set<Vulnerability>,
    /** Birinchisi — asosiy joy. */
    val places: List<PlaceReport>,
    val sources: List<SourceStatus>,
) {
    val main: PlaceReport? get() = places.firstOrNull()
}

data class Settings(
    val placeId: String = "tashkent",
    /** Qo'shimcha joylar (ota-ona, qarindoshlar, safar), ko'pi bilan [MAX_EXTRA_PLACES]. */
    val extraPlaces: List<String> = emptyList(),
    val profile: Set<Vulnerability> = emptySet(),
    val notificationsEnabled: Boolean = true,
    /** Standart — «Xavfli»: O'zbekiston yozida «Ehtiyot» darajasi deyarli har kuni bo'ladi. */
    val alertThreshold: RiskLevel = RiskLevel.WARNING,
    val syncHours: Int = 3,
    /** 22:00–07:00 oralig'ida faqat «Favqulodda» xabar beriladi, qolganlari ertalabga qoldiriladi. */
    val quietHours: Boolean = true,
    val onboardingDone: Boolean = false,
    /** Standart — dark; light mavzu ixtiyoriy (Myrep UI qoidasi). */
    val lightTheme: Boolean = false,
) {
    val allPlaces: List<String> get() = (listOf(placeId) + extraPlaces).distinct()

    companion object {
        val SYNC_CHOICES = listOf(1, 3, 6, 12)
        const val MAX_EXTRA_PLACES = 3
    }
}
