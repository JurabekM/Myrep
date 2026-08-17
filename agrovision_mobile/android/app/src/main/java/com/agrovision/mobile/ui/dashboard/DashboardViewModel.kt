package com.agrovision.mobile.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.FarmProductionRow
import com.agrovision.mobile.data.local.YearYieldRow
import com.agrovision.mobile.data.repository.Alert
import com.agrovision.mobile.data.repository.AlertsRepository
import com.agrovision.mobile.data.repository.KpiRepository
import com.agrovision.mobile.data.repository.KpiSummary
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val loading: Boolean = true,
    val kpi: KpiSummary? = null,
    val trend: List<YearYieldRow> = emptyList(),
    val topFarms: List<FarmProductionRow> = emptyList(),
    val alerts: List<Alert> = emptyList(),
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val kpiRepository: KpiRepository,
    private val alertsRepository: AlertsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val year = kpiRepository.latestYear()
            val kpi = kpiRepository.compute(year)
            val trend = kpiRepository.yieldTrend()
            val topFarms = kpiRepository.topFarms(year)
            val alerts = alertsRepository.generate()
            _state.value = DashboardUiState(loading = false, kpi = kpi, trend = trend, topFarms = topFarms, alerts = alerts)
        }
    }
}
