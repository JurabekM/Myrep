package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.core.Session
import com.agrovision.app.core.toSafeDouble
import com.agrovision.app.data.local.CropEntity
import com.agrovision.app.data.repo.MarketPriceRow
import com.agrovision.app.data.repo.MarketRepository
import com.agrovision.app.data.repo.PriceForecast
import com.agrovision.app.ui.chart.ConfidenceBand
import com.agrovision.app.ui.chart.EmptyChart
import com.agrovision.app.ui.chart.LineChart
import com.agrovision.app.ui.chart.LineSeries
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MarketUiState(
    val loading: Boolean = true,
    val prices: List<MarketPriceRow> = emptyList(),
    val crops: List<CropEntity> = emptyList(),
    val selectedCrop: CropEntity? = null,
    val forecast: PriceForecast? = null,
    val message: String? = null,
)

@HiltViewModel
class MarketViewModel @Inject constructor(private val marketRepository: MarketRepository) : ViewModel() {
    private val _state = MutableStateFlow(MarketUiState())
    val state: StateFlow<MarketUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val crops = marketRepository.crops()
            val selected = _state.value.selectedCrop ?: crops.firstOrNull()
            _state.value = _state.value.copy(
                loading = false,
                prices = marketRepository.latestPrices(),
                crops = crops,
                selectedCrop = selected,
            )
            selected?.let { loadForecast(it) }
        }
    }

    fun selectCrop(crop: CropEntity) {
        _state.value = _state.value.copy(selectedCrop = crop)
        viewModelScope.launch { loadForecast(crop) }
    }

    private suspend fun loadForecast(crop: CropEntity) {
        _state.value = _state.value.copy(forecast = marketRepository.forecast(crop.id))
    }

    fun addPrice(price: Double, market: String) {
        val crop = _state.value.selectedCrop ?: return
        viewModelScope.launch {
            marketRepository.addPrice(crop.id, price, market)
            _state.value = _state.value.copy(message = "${crop.name} narxi saqlandi.")
            refresh()
        }
    }

    fun canEdit(): Boolean = Session.can("edit_data")
}

@Composable
fun MarketScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: MarketViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Bozor", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }

            ChartCard("So'nggi narxlar", "O'zgarish ustuni — 30 kunlik dinamika") {
                DataTable(
                    headers = listOf("Ekin", "Narx (so'm/kg)", "30 kun"),
                    rows = state.prices.map {
                        listOf(it.crop, Fmt.num(it.price, 0), Fmt.signedPercent(it.change30d))
                    },
                    weights = listOf(1.4f, 1.2f, 0.8f),
                    maxRows = 30,
                )
            }

            if (state.crops.isNotEmpty()) {
                Dropdown(
                    label = "Ekin",
                    options = state.crops,
                    selected = state.selectedCrop,
                    optionLabel = { it.name },
                    onSelect = viewModel::selectCrop,
                )
            }

            val forecast = state.forecast
            ChartCard("${state.selectedCrop?.name ?: "Ekin"} — narx dinamikasi va prognozi (so'm/kg)") {
                if (forecast == null || forecast.history.isEmpty()) {
                    EmptyChart("Bu ekin uchun narx tarixi hali kiritilmagan")
                } else {
                    val history = forecast.history.takeLast(26).map { it.price }
                    val projected = forecast.forecast.point
                    val labels = forecast.history.takeLast(26).map { Fmt.monthDay(it.epochDay) } +
                        (1..projected.size).map { "+$it h" }
                    LineChart(
                        labels = labels,
                        series = listOfNotNull(
                            LineSeries("Narx", history + List(projected.size) { null }),
                            if (projected.isNotEmpty()) {
                                LineSeries(
                                    "Prognoz",
                                    List((history.size - 1).coerceAtLeast(0)) { null } +
                                        listOfNotNull(history.lastOrNull()) + projected,
                                    dashed = true,
                                )
                            } else null,
                        ),
                        band = if (projected.isNotEmpty()) {
                            ConfidenceBand(
                                lower = List(history.size) { null } + forecast.forecast.lower,
                                upper = List(history.size) { null } + forecast.forecast.upper,
                            )
                        } else null,
                        valueFormatter = { Fmt.num(it, 0) },
                    )
                }
            }

            if (viewModel.canEdit()) {
                var price by remember { mutableStateOf("") }
                var market by remember { mutableStateOf("Mahalliy bozor") }
                var error by remember { mutableStateOf<String?>(null) }

                ChartCard("Narx kiritish (qo'lda)") {
                    NumberField("Narx", price, { price = it; error = null }, suffix = "so'm/kg")
                    OutlinedTextField(
                        value = market,
                        onValueChange = { market = it },
                        label = { Text("Bozor nomi") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    error?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
                    Button(
                        onClick = {
                            val value = price.toSafeDouble()
                            if (value == null || value <= 0) {
                                error = "Narxni to'g'ri kiriting (masalan: 5000)."
                            } else {
                                viewModel.addPrice(value, market)
                                price = ""
                            }
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Saqlash") }
                    state.message?.let { InfoBanner(it) }
                }
            }
        }
    }
}
