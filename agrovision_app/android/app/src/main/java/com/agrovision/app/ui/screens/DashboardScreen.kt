package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.core.math.Stats
import com.agrovision.app.data.local.CropAreaRow
import com.agrovision.app.data.local.FarmProductionRow
import com.agrovision.app.data.local.RegionYieldRow
import com.agrovision.app.data.local.SearchRow
import com.agrovision.app.data.local.YearYieldRow
import com.agrovision.app.data.repo.*
import com.agrovision.app.ui.chart.*
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
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
    val forecast: Stats.Forecast? = null,
    val crops: List<CropAreaRow> = emptyList(),
    val regions: List<RegionYieldRow> = emptyList(),
    val alerts: List<Alert> = emptyList(),
    val topFarms: List<FarmProductionRow> = emptyList(),
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val kpiRepository: KpiRepository,
    private val analyticsRepository: AnalyticsRepository,
    private val alertsRepository: AlertsRepository,
    private val geoRepository: GeoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(DashboardUiState())
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val year = kpiRepository.latestYear()
            val (trend, forecast) = analyticsRepository.trendForecast(2)
            _state.value = DashboardUiState(
                loading = false,
                kpi = kpiRepository.compute(year),
                trend = trend,
                forecast = if (trend.size >= 2) forecast else null,
                crops = kpiRepository.cropDistribution(year).take(8),
                regions = kpiRepository.byRegion(year),
                alerts = alertsRepository.generate(),
                topFarms = kpiRepository.topFarms(year, 8),
            )
        }
    }

    suspend fun search(query: String): List<SearchRow> = geoRepository.search(query)
}

@Composable
fun DashboardScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(
        navController = navController,
        title = "Bosh sahifa",
        onLogout = onLogout,
        onSearch = { viewModel.search(it) },
    ) { padding ->
        if (state.loading) {
            LoadingState("Ko'rsatkichlar hisoblanmoqda…")
            return@AppScaffold
        }
        val kpi = state.kpi ?: return@AppScaffold

        ScreenColumn(padding) {
            // ---- KPI kartochkalari (desktop bilan bir xil 9 ta) ----
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                item { KpiCard(Icons.Filled.Landscape, "${Fmt.num(kpi.totalAreaHa, 0)} ga", "Umumiy yer maydoni") }
                item { KpiCard(Icons.Filled.Groups, kpi.farmers.toString(), "Fermerlar") }
                item { KpiCard(Icons.Filled.HomeWork, kpi.farms.toString(), "Fermer xo'jaliklari") }
                item { KpiCard(Icons.Filled.GridOn, kpi.fields.toString(), "Dalalar (konturlar)") }
                item { KpiCard(Icons.Filled.Grass, kpi.crops.toString(), "Ekin turlari") }
            }
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                item {
                    KpiCard(
                        Icons.Filled.Agriculture, "${Fmt.dec(kpi.avgYieldTHa, 2)} t/ga",
                        "O'rtacha hosildorlik (${kpi.year})",
                    )
                }
                item { KpiCard(Icons.Filled.Inventory, "${Fmt.num(kpi.productionT, 0)} t", "Ishlab chiqarish") }
                item {
                    KpiCard(
                        Icons.Filled.Payments, "${Fmt.money(kpi.profit)} so'm",
                        "Sof foyda (ROI ${Fmt.dec(kpi.roiPercent, 1)}%)",
                        tint = if (kpi.profit >= 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    )
                }
                item { KpiCard(Icons.Filled.Eco, Fmt.dec(kpi.avgNdvi, 3), "O'rtacha NDVI (60 kun)") }
                item {
                    KpiCard(
                        Icons.Filled.WaterDrop, "${Fmt.dec(kpi.waterMillionM3, 2)} mln m³",
                        "Sug'orish suvi",
                    )
                }
            }

            // ---- Hosildorlik trendi + prognoz ----
            ChartCard(
                "Hosildorlik trendi va prognoz (t/ga)",
                if (state.forecast != null) "Uzuq chiziq — chiziqli trend prognozi (2 yil)" else null,
            ) {
                if (state.trend.isEmpty()) {
                    EmptyChart("Hosildorlik yozuvlari hali kiritilmagan")
                } else {
                    val history = state.trend.map { it.avgYield }
                    val forecastValues = state.forecast?.point ?: emptyList()
                    val labels = state.trend.map { it.year.toString() } +
                        (1..forecastValues.size).map { (state.trend.last().year + it).toString() }
                    val actual: List<Double?> = history + List(forecastValues.size) { null }
                    val projected: List<Double?> = List((history.size - 1).coerceAtLeast(0)) { null } +
                        listOfNotNull(history.lastOrNull()) + forecastValues
                    LineChart(
                        labels = labels,
                        series = listOfNotNull(
                            LineSeries("Haqiqiy", actual),
                            if (forecastValues.isNotEmpty()) LineSeries("Prognoz", projected, dashed = true) else null,
                        ),
                        band = state.forecast?.let { forecast ->
                            ConfidenceBand(
                                lower = List(history.size) { null } + forecast.lower,
                                upper = List(history.size) { null } + forecast.upper,
                            )
                        },
                        valueFormatter = { Fmt.dec(it, 1) },
                    )
                }
            }

            // ---- Ekinlar taqsimoti ----
            ChartCard("Ekin maydonlari taqsimoti (${kpi.year})") {
                DonutChart(state.crops.map { it.crop to it.area })
            }

            // ---- Viloyatlar bo'yicha ishlab chiqarish ----
            ChartCard("Viloyatlar bo'yicha ishlab chiqarish, ${kpi.year} (t)") {
                HorizontalBarChart(
                    labels = state.regions.map { it.region },
                    values = state.regions.map { it.production },
                )
            }

            // ---- Ogohlantirishlar ----
            SectionTitle("Ogohlantirishlar va tahliliy xulosalar")
            if (state.alerts.isEmpty()) {
                EmptyState("Faol ogohlantirishlar yo'q.")
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    state.alerts.forEach { AlertBanner(it.level, it.title, it.detail) }
                }
            }

            // ---- Eng samarali xo'jaliklar ----
            ChartCard("Eng samarali xo'jaliklar, ${kpi.year}") {
                DataTable(
                    headers = listOf("Xo'jalik", "Hudud", "t/ga"),
                    rows = state.topFarms.map {
                        listOf(it.farm, it.region, Fmt.dec(it.avgYield, 2))
                    },
                    weights = listOf(2f, 1.2f, 0.8f),
                )
            }
        }
    }
}
