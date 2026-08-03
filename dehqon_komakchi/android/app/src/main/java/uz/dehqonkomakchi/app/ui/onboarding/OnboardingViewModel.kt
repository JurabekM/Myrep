package uz.dehqonkomakchi.app.ui.onboarding

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.work.IrrigationReminderWorker
import java.time.LocalDate
import javax.inject.Inject

data class OnboardingState(
    val step: Int = 0,
    val region: String = "",
    val district: String = "",
    val plantingDateEpochDay: Long = LocalDate.now().toEpochDay(),
    val notificationsEnabled: Boolean = false,
    val complete: Boolean = false,
)

@HiltViewModel
class OnboardingViewModel @Inject constructor(
    private val userPrefs: UserPrefs,
) : ViewModel() {

    private val _state = MutableStateFlow(OnboardingState())
    val state: StateFlow<OnboardingState> = _state.asStateFlow()

    val totalSteps = 5 // welcome, language, region, planting date, notifications

    fun next() {
        if (_state.value.step < totalSteps - 1) {
            _state.update { it.copy(step = it.step + 1) }
        } else {
            finish()
        }
    }

    fun back() {
        if (_state.value.step > 0) _state.update { it.copy(step = it.step - 1) }
    }

    fun setRegion(region: String, district: String) {
        _state.update { it.copy(region = region, district = district) }
    }

    fun setPlantingDate(epochDay: Long) {
        _state.update { it.copy(plantingDateEpochDay = epochDay) }
    }

    fun setNotificationsEnabled(enabled: Boolean) {
        _state.update { it.copy(notificationsEnabled = enabled) }
    }

    private fun finish() {
        viewModelScope.launch {
            val s = _state.value
            userPrefs.setRegion(s.region, s.district)
            userPrefs.setPlantingDate(s.plantingDateEpochDay)
            userPrefs.setNotificationsEnabled(s.notificationsEnabled)
            userPrefs.setOnboardingComplete(true)
            _state.update { it.copy(complete = true) }
        }
    }

    private inline fun MutableStateFlow<OnboardingState>.update(block: (OnboardingState) -> OnboardingState) {
        value = block(value)
    }
}
