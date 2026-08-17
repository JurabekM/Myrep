package com.agrovision.mobile.ui.reports

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.repository.KpiRepository
import com.agrovision.mobile.data.repository.ReportRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ReportsUiState(
    val years: List<Int> = emptyList(),
    val selectedYear: Int = 0,
    val lastMessage: String? = null,
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val kpiRepository: KpiRepository,
    private val reportRepository: ReportRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val years = kpiRepository.availableYears()
            _state.value = _state.value.copy(years = years, selectedYear = kpiRepository.latestYear())
        }
    }

    fun selectYear(year: Int) { _state.value = _state.value.copy(selectedYear = year) }

    fun exportCsv() {
        viewModelScope.launch {
            val year = _state.value.selectedYear
            val trend = kpiRepository.yieldTrend()
            val regionRows = kpiRepository.byRegion(year)
            val fileName = reportRepository.exportCsv(
                "agrovision_hosildorlik_$year",
                listOf("Yil", "O'rtacha_hosildorlik_tga", "Ishlab_chiqarish_t"),
                trend.map { listOf(it.year.toString(), "${it.avgYield}", "${it.production}") },
            )
            _state.value = _state.value.copy(lastMessage = "CSV eksport tayyor: $fileName (Downloads/AgroVision)")
        }
    }

    fun exportPdf() {
        viewModelScope.launch {
            val year = _state.value.selectedYear
            val kpi = kpiRepository.compute(year)
            val topFarms = kpiRepository.topFarms(year)
            val fileName = reportRepository.exportKpiPdf(
                year,
                listOf(
                    "Yer maydoni" to "${kpi.totalAreaHa} ga",
                    "O'rtacha hosildorlik" to "${kpi.avgYieldTHa} t/ga",
                    "Ishlab chiqarish" to "${kpi.productionT} t",
                    "Sof foyda" to "${kpi.profit} so'm (ROI ${kpi.roiPercent}%)",
                    "O'rtacha NDVI" to "${kpi.avgNdvi}",
                ),
                "Eng samarali xo'jaliklar",
                topFarms.map { listOf(it.farm, it.region, "${it.avgYield} t/ga") },
            )
            _state.value = _state.value.copy(lastMessage = "PDF hisobot tayyor: $fileName (Downloads/AgroVision)")
        }
    }
}
