package uz.qarzsiz.core

import kotlinx.serialization.Serializable
import java.time.LocalDate

/** «Kun tartibi» — diqqatni daromad va sog'liqqa qaratadigan kichik odatlar. */
@Serializable
data class Habit(val id: String, val title: String, val enabled: Boolean = true)

object Habits {
    val defaults: List<Habit> = listOf(
        Habit("early", "Erta turdim"),
        Habit("move", "20 daqiqa harakat (piyoda, mashq)"),
        Habit("learn", "30 daqiqa o'qidim yoki kasbimni o'rgandim"),
        Habit("income", "Daromadni oshirish uchun bitta ish qildim"),
        Habit("noimpulse", "Bugun rejasiz xarid qilmadim"),
        Habit("people", "Foydali odam bilan suhbatlashdim"),
    )

    /** Belgi kaliti: «2026-10-31|early». */
    fun key(date: LocalDate, habitId: String): String = "$date|$habitId"

    /**
     * Ketma-ket kunlar: bugun bajarilgan bo'lsa bugundan, aks holda kechadan orqaga sanaladi
     * (bugun hali kun tugamagan — ketma-ketlik uzilmaydi).
     */
    fun streak(done: Set<String>, habitId: String, today: LocalDate): Int {
        var day = if (key(today, habitId) in done) today else today.minusDays(1)
        var count = 0
        while (key(day, habitId) in done) {
            count++
            day = day.minusDays(1)
        }
        return count
    }
}
