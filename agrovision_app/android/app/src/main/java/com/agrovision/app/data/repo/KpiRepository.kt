package com.agrovision.app.data.repo

import com.agrovision.app.core.round1
import com.agrovision.app.core.round2
import com.agrovision.app.core.round3
import com.agrovision.app.data.local.*
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/** Desktop `analytics/kpi.py` → `KPISummary`. */
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
    suspend fun latestYear(): Int = yieldDao.latestYear() ?: LocalDate.now().year

    suspend fun availableYears(): List<Int> =
        yieldDao.years().ifEmpty { listOf(LocalDate.now().year) }

    suspend fun compute(year: Int? = null): KpiSummary {
        val target = year ?: latestYear()
        val counts = yieldDao.kpiCounts()
        val finance = financeDao.yearlySummary().firstOrNull { it.year == target }
        val income = finance?.income ?: 0.0
        val expense = finance?.expense ?: 0.0
        val profit = income - expense
        val ndviSince = LocalDate.now().minusDays(60).toEpochDay()

        return KpiSummary(
            year = target,
            totalAreaHa = counts.area.round1(),
            farms = counts.farms,
            farmers = counts.farmers,
            fields = counts.fields,
            crops = counts.crops,
            avgYieldTHa = yieldDao.avgYield(target).round2(),
            productionT = kotlin.math.round(yieldDao.totalProduction(target)),
            income = income,
            expense = expense,
            profit = profit,
            roiPercent = if (expense > 0) (profit / expense * 100).round1() else 0.0,
            avgNdvi = satelliteDao.avgNdviSince(ndviSince).round3(),
            waterMillionM3 = (irrigationDao.totalWater(target) / 1_000_000).round2(),
        )
    }

    suspend fun yieldTrend(): List<YearYieldRow> = yieldDao.trend()
    suspend fun byRegion(year: Int): List<RegionYieldRow> = yieldDao.byRegion(year)
    suspend fun byRegionAllYears(): List<RegionYearYieldRow> = yieldDao.byRegionAllYears()
    suspend fun cropDistribution(year: Int): List<CropAreaRow> = yieldDao.cropDistribution(year)
    suspend fun regionCropMatrix(year: Int): List<RegionCropRow> = yieldDao.regionCropMatrix(year)
    suspend fun topFarms(year: Int, limit: Int = 10): List<FarmProductionRow> = yieldDao.topFarms(year, limit)
    suspend fun filteredTrend(regionId: Long?, cropId: Long?): List<YearYieldRow> =
        yieldDao.filteredTrend(regionId, cropId)
}
