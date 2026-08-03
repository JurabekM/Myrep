package uz.dehqonkomakchi.app

import com.google.common.truth.Truth.assertThat
import org.junit.Test
import uz.dehqonkomakchi.app.data.remote.weather.DailyForecast
import uz.dehqonkomakchi.app.data.remote.weather.WeatherSnapshot
import uz.dehqonkomakchi.app.data.repo.IrrigationUrgency
import uz.dehqonkomakchi.app.domain.IrrigationAdvisor
import java.time.LocalDate

class IrrigationAdvisorTest {

    private val today = LocalDate.of(2026, 8, 3)

    private fun weather(rainPercent: Int, currentTemp: Double) = WeatherSnapshot(
        region = "Toshkent viloyati",
        currentTempC = currentTemp,
        currentConditionUzbek = "Ochiq",
        forecast = listOf(
            DailyForecast(today.toEpochDay(), 20.0, currentTemp, rainPercent, "test"),
        ),
        fetchedAtEpochMillis = 0L,
    )

    @Test
    fun `high rain probability suggests holding off regardless of temperature`() {
        val suggestion = IrrigationAdvisor.suggest(weather(rainPercent = 80, currentTemp = 38.0), lastWateredEpochDay = null, today = today)
        assertThat(suggestion.urgency).isEqualTo(IrrigationUrgency.HOLD_OFF)
    }

    @Test
    fun `hot weather with no watering history suggests watering soon`() {
        val suggestion = IrrigationAdvisor.suggest(weather(rainPercent = 10, currentTemp = 36.0), lastWateredEpochDay = null, today = today)
        assertThat(suggestion.urgency).isEqualTo(IrrigationUrgency.WATER_SOON)
    }

    @Test
    fun `hot weather watered yesterday does not urge watering yet`() {
        val yesterday = today.minusDays(1).toEpochDay()
        val suggestion = IrrigationAdvisor.suggest(weather(rainPercent = 10, currentTemp = 36.0), lastWateredEpochDay = yesterday, today = today)
        assertThat(suggestion.urgency).isEqualTo(IrrigationUrgency.NORMAL)
    }

    @Test
    fun `mild weather but four days since watering suggests watering soon`() {
        val fourDaysAgo = today.minusDays(4).toEpochDay()
        val suggestion = IrrigationAdvisor.suggest(weather(rainPercent = 10, currentTemp = 26.0), lastWateredEpochDay = fourDaysAgo, today = today)
        assertThat(suggestion.urgency).isEqualTo(IrrigationUrgency.WATER_SOON)
    }

    @Test
    fun `mild weather watered recently is normal`() {
        val suggestion = IrrigationAdvisor.suggest(weather(rainPercent = 10, currentTemp = 26.0), lastWateredEpochDay = today.toEpochDay(), today = today)
        assertThat(suggestion.urgency).isEqualTo(IrrigationUrgency.NORMAL)
    }
}
