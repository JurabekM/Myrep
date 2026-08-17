package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.core.math.Stats
import com.agrovision.app.data.local.RegionYieldRow
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

data class AnalyticsUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val year: Int = 0,
    val trend: List<YearYieldRow> = emptyList(),
    val forecast: Stats.Forecast? = null,
    val byRegion: List<RegionYieldRow> = emptyList(),
    val heatmap: HeatmapData = HeatmapData(emptyList(), emptyList(), emptyList()),
    val correlation: CorrelationResult = CorrelationResult(emptyList(), 0.0),
    val seasonality: List<SeasonalityPoint> = emptyList(),
    val segments: List<ClusterRow> = emptyList(),
)

@HiltViewModel
class AnalyticsViewModel @Inject constructor(
    private val kpiRepository: KpiRepository,
    private val analyticsRepository: AnalyticsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AnalyticsUiState())
    val state: StateFlow<AnalyticsUiState> = _state.asStateFlow()

    fun refresh(year: Int? = null) {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val target = year ?: _state.value.year.takeIf { it > 0 } ?: kpiRepository.latestYear()
            val (trend, forecast) = analyticsRepository.trendForecast(3)
            _state.value = AnalyticsUiState(
                loading = false,
                years = kpiRepository.availableYears(),
                year = target,
                trend = trend,
                forecast = if (trend.size >= 2) forecast else null,
                byRegion = kpiRepository.byRegion(target),
                heatmap = analyticsRepository.regionCropHeatmap(target),
                correlation = analyticsRepository.rainfallYieldCorrelation(),
                seasonality = analyticsRepository.priceSeasonality(),
                segments = analyticsRepository.regionSegments(target),
            )
        }
    }
}

@Composable
fun AnalyticsScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: AnalyticsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Analitika", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.years.isNotEmpty()) {
                ChipSelector(state.years, state.year, { it.toString() }) { viewModel.refresh(it) }
            }
            if (state.loading) {
                LoadingState("Tahlil hisoblanmoqda…")
                return@ScreenColumn
            }

            // 1) Trend + 3 yillik prognoz (ishonch oralig'i bilan)
            ChartCard(
                "Hosildorlik: trend, prognoz va ishonch oralig'i (t/ga)",
                "Soyalangan hudud — 95% ishonch oralig'i",
            ) {
                if (state.trend.isEmpty()) {
                    EmptyChart("Hosildorlik ma'lumotlari yo'q")
                } else {
                    val history = state.trend.map { it.avgYield }
                    val forecastValues = state.forecast?.point ?: emptyList()
                    val labels = state.trend.map { it.year.toString() } +
                        (1..forecastValues.size).map { (state.trend.last().year + it).toString() }
                    LineChart(
                        labels = labels,
                        series = listOfNotNull(
                            LineSeries("Haqiqiy", history + List(forecastValues.size) { null }),
                            if (forecastValues.isNotEmpty()) {
                                LineSeries(
                                    "Prognoz",
                                    List((history.size - 1).coerceAtLeast(0)) { null } +
                                        listOfNotNull(history.lastOrNull()) + forecastValues,
                                    dashed = true,
                                )
                            } else null,
                        ),
                        band = state.forecast?.let {
                            ConfidenceBand(
                                lower = List(history.size) { null } + it.lower,
                                upper = List(history.size) { null } + it.upper,
                            )
                        },
                    )
                }
            }

            // 2) Viloyatlar bo'yicha o'rtacha hosildorlik
            ChartCard("Viloyatlar — o'rtacha hosildorlik, ${state.year} (t/ga)") {
                HorizontalBarChart(
                    labels = state.byRegion.map { it.region },
                    values = state.byRegion.map { it.avgYield },
                    valueFormatter = { Fmt.dec(it, 2) },
                )
            }

            // 3) Hudud × ekin issiqlik xaritasi
            ChartCard("Issiqlik xaritasi: hudud × ekin hosildorligi, ${state.year} (t/ga)") {
                HeatmapChart(
                    rowLabels = state.heatmap.rows,
                    columnLabels = state.heatmap.columns,
                    values = state.heatmap.values,
                )
            }

            // 4) Yog'ingarchilik ↔ hosildorlik korrelyatsiyasi
            ChartCard(
                "Yog'ingarchilik ↔ hosildorlik korrelyatsiyasi",
                "Pearson r = ${Fmt.dec(state.correlation.r, 3)} " +
                    "(${state.correlation.points.size} tuman-yil kuzatuvi)",
            ) {
                ScatterChart(
                    points = state.correlation.points.map { it.x to it.y },
                    xName = "Mavsumiy yog'in (mm)",
                    yName = "t/ga",
                )
            }

            // 5) Narxlarning mavsumiyligi
            ChartCard("Narxlarning mavsumiyligi (indeks, o'rtacha = 100)") {
                if (state.seasonality.isEmpty()) {
                    EmptyChart("Bozor narxlari yo'q")
                } else {
                    BarChart(
                        labels = state.seasonality.map { Fmt.monthLabel(it.month) },
                        values = state.seasonality.map { it.index },
                        valueFormatter = { Fmt.dec(it, 0) },
                    )
                }
            }

            // 6) K-Means segmentatsiyasi
            ChartCard(
                "Viloyatlar segmentatsiyasi (K-Means, 3 klaster)",
                "Hosildorlik, ishlab chiqarish va mavsumiy yog'in bo'yicha",
            ) {
                DataTable(
                    headers = listOf("Hudud", "t/ga", "Ishlab chiq. (t)", "Yog'in (mm)", "Segment"),
                    rows = state.segments.map {
                        listOf(
                            it.region, Fmt.dec(it.avgYield, 2), Fmt.num(it.production, 0),
                            Fmt.dec(it.precip, 0), it.segment,
                        )
                    },
                    weights = listOf(1.3f, 0.7f, 1f, 0.9f, 1.6f),
                )
            }
        }
    }
}
