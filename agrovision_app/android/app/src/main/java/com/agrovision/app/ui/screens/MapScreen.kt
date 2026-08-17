package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.data.local.MapFieldRow
import com.agrovision.app.data.local.RegionEntity
import com.agrovision.app.data.repo.GeoRepository
import com.agrovision.app.data.repo.KpiRepository
import com.agrovision.app.ui.chart.*
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MapUiState(
    val loading: Boolean = true,
    val years: List<Int> = emptyList(),
    val year: Int = 0,
    val allFields: List<MapFieldRow> = emptyList(),
    val fields: List<MapFieldRow> = emptyList(),
    val regions: List<RegionEntity> = emptyList(),
    val markers: List<MapRegionMarker> = emptyList(),
    val regionFilter: Long? = null,
    val metric: MapMetric = MapMetric.YIELD,
    val layer: MapLayer = MapLayer.POLYGONS,
    val selected: MapFieldRow? = null,
)

@HiltViewModel
class MapViewModel @Inject constructor(
    private val geoRepository: GeoRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            val year = if (_state.value.year > 0) _state.value.year else kpiRepository.latestYear()
            val fields = geoRepository.mapFields(year)
            val regions = geoRepository.regions()
            val byRegion = kpiRepository.byRegion(year).associateBy { it.region }
            _state.value = _state.value.copy(
                loading = false,
                years = kpiRepository.availableYears(),
                year = year,
                allFields = fields,
                fields = applyFilter(fields, _state.value.regionFilter),
                regions = regions,
                markers = regions.map {
                    MapRegionMarker(it.name, it.lat, it.lon, byRegion[it.name]?.avgYield ?: 0.0)
                },
            )
        }
    }

    fun selectYear(year: Int) {
        _state.value = _state.value.copy(year = year)
        refresh()
    }

    fun selectRegion(regionId: Long?) {
        _state.value = _state.value.copy(
            regionFilter = regionId,
            fields = applyFilter(_state.value.allFields, regionId),
            selected = null,
        )
    }

    fun selectMetric(metric: MapMetric) { _state.value = _state.value.copy(metric = metric) }
    fun selectLayer(layer: MapLayer) { _state.value = _state.value.copy(layer = layer) }
    fun selectField(field: MapFieldRow?) { _state.value = _state.value.copy(selected = field) }

    private fun applyFilter(fields: List<MapFieldRow>, regionId: Long?): List<MapFieldRow> =
        if (regionId == null) fields else fields.filter { it.regionId == regionId }
}

@Composable
fun MapScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: MapViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Xarita", onLogout) { padding ->
        ScreenColumn(padding) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }

            // Filtrlar
            Dropdown(
                label = "Ko'rsatkich",
                options = MapMetric.entries.toList(),
                selected = state.metric,
                optionLabel = { it.title },
                onSelect = viewModel::selectMetric,
            )
            Dropdown(
                label = "Qatlam",
                options = MapLayer.entries.toList(),
                selected = state.layer,
                optionLabel = { it.title },
                onSelect = viewModel::selectLayer,
            )
            if (state.years.isNotEmpty()) {
                Text("Yil", style = MaterialTheme.typography.labelMedium)
                ChipSelector(state.years, state.year, { it.toString() }, onSelect = viewModel::selectYear)
            }
            if (state.regions.isNotEmpty()) {
                Text("Viloyat", style = MaterialTheme.typography.labelMedium)
                Row(Modifier.fillMaxWidth()) {
                    FilterChip(
                        selected = state.regionFilter == null,
                        onClick = { viewModel.selectRegion(null) },
                        label = { Text("Barchasi") },
                    )
                }
                ChipSelector(
                    items = state.regions,
                    selected = state.regions.firstOrNull { it.id == state.regionFilter },
                    label = { it.name },
                    onSelect = { viewModel.selectRegion(it.id) },
                )
            }

            // Dala bo'lmasa ham xarita chiziladi — O'zbekiston ma'muriy chegaralari
            // ilova ichidagi ma'lumotdan olinadi va har doim ko'rinadi.
            if (state.allFields.isEmpty()) {
                InfoBanner(
                    "Hozircha dala qo'shilmagan — xaritada O'zbekiston viloyatlari " +
                        "ko'rsatilmoqda. Dalalarni \"Ma'lumotlar\" yoki \"Import\" bo'limida qo'shing.",
                )
            }

            FieldMap(
                fields = state.fields,
                regions = state.markers,
                metric = state.metric,
                layer = state.layer,
                focusRegion = state.regions.firstOrNull { it.id == state.regionFilter }?.name,
                onFieldSelected = viewModel::selectField,
            )

            // Tanlangan dala haqida ma'lumot
            state.selected?.let { field ->
                ElevatedCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text(field.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.Bold)
                        Text("Xo'jalik: ${field.farm}", style = MaterialTheme.typography.bodySmall)
                        Text("Fermer: ${field.farmer}", style = MaterialTheme.typography.bodySmall)
                        Text("Hudud: ${field.region}, ${field.district}", style = MaterialTheme.typography.bodySmall)
                        Text(
                            "Maydon: ${Fmt.dec(field.areaHa, 1)} ga · Tuproq: ${field.soilType}",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text(
                            "Ekin (${state.year}): ${field.crop} · Hosildorlik: ${Fmt.dec(field.yieldTHa, 2)} t/ga",
                            style = MaterialTheme.typography.bodySmall,
                        )
                        Text("NDVI: ${Fmt.dec(field.ndvi, 2)}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            ChartCard("Dalalar ro'yxati (${state.fields.size})") {
                DataTable(
                    headers = listOf("Dala", "Maydon (ga)", "t/ga", "NDVI"),
                    rows = state.fields.take(40).map {
                        listOf(it.name, Fmt.dec(it.areaHa, 1), Fmt.dec(it.yieldTHa, 2), Fmt.dec(it.ndvi, 2))
                    },
                    maxRows = 40,
                )
            }
        }
    }
}
