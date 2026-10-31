package uz.epiradar.engine.trend

import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.model.Anomaly
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.model.TrendPoint
import uz.epiradar.engine.model.TrendSeries
import uz.epiradar.engine.model.TrendStatus
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit
import java.util.Locale

/** FluNet haftalik ma'lumotidan trend, anomaliya va (kerak bo'lsa) signal yaratadi. */
class TrendAnalyzer(
    private val countries: Countries,
) {
    data class Output(
        val series: TrendSeries,
        val signals: List<Signal>,
    )

    fun analyze(
        iso3: String,
        weeks: List<FluWeek>,
        today: LocalDate,
    ): Output {
        val name = countries.nameUz(iso3)
        val title = "Gripp: laboratoriya musbatligi — $name"
        if (weeks.isEmpty()) {
            return Output(empty(iso3, title, "JSST FluNet'da bu mamlakat bo'yicha ma'lumot yo'q."), emptyList())
        }
        // Uzluksiz haftalik qator (yetishmayotgan hafta — null).
        val first = weeks.first().weekStart
        val byWeek = weeks.associateBy { it.weekStart }
        val count = ChronoUnit.WEEKS.between(first, weeks.last().weekStart).toInt() + 1
        val dates = (0 until count).map { first.plusWeeks(it.toLong()) }
        val values: List<Double?> = dates.map { byWeek[it]?.positivity }

        val shown = dates.indices.toList().takeLast(SHOWN_WEEKS)
        val points = shown.mapNotNull { i -> values[i]?.let { TrendPoint(dates[i].toString(), it.round1(), byWeek[dates[i]]?.tested ?: 0) } }

        val novel = weeks.filter { it.h5 > 0 || it.h7n9 > 0 }.filter { ChronoUnit.WEEKS.between(it.weekStart, today) <= NOVEL_LOOKBACK_WEEKS }
        val signals = novel.map { novelSignal(iso3, it) }.toMutableList()

        val recent = values.takeLast(26).count { it != null }
        val lastIdx = values.indices.lastOrNull { values[it] != null }
        val stale = lastIdx == null || ChronoUnit.WEEKS.between(dates[lastIdx], today) > MAX_LAG_WEEKS
        if (lastIdx == null || stale || recent < 8) {
            val note =
                if (stale) {
                    "So'nggi ${MAX_LAG_WEEKS} haftada yangi laboratoriya ma'lumoti kelmagan."
                } else {
                    "Laboratoriya namunalari kam (haftasiga ${FluWeek.MIN_TESTED} tadan kam) — statistik tahlil ishonchli emas."
                }
            return Output(
                TrendSeries("flu:$iso3", iso3, title, "%", points, emptyList(), TrendStatus.NO_DATA, novel.map { it.weekStart.toString() }, note),
                signals,
            )
        }

        val anomalies = mutableListOf<Anomaly>()
        for (i in shown) {
            val r = Aberration.earsC2(values, i) ?: continue
            val x = values[i] ?: continue
            if (r.alarm && x >= MIN_ALARM_POSITIVITY) {
                anomalies += Anomaly(dates[i].toString(), x.round1(), r.mean.round1(), r.threshold.round1(), "EARS C2")
            }
        }

        val x = values[lastIdx]!!
        val lastDate = dates[lastIdx]
        val c2 = Aberration.earsC2(values, lastIdx)
        val historical = seasonalBaseline(dates, values, lastIdx)
        val hl = Aberration.historicalLimit(x, historical)
        val status =
            when {
                hl?.alarm == true && x >= MIN_ALARM_POSITIVITY -> TrendStatus.UNUSUAL
                c2?.alarm == true && x >= MIN_ALARM_POSITIVITY -> TrendStatus.RISING
                else -> TrendStatus.NORMAL
            }
        if (hl?.alarm == true && x >= MIN_ALARM_POSITIVITY) {
            anomalies += Anomaly(lastDate.toString(), x.round1(), hl.mean.round1(), hl.threshold.round1(), "Mavsumiy chegara")
        }

        val expected = hl?.mean ?: c2?.mean
        val note =
            buildString {
                append("${lastDate.uz()} haftasi: namunalarning ${x.fmt()}% i gripp musbat")
                if (expected != null) append(" (odatdagi ~${expected.fmt()}%)")
                append(". ")
                append(
                    when (status) {
                        TrendStatus.UNUSUAL -> "Bu o'tgan yillarning shu davridagi me'yordan sezilarli yuqori."
                        TrendStatus.RISING -> "So'nggi haftalarda keskin o'sish (EARS C2 signali)."
                        else -> "Ko'rsatkich me'yor doirasida."
                    },
                )
            }

        if (status != TrendStatus.NORMAL) {
            val unusual = status == TrendStatus.UNUSUAL
            signals +=
                Signal(
                    // Mamlakat bo'yicha barqaror id: har hafta yangi hodisa (va qayta bildirishnoma) bo'lmasligi uchun.
                    id = "flunet:flu:$iso3",
                    source = SourceId.WHO_FLUNET,
                    title = if (unusual) "Gripp faolligi mavsum me'yoridan yuqori — $name" else "Gripp faolligi o'smoqda — $name",
                    summary = note,
                    url = FLUNET_URL,
                    publishedAt = lastDate.plusDays(7).atStartOfDay().toInstant(ZoneOffset.UTC),
                    countries = listOf(iso3),
                    diseaseId = "influenza",
                    flags = if (unusual) setOf(SignalFlag.ESCALATING) else emptySet(),
                )
        }

        return Output(
            TrendSeries("flu:$iso3", iso3, title, "%", points, anomalies, status, novel.map { it.weekStart.toString() }, note),
            signals,
        )
    }

    /** O'tgan 1–3 yilning shu haftasi ±2 hafta (jami 15 tagacha nuqta). */
    private fun seasonalBaseline(
        dates: List<LocalDate>,
        values: List<Double?>,
        t: Int,
    ): List<Double> {
        val index = dates.withIndex().associate { it.value to it.index }
        val result = mutableListOf<Double>()
        for (year in 1..3) {
            val center = dates[t].minusWeeks(52L * year)
            for (shift in -2..2) {
                // Qator uzluksiz haftalik, shuning uchun 52·k hafta oldingi sana ham qatorda bor (agar shuncha tarix bo'lsa).
                index[center.plusWeeks(shift.toLong())]?.let { values[it] }?.let { result += it }
            }
        }
        return result
    }

    private fun novelSignal(
        iso3: String,
        w: FluWeek,
    ): Signal {
        val name = countries.nameUz(iso3)
        val subtype = if (w.h5 > 0) "A(H5)" else "A(H7N9)"
        return Signal(
            id = "flunet:novel:$iso3:${w.weekStart}",
            source = SourceId.WHO_FLUNET,
            title = "Odam namunasida $subtype qush grippi aniqlandi — $name",
            summary =
                "JSST FluNet: ${w.weekStart.uz()} haftasida laboratoriya $subtype virusini aniqlagan " +
                    "(${w.h5 + w.h7n9} ta namuna). Odamdan odamga yuqish haqida rasmiy xabarlarni kuzating.",
            url = FLUNET_URL,
            publishedAt = w.weekStart.plusDays(7).atStartOfDay().toInstant(ZoneOffset.UTC),
            countries = listOf(iso3),
            diseaseId = "avian_flu",
            flags = setOf(SignalFlag.NOVEL_PATHOGEN),
        )
    }

    private fun empty(
        iso3: String,
        title: String,
        note: String,
    ) = TrendSeries("flu:$iso3", iso3, title, "%", emptyList(), emptyList(), TrendStatus.NO_DATA, emptyList(), note)

    companion object {
        const val SHOWN_WEEKS = 78
        const val MAX_LAG_WEEKS = 6L
        const val NOVEL_LOOKBACK_WEEKS = 8L

        /** Musbatlik shundan past bo'lsa (mavsumlararo shovqin) signal berilmaydi. */
        const val MIN_ALARM_POSITIVITY = 5.0
        const val FLUNET_URL = "https://www.who.int/tools/flunet"

        private val months =
            listOf("yanvar", "fevral", "mart", "aprel", "may", "iyun", "iyul", "avgust", "sentabr", "oktabr", "noyabr", "dekabr")

        fun LocalDate.uz(): String = "$dayOfMonth-${months[monthValue - 1]}"

        private fun Double.round1(): Double = Math.round(this * 10) / 10.0

        private fun Double.fmt(): String = String.format(Locale.ROOT, "%.1f", this)
    }
}
