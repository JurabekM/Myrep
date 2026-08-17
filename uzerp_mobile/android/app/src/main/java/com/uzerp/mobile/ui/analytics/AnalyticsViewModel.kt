package com.uzerp.mobile.ui.analytics

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.data.local.dao.MonthlySalesRow
import com.uzerp.mobile.data.local.dao.TopProductRow
import com.uzerp.mobile.data.repository.ReportsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import java.time.LocalDate
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AnalyticsUiState(
    val monthlySales: List<MonthlySalesRow> = emptyList(),
    val topProducts: List<TopProductRow> = emptyList(),
    val sixMonthTotal: BigDecimal = BigDecimal.ZERO,
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class AnalyticsViewModel @Inject constructor(
    private val reportsRepository: ReportsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AnalyticsUiState())
    val state: StateFlow<AnalyticsUiState> = _state.asStateFlow()

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null)
            try {
                val monthly = reportsRepository.monthlySales(6)
                val from = LocalDate.now().minusMonths(5).withDayOfMonth(1).toString()
                val to = DateUtils.todayStr()
                val top = reportsRepository.topProducts(from, to, limit = 5)
                _state.value = _state.value.copy(
                    monthlySales = monthly,
                    topProducts = top,
                    sixMonthTotal = monthly.fold(BigDecimal.ZERO) { acc, p -> acc.add(p.total) },
                    isLoading = false,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}
