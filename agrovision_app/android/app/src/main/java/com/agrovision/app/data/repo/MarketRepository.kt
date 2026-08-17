package com.agrovision.app.data.repo

import com.agrovision.app.core.math.Stats
import com.agrovision.app.data.local.CropDao
import com.agrovision.app.data.local.CropEntity
import com.agrovision.app.data.local.MarketDao
import com.agrovision.app.data.local.MarketPriceEntity
import com.agrovision.app.data.local.PricePointRow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class MarketPriceRow(
    val cropId: Long,
    val crop: String,
    val price: Double,
    val epochDay: Long,
    /** 30 kunlik o'zgarish, % (desktop `latest_prices`). */
    val change30d: Double,
)

data class PriceForecast(
    val history: List<PricePointRow>,
    val forecast: Stats.Forecast,
)

@Singleton
class MarketRepository @Inject constructor(
    private val marketDao: MarketDao,
    private val cropDao: CropDao,
) {
    /** So'nggi narxlar + 30 kunlik o'zgarish foizi. */
    suspend fun latestPrices(): List<MarketPriceRow> {
        val latest = marketDao.latestPrices()
        if (latest.isEmpty()) return emptyList()
        val since = LocalDate.now().minusDays(400).toEpochDay()
        val history = marketDao.since(since).groupBy { it.crop }
        val monthAgo = LocalDate.now().minusDays(30).toEpochDay()

        return latest.map { row ->
            val series = history[row.crop].orEmpty().sortedBy { it.epochDay }
            val baseline = series.lastOrNull { it.epochDay <= monthAgo }?.price ?: row.price
            MarketPriceRow(
                cropId = row.cropId, crop = row.crop, price = row.price, epochDay = row.epochDay,
                change30d = Stats.percentChange(baseline, row.price),
            )
        }
    }

    suspend fun history(cropId: Long, days: Int = 730): List<PricePointRow> =
        marketDao.history(cropId, LocalDate.now().minusDays(days.toLong()).toEpochDay())

    /** Narx tarixi + haftalik prognoz (ishonch oralig'i bilan). */
    suspend fun forecast(cropId: Long, periods: Int = 8): PriceForecast {
        val history = history(cropId, 365)
        return PriceForecast(history, Stats.linearForecast(history.map { it.price }, periods))
    }

    suspend fun addPrice(cropId: Long, price: Double, marketName: String, date: LocalDate = LocalDate.now()) {
        marketDao.insert(
            MarketPriceEntity(
                cropId = cropId, epochDay = date.toEpochDay(), pricePerKg = price,
                marketName = marketName.ifBlank { "Qo'lda kiritilgan" }, source = "manual",
            ),
        )
    }

    suspend fun crops(): List<CropEntity> = cropDao.all()
}
