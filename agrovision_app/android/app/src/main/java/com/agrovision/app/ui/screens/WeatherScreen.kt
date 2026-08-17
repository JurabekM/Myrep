package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.DistrictEntity
import com.agrovision.app.data.local.MonthClimateRow
import com.agrovision.app.data.local.WeatherDailyRow
import com.agrovision.app.data.remote.WeatherApi
import com.agrovision.app.data.repo.SyncResult
import com.agrovision.app.data.repo.WeatherRepository
import com.agrovision.app.ui.chart.BarChart
import com.agrovision.app.ui.chart.LineChart
import com.agrovision.app.ui.chart.LineSeries
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

data class WeatherUiState(
    val loading: Boolean = true,
    val syncing: Boolean = false,
    val districts: List<Pair<DistrictEntity, String>> = emptyList(),
    val selected: DistrictEntity? = null,
    val history: List<WeatherDailyRow> = emptyList(),
    val climate: List<MonthClimateRow> = emptyList(),
    val forecast: List<WeatherApi.DailyPoint>? = null,
    val message: String? = null,
    val provider: String = "open-meteo",
)

@HiltViewModel
class WeatherViewModel @Inject constructor(private val weatherRepository: WeatherRepository) : ViewModel() {
    private val _state = MutableStateFlow(WeatherUiState())
    val state: StateFlow<WeatherUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val districts = weatherRepository.districtOptions()
            val current = _state.value.selected ?: districts.firstOrNull()?.first
            _state.value = _state.value.copy(
                loading = false, districts = districts, selected = current,
                provider = weatherRepository.provider(),
            )
            current?.let { load(it) }
        }
    }

    fun select(district: DistrictEntity) {
        _state.value = _state.value.copy(selected = district, forecast = null, message = null)
        viewModelScope.launch { load(district) }
    }

    private suspend fun load(district: DistrictEntity) {
        _state.value = _state.value.copy(
            history = weatherRepository.history(district.id, 365),
            climate = weatherRepository.monthlyClimate(district.id),
        )
        // Jonli prognoz — internet bo'lsa
        _state.value = _state.value.copy(forecast = weatherRepository.forecast(district))
    }

    fun sync() {
        val district = _state.value.selected ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(syncing = true, message = null)
            val message = when (val result = weatherRepository.syncHistory(district)) {
                is SyncResult.Success -> "Yangilandi: ${result.days} kunlik haqiqiy ma'lumot yuklandi (${result.provider})."
                SyncResult.UpToDate -> "Ma'lumot allaqachon yangi."
                SyncResult.Offline -> "Internet mavjud emas — keshdagi ma'lumot ko'rsatilmoqda."
                SyncResult.Failed -> "Provayderdan javob olinmadi. Keyinroq urinib ko'ring."
            }
            load(district)
            _state.value = _state.value.copy(syncing = false, message = message)
        }
    }
}

@Composable
fun WeatherScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: WeatherViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Ob-havo", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }
            if (state.districts.isEmpty()) {
                EmptyState("Tumanlar ma'lumotnomasi bo'sh.")
                return@ScreenColumn
            }

            Dropdown(
                label = "Tuman",
                options = state.districts,
                selected = state.districts.firstOrNull { it.first.id == state.selected?.id },
                optionLabel = { it.second },
                onSelect = { viewModel.select(it.first) },
            )

            ChartCard(
                "Ma'lumot manbasi",
                "Provayder: ${state.provider}. Tarixiy ma'lumot Open-Meteo (ERA5 arxiv) yoki " +
                    "NASA POWER dan yuklanadi va qurilmada keshlanadi.",
            ) {
                Button(
                    onClick = viewModel::sync,
                    enabled = !state.syncing,
                    modifier = Modifier.fillMaxWidth(),
                ) {
                    if (state.syncing) {
                        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    } else {
                        Icon(Icons.Filled.CloudDownload, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Internetdan yangilash")
                    }
                }
                state.message?.let { InfoBanner(it) }
            }

            // 7 kunlik prognoz
            SectionTitle("7 kunlik prognoz")
            val forecast = state.forecast
            if (forecast.isNullOrEmpty()) {
                EmptyState("Jonli prognoz mavjud emas (internet ulanishini tekshiring).")
            } else {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(forecast) { day ->
                        ElevatedCard {
                            Column(
                                Modifier.padding(10.dp).widthIn(min = 76.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                            ) {
                                Text(
                                    Fmt.monthDay(day.date.toEpochDay()),
                                    style = MaterialTheme.typography.labelSmall,
                                )
                                Text(
                                    "${day.tMax.toInt()}°/${day.tMin.toInt()}°",
                                    style = MaterialTheme.typography.titleSmall,
                                    fontWeight = FontWeight.Bold,
                                )
                                Text(
                                    "${Fmt.dec(day.precipitationMm, 1)} mm",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.primary,
                                )
                            }
                        }
                    }
                }
            }

            if (state.history.isEmpty()) {
                EmptyState(
                    "Bu tuman uchun tarixiy ma'lumot yo'q. \"Internetdan yangilash\" tugmasini bosing " +
                        "yoki namuna ma'lumotlarni yuklang.",
                )
                return@ScreenColumn
            }

            // Oylik agregatsiya
            val monthly = state.history
                .groupBy { Fmt.yearMonth(it.epochDay) }
                .toSortedMap()
            val labels = monthly.keys.toList()

            ChartCard("Harorat, so'nggi 12 oy (°C)") {
                LineChart(
                    labels = labels.map { it.takeLast(2) },
                    series = listOf(
                        LineSeries("Maks", monthly.values.map { rows -> rows.map { it.tMax }.average() }),
                        LineSeries("Min", monthly.values.map { rows -> rows.map { it.tMin }.average() }),
                    ),
                )
            }

            ChartCard("Oylik yog'ingarchilik (mm)") {
                BarChart(
                    labels = labels.map { it.takeLast(2) },
                    values = monthly.values.map { rows -> rows.sumOf { it.precipitationMm } },
                    valueFormatter = { Fmt.dec(it, 0) },
                )
            }

            if (state.climate.isNotEmpty()) {
                ChartCard("Ko'p yillik iqlim profili — harorat (°C)") {
                    LineChart(
                        labels = state.climate.map { Fmt.monthLabel(it.month) },
                        series = listOf(
                            LineSeries("Maks", state.climate.map { it.tMax }),
                            LineSeries("Min", state.climate.map { it.tMin }),
                        ),
                    )
                }
                ChartCard("Ko'p yillik o'rtacha oylik yog'in (mm)") {
                    BarChart(
                        labels = state.climate.map { Fmt.monthLabel(it.month) },
                        values = state.climate.map { it.precip },
                        valueFormatter = { Fmt.dec(it, 0) },
                    )
                }
            }
        }
    }
}
