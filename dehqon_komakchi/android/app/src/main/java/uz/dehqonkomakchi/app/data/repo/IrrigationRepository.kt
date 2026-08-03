package uz.dehqonkomakchi.app.data.repo

import kotlinx.serialization.Serializable
import kotlinx.serialization.encodeToString
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.json.Json
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.data.db.dao.WeatherCacheDao
import uz.dehqonkomakchi.app.data.db.entity.WeatherCacheEntity
import uz.dehqonkomakchi.app.data.remote.weather.DailyForecast
import uz.dehqonkomakchi.app.data.remote.weather.WeatherProvider
import uz.dehqonkomakchi.app.data.remote.weather.WeatherSnapshot
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
private data class CachedForecastDto(
    val epochDay: Long,
    val tempMinC: Double,
    val tempMaxC: Double,
    val rainProbabilityPercent: Int,
    val summaryUzbek: String,
)

@Serializable
private data class CachedWeatherDto(
    val region: String,
    val currentTempC: Double,
    val currentConditionUzbek: String,
    val forecast: List<CachedForecastDto>,
)

enum class IrrigationUrgency { HOLD_OFF, NORMAL, WATER_SOON }

data class IrrigationSuggestion(
    val urgency: IrrigationUrgency,
    val messageUzbek: String,
)

/**
 * Fetches weather via [WeatherProvider], caches the last successful snapshot in Room so the
 * irrigation screen keeps working offline, and derives a simple adaptive (non-commanding)
 * watering suggestion from temperature, rain probability, and days since last logged watering.
 */
@Singleton
class IrrigationRepository @Inject constructor(
    private val provider: WeatherProvider,
    private val cacheDao: WeatherCacheDao,
    private val userPrefs: UserPrefs,
) {
    private val json = Json { ignoreUnknownKeys = true }

    suspend fun getWeather(region: String): WeatherSnapshot {
        return try {
            val fresh = provider.fetchWeather(region)
            cacheDao.upsert(
                WeatherCacheEntity(
                    region = region,
                    payloadJson = json.encodeToString(fresh.toDto()),
                    fetchedAtEpochMillis = fresh.fetchedAtEpochMillis,
                ),
            )
            fresh
        } catch (e: Exception) {
            loadFromCache(region) ?: throw e
        }
    }

    private suspend fun loadFromCache(region: String): WeatherSnapshot? {
        val cached = cacheDao.get(region) ?: return null
        val dto = runCatching { json.decodeFromString<CachedWeatherDto>(cached.payloadJson) }.getOrNull()
            ?: return null
        return WeatherSnapshot(
            region = dto.region,
            currentTempC = dto.currentTempC,
            currentConditionUzbek = dto.currentConditionUzbek,
            forecast = dto.forecast.map {
                DailyForecast(it.epochDay, it.tempMinC, it.tempMaxC, it.rainProbabilityPercent, it.summaryUzbek)
            },
            fetchedAtEpochMillis = cached.fetchedAtEpochMillis,
            isFromCache = true,
        )
    }

    suspend fun logWatering() {
        userPrefs.setLastWatered(LocalDate.now().toEpochDay())
    }

    fun suggest(weather: WeatherSnapshot, lastWateredEpochDay: Long?): IrrigationSuggestion =
        uz.dehqonkomakchi.app.domain.IrrigationAdvisor.suggest(weather, lastWateredEpochDay)

    private fun WeatherSnapshot.toDto() = CachedWeatherDto(
        region = region,
        currentTempC = currentTempC,
        currentConditionUzbek = currentConditionUzbek,
        forecast = forecast.map { CachedForecastDto(it.epochDay, it.tempMinC, it.tempMaxC, it.rainProbabilityPercent, it.summaryUzbek) },
    )
}
