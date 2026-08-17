package com.agrovision.app.ui.screens

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddPhotoAlternate
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
import com.agrovision.app.data.local.FieldLabelRow
import com.agrovision.app.data.local.NdviPointRow
import com.agrovision.app.data.repo.FieldHealth
import com.agrovision.app.data.repo.GeoRepository
import com.agrovision.app.data.repo.SatelliteRepository
import com.agrovision.app.data.repo.TileRepository
import com.agrovision.app.data.repo.TileSource
import com.agrovision.app.ui.chart.EmptyChart
import com.agrovision.app.ui.chart.LineChart
import com.agrovision.app.ui.chart.LineSeries
import com.agrovision.app.ui.chart.TileMap
import com.agrovision.app.ui.chart.TileOverlay
import com.agrovision.app.ui.theme.MetricHigh
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SatelliteUiState(
    val loading: Boolean = true,
    val processing: Boolean = false,
    val fields: List<FieldLabelRow> = emptyList(),
    val selected: FieldLabelRow? = null,
    val series: List<NdviPointRow> = emptyList(),
    val health: List<FieldHealth> = emptyList(),
    val message: String? = null,
)

@HiltViewModel
class SatelliteViewModel @Inject constructor(
    private val satelliteRepository: SatelliteRepository,
    val tileRepository: TileRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SatelliteUiState())
    val state: StateFlow<SatelliteUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val fields = satelliteRepository.fieldOptions()
            val selected = _state.value.selected?.let { current ->
                fields.firstOrNull { it.id == current.id }
            } ?: fields.firstOrNull()
            _state.value = _state.value.copy(
                loading = false,
                fields = fields,
                selected = selected,
                health = satelliteRepository.fieldHealth(),
                series = selected?.let { satelliteRepository.series(it.id) } ?: emptyList(),
            )
        }
    }

    fun select(field: FieldLabelRow) {
        viewModelScope.launch {
            _state.value = _state.value.copy(selected = field, series = satelliteRepository.series(field.id))
        }
    }

    fun processImage(uri: Uri) {
        val field = _state.value.selected ?: return
        viewModelScope.launch {
            _state.value = _state.value.copy(processing = true, message = null)
            val summary = satelliteRepository.processImage(uri, field.id, Session.current?.username ?: "")
            _state.value = _state.value.copy(processing = false, message = summary)
            refresh()
        }
    }

    fun canImport(): Boolean = Session.can("import_data")
}

@Composable
fun SatelliteScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: SatelliteViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { viewModel.processImage(it) }
    }

    AppScaffold(navController, "Sun'iy yo'ldosh", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }
            if (state.fields.isEmpty()) {
                EmptyState("Hali dala qo'shilmagan. \"Ma'lumotlar\" bo'limida dala qo'shing.")
                return@ScreenColumn
            }

            Dropdown(
                label = "Dala (kontur)",
                options = state.fields,
                selected = state.selected,
                optionLabel = { it.label },
                onSelect = viewModel::select,
            )

            // --- Onlayn sun'iy yo'ldosh xaritasi ---
            var tileSource by remember { mutableStateOf(TileSource.SATELLITE) }
            var tileStatus by remember { mutableStateOf("") }
            val field = state.selected
            ChartCard(
                "Onlayn xarita",
                "Tasvir internetdan yuklanadi va keshlanadi — bir marta ko'rilgan hudud " +
                    "keyinchalik oflayn ham ochiladi.",
            ) {
                ChipSelector(
                    items = TileSource.entries.toList(),
                    selected = tileSource,
                    label = { it.title },
                    onSelect = { tileSource = it },
                )
                if (field != null && (field.lat != 0.0 || field.lon != 0.0)) {
                    TileMap(
                        centerLat = field.lat,
                        centerLon = field.lon,
                        source = tileSource,
                        repository = viewModel.tileRepository,
                        initialZoom = 14,
                        overlays = listOfNotNull(
                            GeoRepository.parsePolygon(field.polygon)
                                .takeIf { it.size >= 3 }
                                ?.let { TileOverlay(field.label, it, MetricHigh) },
                        ),
                        onStatus = { tileStatus = it },
                    )
                } else {
                    EmptyChart("Dala koordinatasi yo'q — xaritani ko'rsatib bo'lmaydi")
                }
                if (tileStatus.isNotBlank()) {
                    Text(
                        tileStatus,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }

            ChartCard("${state.selected?.label ?: ""} — NDVI/EVI dinamikasi") {
                if (state.series.isEmpty()) {
                    EmptyChart("Bu dala uchun indeks yozuvlari yo'q")
                } else {
                    LineChart(
                        labels = state.series.mapIndexed { index, point ->
                            if (index % 4 == 0) Fmt.monthDay(point.epochDay) else ""
                        },
                        series = listOf(
                            LineSeries("NDVI", state.series.map { it.ndvi }),
                            LineSeries("EVI", state.series.map { it.evi }),
                        ),
                        valueFormatter = { Fmt.dec(it, 2) },
                    )
                }
            }

            ChartCard(
                "Dalalar salomatligi (so'nggi NDVI)",
                "A'lo ≥ 0.55 · Yaxshi ≥ 0.40 · O'rtacha ≥ 0.25 · Zaif < 0.25",
            ) {
                DataTable(
                    headers = listOf("Dala", "Xo'jalik", "NDVI", "Holat"),
                    rows = state.health.map {
                        listOf(it.field, it.farm, Fmt.dec(it.ndvi, 2), it.status)
                    },
                    weights = listOf(1.2f, 1.6f, 0.7f, 1f),
                    maxRows = 25,
                )
            }

            if (viewModel.canImport()) {
                ChartCard(
                    "Dron / sun'iy yo'ldosh tasviri",
                    "JPG/PNG tasvirdan yashillik indeksi (ExG) hisoblanib NDVI proksi sifatida yoziladi. " +
                        "Tanlangan dalaga biriktiriladi.",
                ) {
                    Button(
                        onClick = { picker.launch("image/*") },
                        enabled = !state.processing,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        if (state.processing) {
                            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(Icons.Filled.AddPhotoAlternate, contentDescription = null)
                            Spacer(Modifier.width(8.dp))
                            Text("Tasvir tanlash va qayta ishlash")
                        }
                    }
                    state.message?.let { InfoBanner(it) }
                }
            }
        }
    }
}
