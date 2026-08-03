package uz.dehqonkomakchi.app.data.remote.weather

data class DailyForecast(
    val epochDay: Long,
    val tempMinC: Double,
    val tempMaxC: Double,
    val rainProbabilityPercent: Int,
    val summaryUzbek: String,
)

data class WeatherSnapshot(
    val region: String,
    val currentTempC: Double,
    val currentConditionUzbek: String,
    val forecast: List<DailyForecast>,
    val fetchedAtEpochMillis: Long,
    val isFromCache: Boolean = false,
)

/**
 * Provider-agnostic weather interface. [MockWeatherProvider] runs on synthetic/seeded data with
 * zero external calls; a real implementation (OpenWeatherMap, Open-Meteo, or a backend proxy at
 * `/v1/weather`) can be swapped in via `di/ProviderModule.kt` without UI changes.
 */
interface WeatherProvider {
    @Throws(Exception::class)
    suspend fun fetchWeather(region: String): WeatherSnapshot
}
