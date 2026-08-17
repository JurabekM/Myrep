package com.agrovision.mobile.data.repository

import com.agrovision.mobile.data.local.*
import com.agrovision.mobile.data.remote.WeatherApi
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class SeasonSummary(val precip: Double, val tAvg: Double, val humidity: Double)

sealed class FetchResult {
    data class Success(val daysFetched: Int) : FetchResult()
    data object NoInternet : FetchResult()
    data object AlreadyUpToDate : FetchResult()
}

/**
 * Ob-havo repositoriysi — HIBRID: agar internet mavjud bo'lsa, Open-Meteo'dan
 * HAQIQIY tarixiy (archive) va joriy prognoz ma'lumotini yuklab, mahalliy
 * bazada keshlaydi. Internet bo'lmasa, oxirgi keshlangan ma'lumot bilan ishlaydi
 * (hech qachon qulamaydi — barcha tarmoq chaqiruvlari try/catch bilan himoyalangan
 * `WeatherApi` ichida).
 */
@Singleton
class WeatherRepository @Inject constructor(
    private val weatherDao: WeatherDao,
    private val geoDao: GeoDao,
) {
    /** Tuman uchun so'nggi 1 yillik tarixiy ma'lumotni internetdan yuklab keshlaydi. */
    suspend fun refreshHistory(district: DistrictEntity, days: Int = 365): FetchResult {
        val end = LocalDate.now().minusDays(1)
        val latestCached = weatherDao.latestEpochDay(district.id)
        val start = if (latestCached != null && latestCached >= end.minusDays(2).toEpochDay()) {
            return FetchResult.AlreadyUpToDate
        } else if (latestCached != null) {
            LocalDate.ofEpochDay(latestCached + 1)
        } else {
            end.minusDays(days.toLong())
        }
        if (start.isAfter(end)) return FetchResult.AlreadyUpToDate

        val points = WeatherApi.fetchHistory(district.lat, district.lon, start, end) ?: return FetchResult.NoInternet
        if (points.isEmpty()) return FetchResult.NoInternet

        weatherDao.deleteRange(district.id, start.toEpochDay(), end.toEpochDay())
        weatherDao.insertAll(
            points.map {
                WeatherRecordEntity(
                    districtId = district.id, epochDay = it.date.toEpochDay(),
                    tMin = it.tMin, tMax = it.tMax, precipitationMm = it.precip, humidity = it.humidity,
                )
            },
        )
        return FetchResult.Success(points.size)
    }

    /** 7 kunlik jonli prognoz (internet talab qiladi; muvaffaqiyatsiz bo'lsa null). */
    suspend fun fetchLiveForecast(district: DistrictEntity): List<WeatherApi.DailyPoint>? =
        WeatherApi.fetchForecast(district.lat, district.lon, 7)

    suspend fun hasCachedData(districtId: Long): Boolean = weatherDao.countForDistrict(districtId) > 0

    suspend fun history(districtId: Long, days: Int = 365): List<WeatherDailyRow> {
        val since = (LocalDate.now().minusDays(days.toLong())).toEpochDay()
        return weatherDao.history(districtId, since)
    }

    suspend fun monthlyClimate(districtId: Long): List<WeatherMonthlyClimateRow> =
        weatherDao.monthlyClimate(districtId)

    suspend fun seasonSummary(regionName: String, year: Int): SeasonSummary? {
        val row = weatherDao.seasonSummaryRaw(regionName, year) ?: return null
        if (row.precip == null) return null
        return SeasonSummary(row.precip, row.tAvg ?: 0.0, row.humidity ?: 0.0)
    }

    suspend fun seasonalByDistrictYear(): List<DistrictYearPrecipRow> = weatherDao.seasonalByDistrictYear()

    suspend fun districtOptions(): List<Pair<Long, String>> {
        val districts = geoDao.districts()
        val regions = geoDao.regions().associateBy { it.id }
        return districts.map { it.id to "${it.name} (${regions[it.regionId]?.name ?: ""})" }
    }

    suspend fun districtEntity(districtId: Long): DistrictEntity? = geoDao.districts().firstOrNull { it.id == districtId }
}
