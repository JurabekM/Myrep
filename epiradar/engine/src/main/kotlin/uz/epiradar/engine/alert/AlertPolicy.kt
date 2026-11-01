package uz.epiradar.engine.alert

import uz.epiradar.engine.model.OutbreakEvent
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.model.Snapshot
import uz.epiradar.engine.model.ThreatLevel
import java.time.Duration
import java.time.Instant

data class AlertNotification(
    val eventId: String,
    val title: String,
    val body: String,
    val level: ThreatLevel,
    /** Yuqori ustuvorlikdagi kanal (Xavf va Favqulodda). */
    val critical: Boolean,
)

/**
 * Qaysi hodisa haqida push-bildirishnoma yuborishni hal qiladi.
 * Qoidalar: daraja chegaradan past emas · so'nggi [FRESH_DAYS] kunda yangilangan · avval xabar
 * qilinmagan yoki darajasi oshgan · bir sinxronlashda ko'pi bilan [MAX_PER_SYNC] ta + jamlovchi xabar.
 * Birinchi ishga tushishda eski hodisalar «ko'rilgan» deb belgilanadi (faqat Favqulodda xabar qilinadi).
 */
class AlertPolicy {
    data class Decision(
        val notifications: List<AlertNotification>,
        val notified: Map<String, ThreatLevel>,
    )

    fun decide(
        snapshot: Snapshot,
        settings: Settings,
        previouslyNotified: Map<String, ThreatLevel>,
        firstRun: Boolean,
        now: Instant,
    ): Decision {
        val notified = previouslyNotified.filterKeys { id -> snapshot.events.any { it.id == id } }.toMutableMap()
        val due = mutableListOf<Pair<OutbreakEvent, ThreatLevel>>()

        for (e in snapshot.events) {
            val level = effectiveLevel(e, settings)
            val fresh = Duration.between(e.lastUpdated, now).toDays() <= FRESH_DAYS
            val before = notified[e.id]
            val isNewOrEscalated = before == null || level > before
            if (level >= settings.alertThreshold && fresh && isNewOrEscalated) {
                if (!firstRun || level == ThreatLevel.EMERGENCY) due += e to level
            }
            notified[e.id] = maxOf(before ?: level, level)
        }

        if (!settings.notificationsEnabled) return Decision(emptyList(), notified)

        val sorted = due.sortedByDescending { (e, _) -> e.assessment.personalScore }
        val list =
            sorted.take(MAX_PER_SYNC).map { (e, level) ->
                val escalated = previouslyNotified[e.id]?.let { level > it } == true
                AlertNotification(
                    eventId = e.id,
                    title = "${level.uz}: ${e.title}",
                    body =
                        buildString {
                            if (escalated) append("Xavf darajasi oshdi. ")
                            append(e.flags.maxByOrNull { it.weight }?.uz?.let { "$it. " }.orEmpty())
                            append(level.advice)
                        },
                    level = level,
                    critical = level >= ThreatLevel.WARNING,
                )
            }.toMutableList()
        if (sorted.size > MAX_PER_SYNC) {
            val rest = sorted.drop(MAX_PER_SYNC)
            list +=
                AlertNotification(
                    eventId = "summary",
                    title = "Yana ${rest.size} ta yangi ogohlantirish",
                    body = rest.joinToString("; ") { it.first.title },
                    level = rest.maxOf { it.second },
                    critical = false,
                )
        }
        return Decision(list, notified)
    }

    /** Kuzatuv ro'yxatidagi mamlakatda qayd etilgan hodisa uchun — global daraja ham hisobga olinadi. */
    private fun effectiveLevel(
        e: OutbreakEvent,
        settings: Settings,
    ): ThreatLevel {
        val personal = e.assessment.personalLevel
        val watched = e.countries.any { it in settings.watchCountries }
        return if (watched) maxOf(personal, e.assessment.globalLevel) else personal
    }

    companion object {
        const val FRESH_DAYS = 7L
        const val MAX_PER_SYNC = 3
    }
}
