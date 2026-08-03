package uz.dehqonkomakchi.app.ui.irrigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.data.repo.IrrigationRepository
import uz.dehqonkomakchi.app.data.repo.IrrigationSuggestion
import uz.dehqonkomakchi.app.data.remote.weather.WeatherSnapshot
import javax.inject.Inject

sealed interface IrrigationUiState {
    data object Loading : IrrigationUiState
    data class Loaded(
        val weather: WeatherSnapshot,
        val suggestion: IrrigationSuggestion,
        val lastWateredEpochDay: Long?,
    ) : IrrigationUiState
    data class NoRegion(val message: String = "") : IrrigationUiState
    data class Error(val message: String) : IrrigationUiState
}

@HiltViewModel
class IrrigationViewModel @Inject constructor(
    private val repository: IrrigationRepository,
    private val userPrefs: UserPrefs,
) : ViewModel() {

    private val _uiState = MutableStateFlow<IrrigationUiState>(IrrigationUiState.Loading)
    val uiState: StateFlow<IrrigationUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = IrrigationUiState.Loading
            val settings = userPrefs.settings.first()
            if (settings.region.isBlank()) {
                _uiState.value = IrrigationUiState.NoRegion()
                return@launch
            }
            try {
                val weather = repository.getWeather(settings.region)
                val suggestion = repository.suggest(weather, settings.lastWateredEpochDay)
                _uiState.value = IrrigationUiState.Loaded(weather, suggestion, settings.lastWateredEpochDay)
            } catch (e: Exception) {
                _uiState.value = IrrigationUiState.Error(e.message ?: "unknown_error")
            }
        }
    }

    fun logWatering() {
        viewModelScope.launch {
            repository.logWatering()
            load()
        }
    }
}
