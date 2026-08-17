package com.uzerp.mobile.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.data.repository.DashboardKpis
import com.uzerp.mobile.data.repository.ReportsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class DashboardUiState(val kpis: DashboardKpis? = null, val isLoading: Boolean = true)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val reportsRepository: ReportsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            val kpis = try {
                reportsRepository.dashboardKpis()
            } catch (_: Exception) {
                null
            }
            _state.value = DashboardUiState(kpis = kpis, isLoading = false)
        }
    }
}
