package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.round2
import com.agrovision.mobile.data.local.*
import javax.inject.Inject
import javax.inject.Singleton

data class KpiSummary(
    val year: Int,
    val totalAreaHa: Double,
    val farms: Int,
    val farmers: Int,
    val fields: Int,
    val crops: Int,
    val avgYieldTHa: Double,
    val productionT: Double,
    val income: Double,
    val expense: Double,
    val profit: Double,
    val roiPercent: Double,
    val avgNdvi: Double,
    val waterMillionM3: Double,
)

@Singleton
class KpiRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val financeDao: FinanceDao,
    private val satelliteDao: SatelliteDao,
    private val irrigationDao: IrrigationDao,
) {
    suspend fun latestYear(): Int = yieldDao.latestYear() ?: java.time.LocalDate.now().year
    suspend fun availableYears(): List<Int> = yieldDao.years()

    suspend fun compute(year: Int? = null): KpiSummary {
        val y = year ?: latestYear()
        val counts = yieldDao.kpiCounts()
        val avgYield = yieldDao.avgYield(y)
        val production = yieldDao.totalProduction(y)
        val finance = financeDao.yearlySummary().firstOrNull { it.year == y }
        val income = finance?.income ?: 0.0
        val expense = finance?.expense ?: 0.0
        val profit = income - expense
        val ndvi = satelliteDao.fieldHealth().let { rows -> if (rows.isEmpty()) 0.0 else rows.map { it.ndvi }.average() }
        val water = irrigationDao.usageByRegion(y).sumOf { it.waterMlnM3 }

        return KpiSummary(
            year = y, totalAreaHa = counts.area, farms = counts.farms, farmers = counts.farmers,
            fields = counts.fields, crops = counts.crops, avgYieldTHa = avgYield.round2(),
            productionT = production, income = income, expense = expense, profit = profit,
            roiPercent = if (expense > 0) roundTo(profit / expense * 100, 1) else 0.0,
            avgNdvi = roundTo(ndvi, 3),
            waterMillionM3 = roundTo(water, 2),
        )
    }

    suspend fun yieldTrend(): List<YearYieldRow> = yieldDao.trend()
    suspend fun byRegion(year: Int): List<RegionYieldRow> = yieldDao.byRegion(year)
    suspend fun cropDistribution(year: Int): List<CropAreaRow> = yieldDao.cropDistribution(year)
    suspend fun regionCropMatrix(year: Int): List<RegionCropYieldRow> = yieldDao.regionCropMatrix(year)
    suspend fun topFarms(year: Int, limit: Int = 10): List<FarmProductionRow> = yieldDao.topFarms(year, limit)

    private fun roundTo(value: Double, decimals: Int): Double {
        val factor = Math.pow(10.0, decimals.toDouble())
        return Math.round(value * factor) / factor
    }
}
