package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.AnalyticsMath
import com.agrovision.mobile.data.local.GeoDao
import javax.inject.Inject
import javax.inject.Singleton

data class Alert(val level: String, val title: String, val detail: String)

/** Qoidaga asoslangan ogohlantirishlar: qurg'oqchilik va hosildorlik pasayishi (offline). */
@Singleton
class AlertsRepository @Inject constructor(
    private val geoDao: GeoDao,
    private val kpiRepository: KpiRepository,
    private val weatherRepository: WeatherRepository,
) {
    suspend fun generate(): List<Alert> {
        val year = kpiRepository.latestYear()
        val alerts = mutableListOf<Alert>()
        alerts += droughtAlerts(year)
        alerts += yieldDropAlerts(year)
        return alerts.sortedBy { if (it.level == "error") 0 else if (it.level == "warning") 1 else 2 }.take(8)
    }

    private suspend fun droughtAlerts(year: Int): List<Alert> {
        val regions = geoDao.regions()
        val result = mutableListOf<Alert>()
        for (region in regions) {
            val history = (year - 4 until year).mapNotNull { weatherRepository.seasonSummary(region.name, it) }
            val current = weatherRepository.seasonSummary(region.name, year) ?: continue
            if (history.isEmpty()) continue
            val mean = history.map { it.precip }.average()
            if (mean <= 0) continue
            val deficit = (mean - current.precip) / mean * 100
            if (deficit > 30) {
                result += Alert(
                    "error", "${region.name}: qurg'oqchilik xavfi",
                    "$year-yil mavsumida yog'ingarchilik o'rtachadan ${"%.0f".format(deficit)}% kam (${"%.0f".format(current.precip)} mm).",
                )
            }
        }
        return result
    }

    private suspend fun yieldDropAlerts(year: Int): List<Alert> {
        val current = kpiRepository.byRegion(year).associateBy { it.region }
        val previous = kpiRepository.byRegion(year - 1).associateBy { it.region }
        val result = mutableListOf<Alert>()
        for ((region, currentRow) in current) {
            val prevRow = previous[region] ?: continue
            val change = AnalyticsMath.percentChange(prevRow.avgYield, currentRow.avgYield)
            if (change < -12) {
                result += Alert(
                    "warning", "$region: hosildorlik pasaygan",
                    "$year-yilda o'rtacha hosildorlik ${"%.1f".format(change)}% ga kamaydi " +
                        "(${"%.2f".format(prevRow.avgYield)} → ${"%.2f".format(currentRow.avgYield)} t/ga).",
                )
            }
        }
        return result
    }
}
