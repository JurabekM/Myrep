package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.data.repo.ExportDataset
import com.agrovision.app.data.repo.KpiRepository
import com.agrovision.app.data.repo.ReportRepository
import com.agrovision.app.data.repo.TableData
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ReportsUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val year: Int = 0,
    val busy: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false,
    val preview: TableData? = null,
    val dataset: ExportDataset = ExportDataset.YIELDS,
    val format: String = "csv",
)

@HiltViewModel
class ReportsViewModel @Inject constructor(
    private val reportRepository: ReportRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ReportsUiState())
    val state: StateFlow<ReportsUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val years = kpiRepository.availableYears()
            _state.value = _state.value.copy(
                loading = false,
                years = years,
                year = _state.value.year.takeIf { it > 0 } ?: kpiRepository.latestYear(),
            )
            loadPreview()
        }
    }

    fun selectYear(year: Int) { _state.value = _state.value.copy(year = year) }
    fun selectFormat(format: String) { _state.value = _state.value.copy(format = format) }

    fun selectDataset(dataset: ExportDataset) {
        _state.value = _state.value.copy(dataset = dataset)
        viewModelScope.launch { loadPreview() }
    }

    private suspend fun loadPreview() {
        _state.value = _state.value.copy(preview = reportRepository.datasetTable(_state.value.dataset))
    }

    private fun run(block: suspend () -> String) {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true, message = null)
            val result = runCatching { block() }
            _state.value = _state.value.copy(
                busy = false,
                message = result.getOrElse { "Xato: ${it.message ?: "noma'lum"}" }
                    .let { name -> if (result.isSuccess) "Tayyor: $name (Downloads/AgroVision)" else name },
                isError = result.isFailure,
            )
        }
    }

    fun exportPdf() = run { reportRepository.exportPdf(_state.value.year) }
    fun exportHtml() = run { reportRepository.exportHtml(_state.value.year) }
    fun exportGeoJson() = run { reportRepository.exportGeoJson() }
    fun exportDataset() = run { reportRepository.exportDataset(_state.value.dataset, _state.value.format) }
}

@Composable
fun ReportsScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: ReportsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Hisobotlar", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = state.message) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }

            Text(
                "Barcha fayllar qurilma xotirasidagi Downloads/AgroVision papkasiga yoziladi.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            state.message?.let { InfoBanner(it, state.isError) }
            if (state.busy) LinearProgressIndicator(Modifier.fillMaxWidth())

            // ---- KPI hisoboti ----
            ChartCard("Yakuniy KPI hisoboti") {
                if (state.years.isNotEmpty()) {
                    ChipSelector(state.years, state.year, { it.toString() }, onSelect = viewModel::selectYear)
                }
                Text("Tanlangan yil: ${state.year}", style = MaterialTheme.typography.bodyMedium)
                Button(onClick = viewModel::exportPdf, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.PictureAsPdf, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("PDF hisobot")
                }
                OutlinedButton(onClick = viewModel::exportHtml, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.Language, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("HTML hisobot")
                }
            }

            // ---- Dataset eksporti ----
            ChartCard("Ma'lumotlar eksporti") {
                Dropdown(
                    label = "Ma'lumotlar to'plami",
                    options = ExportDataset.entries.toList(),
                    selected = state.dataset,
                    optionLabel = { it.title },
                    onSelect = viewModel::selectDataset,
                )
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    listOf("csv", "json").forEach { format ->
                        FilterChip(
                            selected = state.format == format,
                            onClick = { viewModel.selectFormat(format) },
                            label = { Text(format.uppercase()) },
                        )
                    }
                }
                Button(onClick = viewModel::exportDataset, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.Download, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Eksport qilish")
                }
                OutlinedButton(onClick = viewModel::exportGeoJson, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.Public, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("GeoJSON (dala poligonlari)")
                }
            }

            // ---- Ko'rib chiqish ----
            state.preview?.let { preview ->
                ChartCard("${preview.title} — ${preview.rows.size} qator") {
                    DataTable(
                        headers = preview.headers.take(4),
                        rows = preview.rows.map { it.take(4) },
                        maxRows = 10,
                    )
                }
            }
        }
    }
}
