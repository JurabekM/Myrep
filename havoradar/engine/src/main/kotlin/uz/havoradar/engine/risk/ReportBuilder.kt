package uz.havoradar.engine.risk

import uz.havoradar.engine.model.AirDay
import uz.havoradar.engine.model.AirSeries
import uz.havoradar.engine.model.DayReport
import uz.havoradar.engine.model.HourPoint
import uz.havoradar.engine.model.Place
import uz.havoradar.engine.model.PlaceReport
import uz.havoradar.engine.model.Vulnerability
import uz.havoradar.engine.model.WeatherSeries
import java.time.Instant
import java.time.LocalDate
import java.time.ZoneOffset
import java.time.temporal.ChronoUnit

/** Soatlik qatorlardan kunlik hisobot: issiqlik, havo sifati, UV va «nega bu daraja?» sabablari. */
object ReportBuilder {
    /** Kunlik ko'rsatkich uchun kamida shuncha soatlik qiymat kerak (aks holda kun baholanmaydi). */
    const val MIN_HOURS = 18
    const val MAX_DAYS = 7
    const val CHART_HOURS = 48
    const val NIGHT_FROM = 18
    const val NIGHT_TO = 9

    fun build(
        place: Place,
        weather: WeatherSeries?,
        air: AirSeries?,
        profile: Set<Vulnerability>,
        now: Instant,
    ): PlaceReport {
        val offset = weather?.utcOffsetSeconds ?: air?.utcOffsetSeconds ?: 0
        val localNow = now.atOffset(ZoneOffset.ofTotalSeconds(offset)).toLocalDateTime()
        val today = localNow.toLocalDate()

        val wByDay = weather?.let { w -> w.times.indices.groupBy { w.times[it].toLocalDate() } }.orEmpty()
        val aByDay = air?.let { a -> a.times.indices.groupBy { a.times[it].toLocalDate() } }.orEmpty()

        // Ketma-ket «Xavf» toifasidagi kunlar (o'tgan kunlar ham hisobga olinadi).
        val streaks = HashMap<LocalDate, Int>()
        var run = 0
        var prev: LocalDate? = null
        for (date in wByDay.keys.sorted()) {
            val feels = weather?.let { w -> dailyFeels(w, wByDay.getValue(date)) }
            val danger = feels != null && feels.first >= HeatRisk.DANGER
            run = if (danger && prev != null && date == prev.plusDays(1)) run + 1 else if (danger) 1 else 0
            streaks[date] = run
            prev = date
        }

        val dates = (wByDay.keys + aByDay.keys).filter { !it.isBefore(today) }.sorted().take(MAX_DAYS)
        val days =
            dates.map { date ->
                val wi = wByDay[date].orEmpty()
                val temps = weather?.let { w -> wi.mapNotNull { w.temp[it] } }.orEmpty()
                val fullWeather = weather != null && temps.size >= MIN_HOURS
                val feels = if (fullWeather) dailyFeels(weather, wi) else null
                val tMax = if (fullWeather) temps.max() else null
                val tMin = if (fullWeather) temps.min() else null
                val uvMax = weather?.let { w -> wi.mapNotNull { w.uv[it] }.maxOrNull() }
                val airDay = air?.let { a -> airDay(a, aByDay[date].orEmpty()) }
                DayReport(
                    date = date,
                    tempMax = tMax,
                    tempMin = tMin,
                    feelsMax = feels?.first,
                    feelsPeakHour = feels?.second,
                    uvMax = uvMax,
                    air = airDay,
                    heatRisk =
                        if (feels != null) {
                            HeatRisk.assess(tMax!!, feels.first, feels.second, nightMin(weather, wByDay, date) ?: tMin, streaks[date] ?: 0, profile)
                        } else {
                            null
                        },
                    airRisk = airDay?.let { AirRisk.assess(it, profile) },
                )
            }

        val hourNow = localNow.truncatedTo(ChronoUnit.HOURS)
        val hours = mergeHours(weather, air).filter { !it.time.isBefore(hourNow) }.take(CHART_HOURS)
        return PlaceReport(
            place = place,
            localNow = localNow,
            current = hours.firstOrNull()?.takeIf { it.time == hourNow },
            days = days,
            hours = hours,
            weatherFetchedAt = weather?.fetchedAt,
            airFetchedAt = air?.fetchedAt,
        )
    }

