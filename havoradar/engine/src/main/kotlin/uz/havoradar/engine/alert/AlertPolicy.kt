package uz.havoradar.engine.alert

import uz.havoradar.engine.model.DayReport
import uz.havoradar.engine.model.Hazard
import uz.havoradar.engine.model.PlaceReport
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Snapshot
import java.time.LocalDate
import java.time.LocalTime
import kotlin.math.roundToInt

data class AlertNotification(
    /** Bildirishnoma bosilganda ochiladigan joy. */
    val placeId: String,
    val key: String,
    val title: String,
    val body: String,
    val level: RiskLevel,
    /** Yuqori ustuvorlikdagi kanal (Xavfli va Favqulodda). */
    val critical: Boolean,
)

/**
 * Qaysi xavf haqida push yuborishni hal qiladi. Kalit — `joy|xavf|sana`.
 * - Faqat bugun va ertaga (oldindan ogohlantirish), daraja chegaradan past emas.
 * - Bir to'lqin — bir xabar: oldingi kun shu darajada xabar qilingan bo'lsa, davomi jim belgilanadi;
 *   faqat daraja oshsa yana xabar beriladi.
 * - Sokin soatlarda (22:00–07:00) faqat «Favqulodda»; qolganlari belgilanmaydi va ertalab yuboriladi.
 * - Birinchi ishga tushishda faqat «Favqulodda» (qolgani ilovaning o'zida ko'rinib turibdi).
 * - Bir sinxronlashda ko'pi bilan [MAX_PER_SYNC] ta + jamlovchi xabar.
 */
class AlertPolicy {
    data class Decision(
        val notifications: List<AlertNotification>,
        val notified: Map<String, RiskLevel>,
    )

    private data class Due(
        val report: PlaceReport,
        val day: DayReport,
        val hazard: Hazard,
        val level: RiskLevel,
        val escalated: Boolean,
        val score: Int,
    )

    fun decide(
        snapshot: Snapshot,
        settings: Settings,
        previouslyNotified: Map<String, RiskLevel>,
        firstRun: Boolean,
        localTime: LocalTime,
    ): Decision {
        val notified = previouslyNotified.toMutableMap()
        val quiet = settings.quietHours && (localTime >= QUIET_START || localTime < QUIET_END)
        val due = mutableListOf<Due>()
        // Ro'yxatdan olib tashlangan joylarning kalitlari ham tozalanadi.
        notified.keys.removeIf { k -> snapshot.places.none { k.startsWith("${it.place.id}|") } }

        for (report in snapshot.places) {
            val today = report.localNow.toLocalDate()
            // Eski kalitlar tozalanadi (kechagisi «to'lqin davomi»ni aniqlash uchun qoladi).
            notified.keys.removeIf { it.startsWith("${report.place.id}|") && parseDate(it)?.isBefore(today.minusDays(1)) != false }
            for (day in report.days.filter { !it.date.isAfter(today.plusDays(HORIZON_DAYS)) }) {
                for (hazard in Hazard.entries) {
                    val risk = day.risk(hazard) ?: continue
                    val level = risk.personalLevel
                    if (level < settings.alertThreshold) continue
                    val k = key(report.place.id, hazard, day.date)
                    val before = notified[k]
                    val yesterday = notified[key(report.place.id, hazard, day.date.minusDays(1))]
                    val escalated = before != null && level > before
                    val isNew = before == null && (yesterday == null || level > yesterday)
                    if (!isNew && !escalated) {
                        // To'lqin davomi: jim belgilanadi, keyingi kun ham zanjirga ulanadi.
                        if (before == null) notified[k] = level
                        continue
                    }
                    // Bugungi issiqlik cho'qqisi o'tib bo'lgan bo'lsa — kechikkan «bugun» xabari yuborilmaydi va belgilanmaydi
                    // (aks holda ertangi kun «to'lqin davomi» deb jim qolardi).
                    val peakPassed =
                        hazard == Hazard.HEAT && day.date == today && day.feelsPeakHour?.let { report.localNow.hour > it } == true
                    if (peakPassed && level < RiskLevel.EMERGENCY) continue
                    val send = settings.notificationsEnabled && (!quiet || level == RiskLevel.EMERGENCY) && (!firstRun || level == RiskLevel.EMERGENCY)
                    if (send) {
                        due += Due(report, day, hazard, level, escalated || (before == null && yesterday != null), risk.personalScore)
                        notified[k] = level
                    } else if (firstRun || !settings.notificationsEnabled) {
                        // Birinchi ishga tushish yoki bildirishnomalar o'chiq — «ko'rilgan» deb belgilanadi.
                        notified[k] = level
                    }
                    // Sokin soatlar: belgilanmaydi — ertalabgi sinxronlashda yuboriladi.
                }
            }
        }

        val sorted = due.sortedWith(compareByDescending<Due> { it.level }.thenBy { it.day.date }.thenByDescending { it.score })
        val list = sorted.take(MAX_PER_SYNC).map(::notification).toMutableList()
        if (sorted.size > MAX_PER_SYNC) {
            val rest = sorted.drop(MAX_PER_SYNC)
            list +=
                AlertNotification(
                    placeId = snapshot.main?.place?.id ?: rest.first().report.place.id,
                    key = "summary",
                    title = "Yana ${rest.size} ta ogohlantirish",
                    body = rest.joinToString("; ") { "${it.report.place.name}: ${it.hazard.uz.lowercase()}, ${dayWord(it.day.date, it.report)}" },
                    level = rest.maxOf { it.level },
                    critical = false,
                )
        }
        return Decision(list, notified)
    }

