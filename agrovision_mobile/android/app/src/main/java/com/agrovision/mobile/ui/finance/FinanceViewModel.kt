package com.agrovision.mobile.ui.finance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.FarmFinanceRow
import com.agrovision.mobile.data.local.RegionFinanceRow
import com.agrovision.mobile.data.repository.FinanceRepository
import com.agrovision.mobile.data.repository.KpiRepository
import com.agrovision.mobile.data.repository.YearFinance
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FinanceUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val selectedYear: Int = 0,
    val summary: List<YearFinance> = emptyList(),
    val byRegion: List<RegionFinanceRow> = emptyList(),
    val farmRanking: List<FarmFinanceRow> = emptyList(),
)

@HiltViewModel
class FinanceViewModel @Inject constructor(
    private val financeRepository: FinanceRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(FinanceUiState())
    val state: StateFlow<FinanceUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val years = kpiRepository.availableYears()
            val summary = financeRepository.yearlySummary()
            _state.value = _state.value.copy(years = years, summary = summary)
            select(kpiRepository.latestYear())
        }
    }

    fun select(year: Int) = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, selectedYear = year)
        _state.value = _state.value.copy(
            loading = false,
            byRegion = financeRepository.byRegion(year),
            farmRanking = financeRepository.farmProfitability(year),
        )
    }
}