    /**
     * Issiq kundan keyingi tun (18:00–09:00) eng past harorati — organizm aynan shu tunda tiklanishi kerak.
     * Kalendar kunining minimumi odatda o'sha kun ertalabi (ya'ni oldingi tun) bo'ladi. Ertasi ertalab prognozda
     * bo'lmasa — null (chaqiruvchi kalendar minimumini oladi).
     */
    private fun nightMin(
        w: WeatherSeries?,
        byDay: Map<LocalDate, List<Int>>,
        date: LocalDate,
    ): Double? {
        if (w == null) return null
        val evening = byDay[date].orEmpty().filter { w.times[it].hour >= NIGHT_FROM }.mapNotNull { w.temp[it] }
        val morning = byDay[date.plusDays(1)].orEmpty().filter { w.times[it].hour < NIGHT_TO }.mapNotNull { w.temp[it] }
        if (evening.size < 4 || morning.size < 6) return null
        return (evening + morning).min()
    }

    /** Kunning eng yuqori issiqlik ko'rsatkichi va u kuzatiladigan soat. */
    private fun dailyFeels(
        w: WeatherSeries,
        idx: List<Int>,
    ): Pair<Double, Int>? =
        idx
            .mapNotNull { i -> w.temp[i]?.let { t -> HeatIndex.feels(t, w.humidity[i]) to w.times[i].hour } }
            .maxByOrNull { it.first }

    private fun airDay(
        a: AirSeries,
        idx: List<Int>,
    ): AirDay? {
        fun mean(values: List<Double?>): Double? {
            val v = idx.mapNotNull { values[it] }
            return if (v.size >= MIN_HOURS) v.average() else null
        }
        val pm25 = mean(a.pm25)
        val pm10 = mean(a.pm10)
        if (pm25 == null && pm10 == null) return null
        val dust = mean(a.dust)
        return AirDay(
            pm25Mean = pm25,
            pm10Mean = pm10,
            ozoneMax8h = max8h(idx.map { a.ozone[it] }),
            no2Mean = mean(a.no2),
            no2Max = idx.mapNotNull { a.no2[it] }.maxOrNull(),
            dustShare = if (dust != null && pm10 != null && pm10 > 0) (dust / pm10).coerceIn(0.0, 1.0) else null,
            worstHour = idx.filter { a.pm25[it] != null }.maxByOrNull { a.pm25[it]!! }?.let { a.times[it].hour },
        )
    }

    /** JSST ozon ko'rsatkichi: kun ichidagi 8 soatlik sirpanuvchi o'rtachaning eng kattasi. */
    internal fun max8h(values: List<Double?>): Double? =
        values
            .windowed(8)
            .mapNotNull { w -> w.filterNotNull().takeIf { it.size >= 6 }?.average() }
            .maxOrNull()

    private fun mergeHours(
        w: WeatherSeries?,
        a: AirSeries?,
    ): List<HourPoint> {
        if (w == null) {
            return a?.let { s -> s.times.indices.map { i -> HourPoint(s.times[i], null, null, null, null, s.pm25[i], s.pm10[i]) } }.orEmpty()
        }
        val airAt = a?.let { s -> s.times.indices.associateBy { s.times[it] } }.orEmpty()
        return w.times.indices.map { i ->
            val ai = airAt[w.times[i]]
            val temp = w.temp[i]
            HourPoint(
                time = w.times[i],
                temp = temp,
                feels = temp?.let { HeatIndex.feels(it, w.humidity[i]) },
                humidity = w.humidity[i],
                uv = w.uv[i],
                pm25 = if (ai != null && a != null) a.pm25[ai] else null,
                pm10 = if (ai != null && a != null) a.pm10[ai] else null,
            )
        }
    }
}
