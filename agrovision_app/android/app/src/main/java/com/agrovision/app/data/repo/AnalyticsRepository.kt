package com.agrovision.app.data.repo

import com.agrovision.app.core.math.KMeans
import com.agrovision.app.core.math.Stats
import com.agrovision.app.core.round1
import com.agrovision.app.core.round2
import com.agrovision.app.data.local.*
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class ScatterPoint(val x: Double, val y: Double, val label: String)

data class CorrelationResult(val points: List<ScatterPoint>, val r: Double)

data class HeatmapData(
    val rows: List<String>,
    val columns: List<String>,
    /** [rowIndex][colIndex] → qiymat yoki null. */
    val values: List<List<Double?>>,
)

data class ClusterRow(
    val region: String,
    val avgYield: Double,
    val production: Double,
    val precip: Double,
    val segment: String,
)

data class SeasonalityPoint(val month: Int, val index: Double)

@Singleton
class AnalyticsRepository @Inject constructor(
    private val yieldDao: YieldDao,
    private val weatherDao: WeatherDao,
    private val marketDao: MarketDao,
) {
    /** Hosildorlik trendi + N yillik prognoz (ishonch oralig'i bilan). */
    suspend fun trendForecast(periods: Int = 3): Pair<List<YearYieldRow>, Stats.Forecast> {
        val trend = yieldDao.trend()
        return trend to Stats.linearForecast(trend.map { it.avgYield }, periods)
    }

    /** Yog'ingarchilik ↔ hosildorlik korrelyatsiyasi (tuman×yil). */
    suspend fun rainfallYieldCorrelation(): CorrelationResult {
        val yields = yieldDao.districtYearYield()
        val seasons = weatherDao.seasonByDistrictYear().associateBy { it.districtId to it.year }
        val points = yields.mapNotNull { row ->
            val season = seasons[row.districtId to row.year] ?: return@mapNotNull null
            ScatterPoint(season.precip.round1(), row.avgYield.round2(), "${row.district} ${row.year}")
        }
        val r = Stats.correlation(points.map { it.x }, points.map { it.y })
        return CorrelationResult(points, r)
    }

    /** Hudud × ekin hosildorlik matritsasi (heatmap uchun). */
    suspend fun regionCropHeatmap(year: Int, maxCrops: Int = 10): HeatmapData {
        val matrix = yieldDao.regionCropMatrix(year)
        if (matrix.isEmpty()) return HeatmapData(emptyList(), emptyList(), emptyList())
        val topCrops = matrix.groupBy { it.crop }
            .entries.sortedByDescending { it.value.size }
            .take(maxCrops).map { it.key }
        val regions = matrix.map { it.region }.distinct().sorted()
        val lookup = matrix.associate { (it.region to it.crop) to it.avgYield }
        val values = regions.map { region -> topCrops.map { crop -> lookup[region to crop] } }
        return HeatmapData(regions, topCrops, values)
    }

    /** Narxlarning mavsumiyligi: oylik indeks (o'rtacha = 100). */
    suspend fun priceSeasonality(): List<SeasonalityPoint> {
        val since = LocalDate.now().minusYears(5).toEpochDay()
        val prices = marketDao.since(since)
        if (prices.isEmpty()) return emptyList()
        val byMonth = prices.groupBy { LocalDate.ofEpochDay(it.epochDay).monthValue }
            .mapValues { (_, rows) -> rows.sumOf { it.price } / rows.size }
        val overall = byMonth.values.average().let { if (it <= 0) 1.0 else it }
        return (1..12).mapNotNull { month ->
            byMonth[month]?.let { SeasonalityPoint(month, (it / overall * 100).round1()) }
        }
    }

    /**
     * Viloyatlar segmentatsiyasi (K-Means, 3 klaster) — hosildorlik, ishlab
     * chiqarish va mavsumiy yog'in bo'yicha. Desktop analitika sahifasidagi
     * `sklearn.cluster.KMeans` bilan bir xil yondashuv.
     */
    suspend fun regionSegments(year: Int): List<ClusterRow> {
        val regions = yieldDao.byRegion(year)
        if (regions.isEmpty()) return emptyList()
        val rainfall = weatherDao.seasonByRegionYear()
            .filter { it.year == year }
            .associate { it.region to it.precip }

        val raw = regions.map {
            doubleArrayOf(it.avgYield, it.production, rainfall[it.region] ?: 0.0)
        }.toTypedArray()

        if (regions.size < 3) {
            return regions.map {
                ClusterRow(it.region, it.avgYield, it.production, (rainfall[it.region] ?: 0.0).round1(), "A — yuqori salohiyat")
            }
        }

        val result = KMeans.fit(KMeans.standardize(raw), k = 3)
        // Klasterlarni o'rtacha hosildorlik bo'yicha tartiblab nom berish
        val names = listOf("A — yuqori salohiyat", "B — o'rtacha", "C — e'tibor talab")
        val order = result.labels.indices.groupBy { result.labels[it] }
            .entries.sortedByDescending { entry -> entry.value.map { regions[it].avgYield }.average() }
            .mapIndexed { rank, entry -> entry.key to names.getOrElse(rank) { "D" } }
            .toMap()

        return regions.indices.map { i ->
            ClusterRow(
                region = regions[i].region,
                avgYield = regions[i].avgYield,
                production = regions[i].production,
                precip = (rainfall[regions[i].region] ?: 0.0).round1(),
                segment = order[result.labels[i]] ?: "—",
            )
        }.sortedBy { it.segment }
    }
}
