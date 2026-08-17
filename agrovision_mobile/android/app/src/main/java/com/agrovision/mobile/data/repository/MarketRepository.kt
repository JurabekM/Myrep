package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.AnalyticsMath
import com.agrovision.mobile.data.local.LatestPriceRow
import com.agrovision.mobile.data.local.MarketDao
import com.agrovision.mobile.data.local.MarketPriceEntity
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class PriceForecast(
    val history: List<Double>,
    val forecast: List<Double>,
    val lower: List<Double>,
    val upper: List<Double>,
)

@Singleton
class MarketRepository @Inject constructor(private val marketDao: MarketDao) {

    suspend fun latestPrices(): List<LatestPriceRow> = marketDao.latestPrices()

    suspend fun history(cropId: Long, days: Int = 730): List<Pair<Long, Double>> {
        val since = LocalDate.now().minusDays(days.toLong()).toEpochDay()
        return marketDao.history(cropId, since).map { it.epochDay to it.price }
    }

    suspend fun forecast(cropId: Long, periods: Int = 8): PriceForecast {
        val values = history(cropId, 365).map { it.second }
        val (forecast, lower, upper) = AnalyticsMath.linearForecast(values, periods)
        return PriceForecast(values.takeLast(26), forecast, lower, upper)
    }

    suspend fun addPrice(cropId: Long, price: Double, marketName: String) {
        marketDao.insertOne(
            MarketPriceEntity(
                cropId = cropId, epochDay = LocalDate.now().toEpochDay(),
                pricePerKg = price, marketName = marketName, source = "manual",
            ),
        )
    }
}
