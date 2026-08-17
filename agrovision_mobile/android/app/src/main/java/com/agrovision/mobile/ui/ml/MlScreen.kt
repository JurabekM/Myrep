package com.agrovision.mobile.ui.ml

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.data.local.CropEntity
import com.agrovision.mobile.data.local.RegionEntity
import com.agrovision.mobile.ui.common.LoadingState
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.common.SimpleDropdown
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun MlScreen(navController: NavHostController, viewModel: MlViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    AppScaffold(navController, "Machine Learning", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) { LoadingState(); return@AppScaffold }
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(18.dp)) {
            ElevatedCard {
                Column(Modifier.padding(14.dp)) {
                    Text("Hosildorlik modeli (mahalliy chiziqli regressiya)", style = MaterialTheme.typography.titleMedium)
                    Text("R² = ${state.status?.rSquared?.let { "%.3f".format(it) } ?: "-"}", style = MaterialTheme.typography.bodyMedium)
                    Spacer(Modifier.height(8.dp))
                    OutlinedButton(onClick = viewModel::retrain) { Text("Modelni qayta o'qitish") }
                }
            }

            var crop by remember { mutableStateOf<CropEntity?>(state.crops.firstOrNull()) }
            var region by remember { mutableStateOf<RegionEntity?>(state.regions.firstOrNull()) }
            var area by remember { mutableFloatStateOf(50f) }
            var precip by remember { mutableFloatStateOf(150f) }
            var tAvg by remember { mutableFloatStateOf(24f) }
            var irrigation by remember { mutableFloatStateOf(350f) }

            SectionTitle("Hosil prognozi")
            ElevatedCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SimpleDropdown("Ekin", state.crops, crop, { it.name }, { crop = it })
                    SimpleDropdown("Viloyat", state.regions, region, { it.name }, { region = it })
                    LabeledSlider("Maydon (ga)", area, 1f, 300f) { area = it }
                    LabeledSlider("Mavsumiy yog'in (mm)", precip, 30f, 500f) { precip = it }
                    LabeledSlider("O'rtacha harorat (°C)", tAvg, 15f, 35f) { tAvg = it }
                    LabeledSlider("Sug'orish (mm)", irrigation, 0f, 900f) { irrigation = it }
                    Button(onClick = {
                        val c = crop; val r = region
                        if (c != null && r != null) viewModel.predictYield(c, r, area.toDouble(), precip.toDouble(), tAvg.toDouble(), irrigation.toDouble())
                    }) { Text("Bashorat qilish") }
                    state.yieldPrediction?.let { Text("Prognoz: $it t/ga", style = MaterialTheme.typography.titleMedium) }
                }
            }

            var humidity by remember { mutableFloatStateOf(65f) }
            var dTemp by remember { mutableFloatStateOf(23f) }
            var ndvi by remember { mutableFloatStateOf(0.5f) }

            SectionTitle("Kasallik xavfi")
            ElevatedCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    LabeledSlider("Namlik (%)", humidity, 10f, 95f) { humidity = it }
                    LabeledSlider("Harorat (°C)", dTemp, 5f, 40f) { dTemp = it }
                    LabeledSlider("NDVI", ndvi, 0.05f, 0.9f) { ndvi = it }
                    Button(onClick = { viewModel.predictDisease(humidity.toDouble(), dTemp.toDouble(), ndvi.toDouble()) }) { Text("Xavfni baholash") }
                    state.diseaseRisk?.let { risk ->
                        LinearProgressIndicator(progress = { (risk / 100).toFloat() }, modifier = Modifier.fillMaxWidth())
                        Text("Xavf darajasi: ${"%.1f".format(risk)}%")
                    }
                }
            }

            var wPrecip by remember { mutableFloatStateOf(150f) }
            var wTemp by remember { mutableFloatStateOf(25f) }
            var wArea by remember { mutableFloatStateOf(50f) }

            SectionTitle("Suv ehtiyoji")
            ElevatedCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    LabeledSlider("Kutilayotgan yog'in (mm)", wPrecip, 30f, 500f) { wPrecip = it }
                    LabeledSlider("O'rtacha harorat (°C)", wTemp, 15f, 35f) { wTemp = it }
                    LabeledSlider("Maydon (ga)", wArea, 1f, 300f) { wArea = it }
                    Button(onClick = { crop?.let { viewModel.predictWater(it, wPrecip.toDouble(), wTemp.toDouble(), wArea.toDouble()) } }) { Text("Hisoblash") }
                    state.waterNeedResult?.let { Text("Jami: ${"%,.0f".format(it)} m³", style = MaterialTheme.typography.titleMedium) }
                }
            }

            SectionTitle("Ekin tavsiyasi")
            ElevatedCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(onClick = { region?.let { viewModel.recommend(it) } }) { Text("Tavsiya olish") }
                    state.recommendations.forEachIndexed { i, rec ->
                        Text("${i + 1}. ${rec.crop} — ishonch ${rec.confidencePercent}%")
                    }
                }
            }
        }
    }
}

@Composable
private fun LabeledSlider(label: String, value: Float, min: Float, max: Float, onChange: (Float) -> Unit) {
    Column {
        Text("$label: ${"%.1f".format(value)}", style = MaterialTheme.typography.bodySmall)
        Slider(value = value, onValueChange = onChange, valueRange = min..max)
    }
}