    private fun notification(d: Due): AlertNotification {
        val place = d.report.place.name
        val whenWord = dayWord(d.day.date, d.report)
        val streak = episodeLength(d.report, d.hazard, d.day.date, d.level)
        val risk = d.day.risk(d.hazard)!!
        val title =
            when (d.hazard) {
                Hazard.HEAT -> "${d.level.uz} issiqlik — $place, $whenWord"
                Hazard.AIR -> "Havo ifloslanishi: ${d.level.uz.lowercase()} — $place, $whenWord"
            }
        val body =
            buildString {
                if (d.escalated) append("Xavf darajasi oshdi. ")
                when (d.hazard) {
                    Hazard.HEAT -> {
                        d.day.feelsMax?.let { append("Issiqlik ko'rsatkichi ${it.roundToInt()}°C gacha") }
                        d.day.feelsPeakHour?.let { append(" (${it.toString().padStart(2, '0')}:00 atrofida)") }
                        append(". ")
                    }
                    Hazard.AIR -> d.day.air?.pm25Mean?.let { append("PM2.5 o'rtacha ${it.roundToInt()} µg/m³ (JSST tavsiyasi 15). ") }
                }
                if (streak > 1) append("Kamida $streak kun davom etishi kutilmoqda. ")
                append(risk.advice.firstOrNull() ?: d.level.advice)
            }
        return AlertNotification(
            placeId = d.report.place.id,
            key = key(d.report.place.id, d.hazard, d.day.date),
            title = title,
            body = body,
            level = d.level,
            critical = d.level >= RiskLevel.WARNING,
        )
    }

    /** Shu kundan boshlab prognozda daraja necha kun shu darajada yoki yuqori turadi. */
    private fun episodeLength(
        r: PlaceReport,
        h: Hazard,
        from: LocalDate,
        level: RiskLevel,
    ): Int =
        r.days
            .filter { !it.date.isBefore(from) }
            .takeWhile { (it.risk(h)?.personalLevel ?: RiskLevel.CALM) >= level }
            .size

    private fun dayWord(
        date: LocalDate,
        r: PlaceReport,
    ): String =
        when (date) {
            r.localNow.toLocalDate() -> "bugun"
            r.localNow.toLocalDate().plusDays(1) -> "ertaga"
            else -> "${date.dayOfMonth}-${MONTHS[date.monthValue - 1]}"
        }

    companion object {
        const val MAX_PER_SYNC = 3
        const val HORIZON_DAYS = 1L
        val QUIET_START: LocalTime = LocalTime.of(22, 0)
        val QUIET_END: LocalTime = LocalTime.of(7, 0)
        private val MONTHS =
            listOf("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr")

        fun key(
            placeId: String,
            hazard: Hazard,
            date: LocalDate,
        ) = "$placeId|${hazard.name}|$date"

        private fun parseDate(key: String): LocalDate? = runCatching { LocalDate.parse(key.substringAfterLast('|')) }.getOrNull()
    }
}
