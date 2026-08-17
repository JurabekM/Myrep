package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Opacity
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.MethodWaterRow
import com.agrovision.app.data.local.MonthWaterRow
import com.agrovision.app.data.local.RegionWaterRow
import com.agrovision.app.data.repo.CropWaterEfficiency
import com.agrovision.app.data.repo.IrrigationRepository
import com.agrovision.app.data.repo.KpiRepository
import com.agrovision.app.ui.chart.BarChart
import com.agrovision.app.ui.chart.DonutChart
import com.agrovision.app.ui.chart.HorizontalBarChart
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class IrrigationUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val year: Int = 0,
    val totalMln: Double = 0.0,
    val dripShare: Double = 0.0,
    val byRegion: List<RegionWaterRow> = emptyList(),
    val byMethod: List<MethodWaterRow> = emptyList(),
    val monthly: List<MonthWaterRow> = emptyList(),
    val efficiency: List<CropWaterEfficiency> = emptyList(),
)

@HiltViewModel
class IrrigationViewModel @Inject constructor(
    private val irrigationRepository: IrrigationRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(IrrigationUiState())
    val state: StateFlow<IrrigationUiState> = _state.asStateFlow()

    fun refresh(year: Int? = null) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val target = year ?: _state.value.year.takeIf { it > 0 } ?: kpiRepository.latestYear()
            _state.value = IrrigationUiState(
                loading = false,
                years = kpiRepository.availableYears(),
                year = target,
                totalMln = irrigationRepository.totalWaterMln(target),
                dripShare = irrigationRepository.dripSharePercent(target),
                byRegion = irrigationRepository.byRegion(target),
                byMethod = irrigationRepository.byMethod(target),
                monthly = irrigationRepository.monthly(target),
                efficiency = irrigationRepository.efficiencyByCrop(target),
            )
        }
    }
}

@Composable
fun IrrigationScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: IrrigationViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Sug'orish", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.years.isNotEmpty()) {
                ChipSelector(state.years, state.year, { it.toString() }) { viewModel.refresh(it) }
            }
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }

            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                KpiCard(
                    Icons.Filled.WaterDrop,
                    "${Fmt.dec(state.totalMln, 1)} mln m³",
                    "Jami sug'orish suvi, ${state.year}",
                    modifier = Modifier.weight(1f),
                )
                KpiCard(
                    Icons.Filled.Opacity,
                    "${Fmt.dec(state.dripShare, 1)}%",
                    "Tomchilatib sug'orish ulushi",
                    modifier = Modifier.weight(1f),
                )
            }

            ChartCard("Viloyatlar bo'yicha suv sarfi (mln m³)") {
                HorizontalBarChart(
                    labels = state.byRegion.map { it.region },
                    values = state.byRegion.map { it.waterMlnM3 },
                    valueFormatter = { Fmt.dec(it, 2) },
                )
            }

            ChartCard("Sug'orish usullari bo'yicha taqsimot") {
                DonutChart(state.byMethod.map { it.method to it.waterMlnM3 })
            }

            ChartCard("Oylik suv sarfi (mln m³)") {
                BarChart(
                    labels = state.monthly.map { Fmt.monthLabel(it.month) },
                    values = state.monthly.map { it.waterMlnM3 },
                    valueFormatter = { Fmt.dec(it, 1) },
                )
            }

            ChartCard("Suv samaradorligi", "1 tonna mahsulotga sarflangan m³ — kam bo'lsa yaxshi") {
                DataTable(
                    headers = listOf("Ekin", "Ishlab chiq. (t)", "m³/tonna"),
                    rows = state.efficiency.map {
                        listOf(it.crop, Fmt.num(it.productionT, 0), Fmt.num(it.m3PerTonne, 0))
                    },
                    weights = listOf(1.3f, 1.1f, 1f),
                )
            }
        }
    }
}
