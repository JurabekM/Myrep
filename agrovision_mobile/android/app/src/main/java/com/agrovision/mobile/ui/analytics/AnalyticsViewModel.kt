package com.agrovision.mobile.ui.analytics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.core.AnalyticsMath
import com.agrovision.mobile.data.local.RegionCropYieldRow
import com.agrovision.mobile.data.local.RegionYieldRow
import com.agrovision.mobile.data.local.YearYieldRow
import com.agrovision.mobile.data.repository.KpiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AnalyticsUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val selectedYear: Int = 0,
    val trend: List<YearYieldRow> = emptyList(),
    val forecastLabels: List<String> = emptyList(),
    val forecastActual: List<Double?> = emptyList(),
    val forecastLine: List<Double?> = emptyList(),
    val byRegion: List<RegionYieldRow> = emptyList(),
    val matrix: List<RegionCropYieldRow> = emptyList(),
)

@HiltViewModel
class AnalyticsViewModel @Inject constructor(private val kpiRepository: KpiRepository) : ViewModel() {
    private val _state = MutableStateFlow(AnalyticsUiState())
    val state: StateFlow<AnalyticsUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val years = kpiRepository.availableYears()
            val latest = kpiRepository.latestYear()
            _state.value = _state.value.copy(years = years, selectedYear = latest)
            loadYear(latest)
        }
    }

    fun selectYear(year: Int) = viewModelScope.launch { loadYear(year) }

    private suspend fun loadYear(year: Int) {
        _state.value = _state.value.copy(loading = true, selectedYear = year)
        val trend = kpiRepository.yieldTrend()
        val byRegion = kpiRepository.byRegion(year)
        val matrix = kpiRepository.regionCropMatrix(year)

        if (trend.isEmpty()) {
            _state.value = _state.value.copy(
                loading = false, trend = emptyList(), forecastLabels = emptyList(),
                forecastActual = emptyList(), forecastLine = emptyList(), byRegion = byRegion, matrix = matrix,
            )
            return
        }

        val values = trend.map { it.avgYield }
        val (forecast, _, _) = AnalyticsMath.linearForecast(values, 2)
        val labels = trend.map { it.year.toString() } + listOf(trend.last().year + 1, trend.last().year + 2).map { it.toString() }
        val actual: List<Double?> = values.map { it } + listOf(null, null)
        val forecastLine: List<Double?> = List(values.size - 1) { null } + listOf(values.last()) + forecast

        _state.value = _state.value.copy(
            loading = false, trend = trend, forecastLabels = labels, forecastActual = actual,
            forecastLine = forecastLine, byRegion = byRegion, matrix = matrix,
        )
    }
}
