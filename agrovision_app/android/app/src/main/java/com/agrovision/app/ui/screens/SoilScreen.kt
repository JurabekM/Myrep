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
import com.agrovision.app.data.local.SoilStatRow
import com.agrovision.app.data.repo.GeoRepository
import com.agrovision.app.ui.chart.DonutChart
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

/** Agronomik baholash — desktop `plugins/soil_analysis.py` ma'lumotlari. */
private val SUITABILITY = listOf(
    Triple("bo'z tuproq", "Bug'doy, paxta, sabzavotlar uchun qulay", 0.85f),
    Triple("o'tloq tuproq", "Sholi va ozuqa ekinlari uchun juda mos", 0.90f),
    Triple("sho'rlangan tuproq", "Meliorativ ishlov talab etiladi; arpa bardoshli", 0.55f),
    Triple("qumloq tuproq", "Poliz ekinlari uchun mos; tez-tez sug'orish kerak", 0.65f),
    Triple("gilli tuproq", "Namlikni yaxshi saqlaydi; drenaj nazorati zarur", 0.75f),
)

@HiltViewModel
class SoilViewModel @Inject constructor(private val geoRepository: GeoRepository) : ViewModel() {
    private val _stats = MutableStateFlow<List<SoilStatRow>>(emptyList())
    val stats: StateFlow<List<SoilStatRow>> = _stats.asStateFlow()

    fun refresh() {
        viewModelScope.launch { _stats.value = geoRepository.soilStats() }
    }
}

@Composable
fun SoilScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: SoilViewModel = hiltViewModel(),
) {
    val stats by viewModel.stats.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Tuproq tahlili", onLogout) { padding ->
        ScreenColumn(padding) {
            if (stats.isEmpty()) {
                EmptyState("Dalalar qo'shilgandan keyin tuproq statistikasi ko'rinadi.")
            } else {
                ChartCard("Tuproq turlari bo'yicha maydon (ga)") {
                    DonutChart(stats.map { it.soilType to it.areaHa })
                }
                ChartCard("Tuproq turlari statistikasi") {
                    DataTable(
                        headers = listOf("Tuproq", "Dalalar", "Maydon (ga)", "O'rtacha hosil"),
                        rows = stats.map {
                            listOf(
                                it.soilType, it.fields.toString(),
                                Fmt.num(it.areaHa, 0), Fmt.dec(it.avgYield, 2),
                            )
                        },
                        weights = listOf(1.6f, 0.8f, 1f, 1f),
                    )
                }
            }

            ChartCard("Agronomik baholash", "Tuproq turining ekinlarga umumiy mosligi") {
                SUITABILITY.forEach { (soil, note, score) ->
                    Column(Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(soil, style = MaterialTheme.typography.bodyMedium)
                            Text(
                                "${(score * 100).toInt()}%",
                                style = MaterialTheme.typography.labelMedium,
                            )
                        }
                        LinearProgressIndicator(
                            progress = { score },
                            modifier = Modifier.fillMaxWidth().padding(vertical = 3.dp),
                        )
                        Text(
                            note,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
            }
        }
    }
}
