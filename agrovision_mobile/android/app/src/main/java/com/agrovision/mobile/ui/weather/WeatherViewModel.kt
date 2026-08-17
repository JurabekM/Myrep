package com.agrovision.mobile.ui.weather

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.WeatherDailyRow
import com.agrovision.mobile.data.local.WeatherMonthlyClimateRow
import com.agrovision.mobile.data.remote.WeatherApi
import com.agrovision.mobile.data.repository.FetchResult
import com.agrovision.mobile.data.repository.WeatherRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DistrictOption(val id: Long, val label: String)

data class WeatherUiState(
    val loading: Boolean = true,
    val districts: List<DistrictOption> = emptyList(),
    val selected: DistrictOption? = null,
    val history: List<WeatherDailyRow> = emptyList(),
    val climate: List<WeatherMonthlyClimateRow> = emptyList(),
    val forecast: List<WeatherApi.DailyPoint>? = null,
    val forecastLoading: Boolean = false,
    val statusMessage: String? = null,
    val hasCachedData: Boolean = false,
)

private val MONTHS_UZ = listOf("Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek")

@HiltViewModel
class WeatherViewModel @Inject constructor(private val weatherRepository: WeatherRepository) : ViewModel() {
    private val _state = MutableStateFlow(WeatherUiState())
    val state: StateFlow<WeatherUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val districts = weatherRepository.districtOptions().map { DistrictOption(it.first, it.second) }
            _state.value = _state.value.copy(districts = districts, selected = districts.firstOrNull(), loading = false)
            districts.firstOrNull()?.let { select(it) }
        }
    }

    fun select(option: DistrictOption) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, selected = option, forecast = null)
            loadLocal(option.id)
            loadForecast(option.id)
        }
    }

    fun refreshFromInternet() {
        val option = _state.value.selected ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true, statusMessage = null)
            val district = weatherRepository.districtEntity(option.id)
            if (district == null) {
                _state.value = _state.value.copy(loading = false, statusMessage = "Tuman topilmadi.")
                return@launch
            }
            val message = when (val result = weatherRepository.refreshHistory(district)) {
                is FetchResult.Success -> "Yangilandi: ${result.daysFetched} kunlik haqiqiy ma'lumot yuklandi (Open-Meteo)."
                FetchResult.AlreadyUpToDate -> "Ma'lumot allaqachon yangi."
                FetchResult.NoInternet -> "Internetga ulanib bo'lmadi. Keshdagi ma'lumot ko'rsatilmoqda."
            }
            loadLocal(option.id)
            loadForecast(option.id)
            _state.value = _state.value.copy(statusMessage = message)
        }
    }

    private suspend fun loadLocal(districtId: Long) {
        val history = weatherRepository.history(districtId, 365)
        val climate = weatherRepository.monthlyClimate(districtId)
        val cached = weatherRepository.hasCachedData(districtId)
        _state.value = _state.value.copy(loading = false, history = history, climate = climate, hasCachedData = cached)
    }

    private fun loadForecast(districtId: Long) {
        viewModelScope.launch {
            _state.value = _state.value.copy(forecastLoading = true)
            val district = weatherRepository.districtEntity(districtId)
            val forecast = district?.let { weatherRepository.fetchLiveForecast(it) }
            _state.value = _state.value.copy(forecastLoading = false, forecast = forecast)
        }
    }

    fun monthLabel(month: Int) = MONTHS_UZ.getOrElse(month - 1) { "$month" }
}
