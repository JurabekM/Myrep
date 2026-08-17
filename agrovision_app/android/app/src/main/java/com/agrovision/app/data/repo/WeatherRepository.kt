package com.agrovision.app.data.repo

import android.content.Context
import com.agrovision.app.core.NetworkStatus
import com.agrovision.app.data.local.*
import com.agrovision.app.data.remote.WeatherApi
import dagger.hilt.android.qualifiers.ApplicationContext
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

data class SeasonSummary(val precip: Double, val tAvg: Double, val humidity: Double)

sealed class SyncResult {
    data class Success(val days: Int, val provider: String) : SyncResult()
    data object UpToDate : SyncResult()
    data object Offline : SyncResult()
    data object Failed : SyncResult()
}

/**
 * Ob-havo — hibrid manba (desktop `weather/service.py` bilan bir xil mantiq):
 * internet mavjud bo'lsa provayderdan (Open-Meteo yoki NASA POWER) haqiqiy
 * ma'lumot yuklab bazaga keshlaydi; internet bo'lmasa keshdagi (yoki
 * namuna) ma'lumot bilan to'liq ishlayveradi.
 */
@Singleton
class WeatherRepository @Inject constructor(
    @ApplicationContext private val context: Context,
    private val weatherDao: WeatherDao,
    private val geoDao: GeoDao,
    private val settingsRepository: SettingsRepository,
) {
    suspend fun isOnline(): Boolean = NetworkStatus.isOnline(context)

    suspend fun provider(): String = settingsRepository.get("weather_provider", "open-meteo")

    /** Tanlangan tuman uchun tarixiy ma'lumotni internetdan yuklab keshlaydi. */
    suspend fun syncHistory(district: DistrictEntity, days: Int = 365): SyncResult {
        if (!isOnline()) return SyncResult.Offline
        val end = LocalDate.now().minusDays(1)
        val cached = weatherDao.latestEpochDay(district.id)
        val start = when {
            cached != null && cached >= end.minusDays(1).toEpochDay() -> return SyncResult.UpToDate
            cached != null && cached > end.minusDays(days.toLong()).toEpochDay() -> LocalDate.ofEpochDay(cached + 1)
            else -> end.minusDays(days.toLong())
        }
        if (start.isAfter(end)) return SyncResult.UpToDate

        val selected = provider()
        val points = if (selected == "nasa-power") {
            WeatherApi.nasaPowerHistory(district.lat, district.lon, start, end)
                ?: WeatherApi.openMeteoHistory(district.lat, district.lon, start, end)
        } else {
            WeatherApi.openMeteoHistory(district.lat, district.lon, start, end)
                ?: WeatherApi.nasaPowerHistory(district.lat, district.lon, start, end)
        } ?: return SyncResult.Failed

        weatherDao.deleteRange(district.id, start.toEpochDay(), end.toEpochDay())
        weatherDao.insertAll(
            points.map {
                WeatherRecordEntity(
                    districtId = district.id, epochDay = it.date.toEpochDay(),
                    tMin = it.tMin, tMax = it.tMax,
                    precipitationMm = it.precipitationMm, humidity = it.humidity,
                    source = selected,
                )
            },
        )
        return SyncResult.Success(points.size, selected)
    }

    /** 7 kunlik jonli prognoz (internetsiz `null`). */
    suspend fun forecast(district: DistrictEntity): List<WeatherApi.DailyPoint>? {
        if (!isOnline()) return null
        return WeatherApi.openMeteoForecast(district.lat, district.lon, 7)
    }

    suspend fun hasData(districtId: Long): Boolean = weatherDao.countForDistrict(districtId) > 0

    suspend fun history(districtId: Long, days: Int = 365): List<WeatherDailyRow> =
        weatherDao.history(districtId, LocalDate.now().minusDays(days.toLong()).toEpochDay())

    suspend fun monthlyClimate(districtId: Long): List<MonthClimateRow> = weatherDao.monthlyClimate(districtId)

    /** Viloyat×yil mavsumiy xulosa — AI va ogohlantirishlar uchun. */
    suspend fun seasonSummary(regionName: String, year: Int): SeasonSummary? {
        val row = weatherDao.seasonByRegionYear()
            .firstOrNull { it.region == regionName && it.year == year } ?: return null
        return SeasonSummary(row.precip, row.tAvg, row.humidity)
    }

    suspend fun allRegionSeasons(): List<RegionSeasonRow> = weatherDao.seasonByRegionYear()

    suspend fun districtOptions(): List<Pair<DistrictEntity, String>> {
        val regionNames = geoDao.regions().associate { it.id to it.name }
        return geoDao.districts().map { it to "${it.name} (${regionNames[it.regionId] ?: ""})" }
    }
}
