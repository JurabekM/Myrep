package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.CreditRow
import com.agrovision.app.data.repo.EntityFinance
import com.agrovision.app.data.repo.FinanceRepository
import com.agrovision.app.data.repo.KpiRepository
import com.agrovision.app.data.repo.YearFinance
import com.agrovision.app.ui.chart.LineChart
import com.agrovision.app.ui.chart.LineSeries
import com.agrovision.app.ui.chart.HorizontalBarChart
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class FinanceUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val year: Int = 0,
    val summary: List<YearFinance> = emptyList(),
    val byRegion: List<EntityFinance> = emptyList(),
    val farmRanking: List<EntityFinance> = emptyList(),
    val credits: List<CreditRow> = emptyList(),
)

@HiltViewModel
class FinanceViewModel @Inject constructor(
    private val financeRepository: FinanceRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(FinanceUiState())
    val state: StateFlow<FinanceUiState> = _state.asStateFlow()

    fun refresh(year: Int? = null) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val target = year ?: _state.value.year.takeIf { it > 0 } ?: kpiRepository.latestYear()
            _state.value = FinanceUiState(
                loading = false,
                years = kpiRepository.availableYears(),
                year = target,
                summary = financeRepository.yearlySummary(),
                byRegion = financeRepository.byRegion(target),
                farmRanking = financeRepository.farmRanking(target),
                credits = financeRepository.creditsAndSubsidies(target),
            )
        }
    }
}

@Composable
fun FinanceScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: FinanceViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Moliya", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.years.isNotEmpty()) {
                ChipSelector(state.years, state.year, { it.toString() }) { viewModel.refresh(it) }
            }
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }
            if (state.summary.isEmpty()) {
                EmptyState("Moliya yozuvlari hali kiritilmagan.")
                return@ScreenColumn
            }

            val record = state.summary.firstOrNull { it.year == state.year }
            if (record != null) {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    item { KpiCard(Icons.Filled.TrendingUp, "${Fmt.money(record.income)} so'm", "Daromad, ${state.year}") }
                    item { KpiCard(Icons.Filled.TrendingDown, "${Fmt.money(record.expense)} so'm", "Xarajat") }
                    item {
                        KpiCard(
                            Icons.Filled.Savings, "${Fmt.money(record.profit)} so'm", "Sof foyda",
                            tint = if (record.profit >= 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                        )
                    }
                    item { KpiCard(Icons.Filled.Percent, "${Fmt.dec(record.roi, 1)}%", "ROI") }
                    item { KpiCard(Icons.Filled.AccountBalance, "${Fmt.money(record.credit)} so'm", "Kreditlar") }
                    item { KpiCard(Icons.Filled.VolunteerActivism, "${Fmt.money(record.subsidy)} so'm", "Subsidiyalar") }
                }
            }

            ChartCard("Daromad, xarajat va foyda dinamikasi (mlrd so'm)") {
                LineChart(
                    labels = state.summary.map { it.year.toString() },
                    series = listOf(
                        LineSeries("Daromad", state.summary.map { it.income / 1e9 }),
                        LineSeries("Xarajat", state.summary.map { it.expense / 1e9 }),
                        LineSeries("Foyda", state.summary.map { it.profit / 1e9 }),
                    ),
                    valueFormatter = { Fmt.dec(it, 1) },
                )
            }

            ChartCard("ROI trendi (%)") {
                LineChart(
                    labels = state.summary.map { it.year.toString() },
                    series = listOf(LineSeries("ROI", state.summary.map { it.roi })),
                    valueFormatter = { Fmt.dec(it, 0) },
                )
            }

            ChartCard("Viloyatlar bo'yicha sof foyda, ${state.year} (mln so'm)") {
                HorizontalBarChart(
                    labels = state.byRegion.map { it.name },
                    values = state.byRegion.map { it.profit / 1e6 },
                    valueFormatter = { Fmt.dec(it, 0) },
                )
            }

            ChartCard("Xo'jaliklar reytingi, ${state.year} (mln so'm)") {
                DataTable(
                    headers = listOf("Xo'jalik", "Daromad", "Foyda", "ROI"),
                    rows = state.farmRanking.map {
                        listOf(
                            it.name, Fmt.num(it.income / 1e6, 0),
                            Fmt.num(it.profit / 1e6, 0), "${Fmt.dec(it.roi, 0)}%",
                        )
                    },
                    weights = listOf(2f, 1f, 1f, 0.8f),
                )
            }

            ChartCard("Kredit va subsidiyalar, ${state.year} (mln so'm)") {
                DataTable(
                    headers = listOf("Xo'jalik", "Turi", "Summa"),
                    rows = state.credits.map {
                        listOf(it.farm, if (it.category == "credit") "Kredit" else "Subsidiya", Fmt.num(it.amount / 1e6, 1))
                    },
                    weights = listOf(2f, 1f, 1f),
                )
            }
        }
    }
}
