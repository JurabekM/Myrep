package uz.dehqonkomakchi.app.data.remote.weather

import kotlinx.coroutines.delay
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton
import kotlin.math.roundToInt
import kotlin.random.Random

/**
 * Synthetic weather generator seeded by region name + day-of-year so results are stable within
 * a day (deterministic-ish) but vary across regions/days. Lets the whole irrigation feature work
 * fully offline with zero API keys.
 */
@Singleton
class MockWeatherProvider @Inject constructor() : WeatherProvider {

    override suspend fun fetchWeather(region: String): WeatherSnapshot {
        delay(300)
        val today = LocalDate.now()
        val seed = region.hashCode() + today.dayOfYear
        val random = Random(seed)

        val baseTemp = 22 + random.nextInt(-4, 12) // rough seasonal-ish variance
        val currentTemp = baseTemp + random.nextDouble(-2.0, 2.0)
        val conditions = listOf("Ochiq", "Bulutli", "Yengil yomg'ir", "Issiq va quruq", "Shamolli")
        val currentCondition = conditions[random.nextInt(conditions.size)]

        val forecast = (0..4).map { offset ->
            val day = today.plusDays(offset.toLong())
            val daySeed = Random(seed + offset)
            val min = baseTemp - daySeed.nextInt(2, 6)
            val max = baseTemp + daySeed.nextInt(2, 8)
            val rainChance = daySeed.nextInt(0, 100)
            DailyForecast(
                epochDay = day.toEpochDay(),
                tempMinC = min.toDouble(),
                tempMaxC = max.toDouble(),
                rainProbabilityPercent = rainChance,
                summaryUzbek = when {
                    rainChance > 60 -> "Yomg'ir ehtimoli yuqori"
                    rainChance > 30 -> "Yomg'ir ehtimoli bor"
                    max > 34 -> "Issiq kun"
                    else -> "Quyoshli"
                },
            )
        }

        return WeatherSnapshot(
            region = region,
            currentTempC = (currentTemp * 10).roundToInt() / 10.0,
            currentConditionUzbek = currentCondition,
            forecast = forecast,
            fetchedAtEpochMillis = System.currentTimeMillis(),
        )
    }
}
