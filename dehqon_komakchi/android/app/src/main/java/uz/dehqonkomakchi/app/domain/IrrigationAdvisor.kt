package uz.dehqonkomakchi.app.domain

import uz.dehqonkomakchi.app.data.remote.weather.WeatherSnapshot
import uz.dehqonkomakchi.app.data.repo.IrrigationSuggestion
import uz.dehqonkomakchi.app.data.repo.IrrigationUrgency
import java.time.LocalDate

/**
 * Pure, side-effect-free irrigation suggestion logic, extracted from [uz.dehqonkomakchi.app.data.repo.IrrigationRepository]
 * so it is trivially unit-testable without Room/DataStore.
 */
object IrrigationAdvisor {

    fun suggest(
        weather: WeatherSnapshot,
        lastWateredEpochDay: Long?,
        today: LocalDate = LocalDate.now(),
    ): IrrigationSuggestion {
        val todayForecast = weather.forecast.firstOrNull()
        val rainSoon = (todayForecast?.rainProbabilityPercent ?: 0) >= 55
        val hot = weather.currentTempC >= 34
        val daysSinceWatered = lastWateredEpochDay?.let { today.toEpochDay() - it }

        return when {
            rainSoon -> IrrigationSuggestion(
                IrrigationUrgency.HOLD_OFF,
                "Yaqin 24 soatda yomg'ir ehtimoli yuqori — sug'orishni kechiktirib, tuproq holatini kuzatishingiz mumkin.",
            )
            hot && (daysSinceWatered == null || daysSinceWatered >= 2) -> IrrigationSuggestion(
                IrrigationUrgency.WATER_SOON,
                "Havo issiq va so'nggi sug'organingizdan biroz vaqt o'tgan — tuproqni tekshirib, kerak bo'lsa sug'orishni o'ylab ko'ring.",
            )
            daysSinceWatered != null && daysSinceWatered >= 4 -> IrrigationSuggestion(
                IrrigationUrgency.WATER_SOON,
                "So'nggi sug'organingizdan bir necha kun o'tdi — tuproq namligini tekshirib chiqing.",
            )
            else -> IrrigationSuggestion(
                IrrigationUrgency.NORMAL,
                "Hozircha alohida shoshilinch choralarga hojat yo'q — odatdagi tartibda kuzatib boring.",
            )
        }
    }
}
