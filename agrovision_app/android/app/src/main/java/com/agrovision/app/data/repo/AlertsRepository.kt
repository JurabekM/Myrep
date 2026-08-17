package com.agrovision.app.data.repo

import com.agrovision.app.core.Fmt
import com.agrovision.app.core.math.Stats
import com.agrovision.app.data.local.MarketDao
import com.agrovision.app.data.local.SatelliteDao
import com.agrovision.app.data.local.YieldDao
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class Alert(val level: String, val title: String, val detail: String)

/**
 * Qoidaga asoslangan ogohlantirishlar — desktop `analytics/insights.py`
 * dagi 5 turdagi tekshiruvning to'liq porti:
 * qurg'oqchilik · hosildorlik pasayishi · narx anomaliyasi · past NDVI · zarar.
 */
@Singleton
class AlertsRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val marketDao: MarketDao,
    private val satelliteDao: SatelliteDao,
    private val weatherRepository: WeatherRepository,
    private val financeRepository: FinanceRepository,
) {
    suspend fun generate(): List<Alert> {
        val year = yieldDao.latestYear() ?: LocalDate.now().year
        val alerts = mutableListOf<Alert>()
        alerts += droughtAlerts(year)
        alerts += yieldDropAlerts()
        alerts += priceSpikeAlerts()
        alerts += ndviAlerts()
        alerts += lossAlerts(year)
        val rank = mapOf("error" to 0, "warning" to 1, "info" to 2)
        return alerts.sortedBy { rank[it.level] ?: 3 }.take(12)
    }

    /** Mavsumiy yog'ingarchilik o'rtachadan 30%+ kam bo'lsa. */
    private suspend fun droughtAlerts(year: Int): List<Alert> {
        val seasons = weatherRepository.allRegionSeasons()
        if (seasons.isEmpty()) return emptyList()
        return seasons.groupBy { it.region }.mapNotNull { (region, rows) ->
            val current = rows.firstOrNull { it.year == year } ?: return@mapNotNull null
            val mean = rows.map { it.precip }.average()
            if (mean <= 0) return@mapNotNull null
            val deficit = (mean - current.precip) / mean * 100
            if (deficit <= 30) return@mapNotNull null
            Alert(
                "error", "$region: qurg'oqchilik xavfi",
                "$year-yil mavsumida yog'ingarchilik o'rtachadan ${Fmt.dec(deficit, 0)}% kam " +
                    "(${Fmt.dec(current.precip, 0)} mm).",
            )
        }
    }

    /** Viloyat hosildorligi o'tgan yilga nisbatan 12%+ pasaysa. */
    private suspend fun yieldDropAlerts(): List<Alert> {
        val rows = yieldDao.byRegionAllYears()
        return rows.groupBy { it.region }.mapNotNull { (region, series) ->
            if (series.size < 2) return@mapNotNull null
            val sorted = series.sortedBy { it.year }
            val previous = sorted[sorted.size - 2]
            val current = sorted.last()
            val change = Stats.percentChange(previous.avgYield, current.avgYield)
            if (change >= -12) return@mapNotNull null
            Alert(
                "warning", "$region: hosildorlik pasaygan",
                "${current.year}-yilda o'rtacha hosildorlik ${Fmt.dec(change, 1)}% ga kamaydi " +
                    "(${Fmt.dec(previous.avgYield, 2)} → ${Fmt.dec(current.avgYield, 2)} t/ga).",
            )
        }
    }

    /** So'nggi 6 oyda narx z-ball > 2.4 bo'lgan anomaliya. */
    private suspend fun priceSpikeAlerts(): List<Alert> {
        val since = LocalDate.now().minusDays(180).toEpochDay()
        val prices = marketDao.since(since)
        if (prices.isEmpty()) return emptyList()
        return prices.groupBy { it.crop }.mapNotNull { (crop, rows) ->
            val series = rows.sortedBy { it.epochDay }.map { it.price }
            val anomalies = Stats.zscoreAnomalies(series, threshold = 2.4)
            val last = anomalies.lastOrNull() ?: return@mapNotNull null
            if (last < series.size - 3) return@mapNotNull null
            val mean = Stats.mean(series)
            val direction = if (series[last] > mean) "keskin oshdi" else "keskin tushdi"
            Alert(
                "info", "$crop narxi $direction",
                "So'nggi narx ${Fmt.num(series[last], 0)} so'm/kg " +
                    "(6 oylik o'rtacha: ${Fmt.num(mean, 0)} so'm/kg).",
            )
        }.take(3)
    }

    /** NDVI < 0.25 bo'lgan dalalar. */
    private suspend fun ndviAlerts(): List<Alert> {
        val cutoff = LocalDate.now().minusDays(45).toEpochDay()
        return satelliteDao.fieldHealth()
            .filter { it.epochDay >= cutoff && it.ndvi < 0.25 }
            .take(3)
            .map {
                Alert(
                    "warning", "${it.field}: past vegetatsiya indeksi",
                    "${it.farm} dalasida NDVI=${Fmt.dec(it.ndvi, 2)} — o'simlik holati zaif.",
                )
            }
    }

    /** Zarar bilan ishlayotgan xo'jaliklar. */
    private suspend fun lossAlerts(year: Int): List<Alert> =
        financeRepository.losingFarms(year).map {
            Alert(
                "warning", "${it.name}: zarar bilan ishlamoqda",
                "$year-yilda zarar ${Fmt.num(-it.profit / 1e6, 0)} mln so'm " +
                    "(daromad ${Fmt.num(it.income / 1e6, 0)}, xarajat ${Fmt.num(it.expense / 1e6, 0)} mln).",
            )
        }
}
