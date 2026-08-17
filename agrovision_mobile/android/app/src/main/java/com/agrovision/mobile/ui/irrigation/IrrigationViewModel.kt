package com.agrovision.mobile.ui.irrigation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.CropEfficiencyRow
import com.agrovision.mobile.data.local.MethodWaterRow
import com.agrovision.mobile.data.local.MonthWaterRow
import com.agrovision.mobile.data.local.RegionWaterRow
import com.agrovision.mobile.data.repository.IrrigationRepository
import com.agrovision.mobile.data.repository.KpiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class IrrigationUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val selectedYear: Int = 0,
    val byRegion: List<RegionWaterRow> = emptyList(),
    val byMethod: List<MethodWaterRow> = emptyList(),
    val monthly: List<MonthWaterRow> = emptyList(),
    val efficiency: List<CropEfficiencyRow> = emptyList(),
)

private val MONTHS_UZ = mapOf(4 to "Aprel", 5 to "May", 6 to "Iyun", 7 to "Iyul", 8 to "Avgust")

@HiltViewModel
class IrrigationViewModel @Inject constructor(
    private val irrigationRepository: IrrigationRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(IrrigationUiState())
    val state: StateFlow<IrrigationUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val years = kpiRepository.availableYears()
            _state.value = _state.value.copy(years = years)
            select(kpiRepository.latestYear())
        }
    }

    fun select(year: Int) = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true, selectedYear = year)
        _state.value = _state.value.copy(
            loading = false,
            byRegion = irrigationRepository.usageByRegion(year),
            byMethod = irrigationRepository.usageByMethod(year),
            monthly = irrigationRepository.monthlyUsage(year),
            efficiency = irrigationRepository.efficiencyByCrop(year),
        )
    }

    fun monthLabel(m: Int) = MONTHS_UZ[m] ?: "$m"
}
