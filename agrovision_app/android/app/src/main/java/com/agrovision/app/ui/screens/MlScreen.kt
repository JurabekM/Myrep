package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
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
import com.agrovision.app.data.local.CropEntity
import com.agrovision.app.data.local.RegionEntity
import com.agrovision.app.data.repo.CropRecommendation
import com.agrovision.app.data.repo.KpiRepository
import com.agrovision.app.data.repo.MlRepository
import com.agrovision.app.data.repo.ModelInfo
import com.agrovision.app.data.repo.WeatherRepository
import com.agrovision.app.ui.chart.GaugeChart
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MlUiState(
    val loading: Boolean = true,
    val training: Boolean = false,
    val trainingStep: String = "",
    val models: List<ModelInfo> = emptyList(),
    val crops: List<CropEntity> = emptyList(),
    val regions: List<RegionEntity> = emptyList(),
    val yieldPrediction: Double? = null,
    val diseaseRisk: Double? = null,
    val waterNeed: Double? = null,
    val recommendations: List<CropRecommendation> = emptyList(),
    val message: String? = null,
)

@HiltViewModel
class MlViewModel @Inject constructor(
    private val mlRepository: MlRepository,
    private val kpiRepository: KpiRepository,
    private val weatherRepository: WeatherRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MlUiState())
    val state: StateFlow<MlUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            _state.value = _state.value.copy(
                loading = false,
                models = mlRepository.status(),
                crops = mlRepository.crops(),
                regions = mlRepository.regions(),
            )
        }
    }

    fun retrain() {
        viewModelScope.launch {
            _state.value = _state.value.copy(training = true, trainingStep = "Boshlanmoqda", message = null)
            val models = mlRepository.trainAll { step ->
                _state.value = _state.value.copy(trainingStep = step)
            }
            _state.value = _state.value.copy(
                training = false, models = models,
                message = if (models.isEmpty()) {
                    "O'qitish uchun ma'lumot yetarli emas (kamida 20 hosildorlik yozuvi kerak)."
                } else {
                    "${models.size} model qayta o'qitildi."
                },
            )
        }
    }

    fun predictYield(crop: CropEntity, region: RegionEntity, area: Double, precip: Double, tAvg: Double, irrigation: Double) {
        viewModelScope.launch {
            val value = mlRepository.predictYield(
                cropId = crop.id, regionId = region.id, areaHa = area, precip = precip,
                tAvg = tAvg, irrigationMm = irrigation, waterNeedMm = crop.waterNeedMm, fertility = region.fertility,
            )
            _state.value = _state.value.copy(
                yieldPrediction = value,
                message = if (value == null) "Model o'qitilmagan — \"Qayta o'qitish\" tugmasini bosing." else null,
            )
        }
    }

    fun predictDisease(humidity: Double, tAvg: Double, precip: Double, ndvi: Double) {
        viewModelScope.launch {
            val value = mlRepository.predictDiseaseRisk(humidity, tAvg, precip, ndvi)
            _state.value = _state.value.copy(
                diseaseRisk = value?.times(100),
                message = if (value == null) "Model o'qitilmagan." else null,
            )
        }
    }

    fun predictWater(crop: CropEntity, precip: Double, tAvg: Double, area: Double) {
        viewModelScope.launch {
            val perHa = mlRepository.predictWaterNeed(crop.waterNeedMm, precip, tAvg, area)
            _state.value = _state.value.copy(
                waterNeed = perHa?.times(area),
                message = if (perHa == null) "Model o'qitilmagan." else null,
            )
        }
    }

    fun recommend(region: RegionEntity) {
        viewModelScope.launch {
            val year = kpiRepository.latestYear()
            val season = weatherRepository.seasonSummary(region.name, year)
            val result = mlRepository.recommendCrops(
                region.id, season?.precip ?: 150.0, season?.tAvg ?: 24.0, region.fertility,
            )
            _state.value = _state.value.copy(
                recommendations = result,
                message = if (result.isEmpty()) "Tavsiya modeli o'qitilmagan yoki ma'lumot yetarli emas." else null,
            )
        }
    }
}

@Composable
fun MlScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: MlViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Machine Learning", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = state.message) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }

            // Model holati
            if (state.models.isEmpty()) {
                InfoBanner(
                    "Modellar hali o'qitilmagan. Hosildorlik yozuvlari kiritilgandan keyin " +
                        "\"Modellarni qayta o'qitish\" tugmasini bosing.",
                )
            } else {
                LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(state.models.size) { index ->
                        val model = state.models[index]
                        KpiCard(
                            icon = when (model.name) {
                                MlRepository.YIELD -> Icons.Filled.Agriculture
                                MlRepository.DISEASE -> Icons.Filled.Coronavirus
                                MlRepository.WATER -> Icons.Filled.WaterDrop
                                else -> Icons.Filled.Recommend
                            },
                            value = "${model.metricName} ${Fmt.dec(model.metric, 3)}",
                            label = "${model.title}\n${model.algorithm} · ${model.rows} qator",
                        )
                    }
                }
            }

            if (state.training) {
                LoadingState("${state.trainingStep}…")
            } else {
                OutlinedButton(onClick = viewModel::retrain, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.ModelTraining, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Modellarni qayta o'qitish")
                }
            }
            state.message?.let { InfoBanner(it) }

            val crops = state.crops
            val regions = state.regions
            if (crops.isEmpty() || regions.isEmpty()) {
                EmptyState("Ma'lumotnoma bo'sh.")
                return@ScreenColumn
            }

            // ---- 1) Hosil prognozi ----
            var crop by remember(crops) { mutableStateOf(crops.first()) }
            var region by remember(regions) { mutableStateOf(regions.first()) }
            var area by remember { mutableFloatStateOf(50f) }
            var precip by remember { mutableFloatStateOf(150f) }
            var temperature by remember { mutableFloatStateOf(24f) }
            var irrigation by remember { mutableFloatStateOf(350f) }

            ChartCard("Hosil prognozi", "RandomForest regressor · 8 xususiyat") {
                Dropdown("Ekin", crops, crop, { it.name }) { crop = it }
                Dropdown("Viloyat", regions, region, { it.name }) { region = it }
                LabeledSlider("Maydon (ga)", area, 1f..300f, { area = it })
                LabeledSlider("Mavsumiy yog'in (mm)", precip, 30f..500f, { precip = it })
                LabeledSlider("O'rtacha harorat (°C)", temperature, 15f..35f, { temperature = it }, decimals = 1)
                LabeledSlider("Sug'orish (mm)", irrigation, 0f..900f, { irrigation = it })
                Button(
                    onClick = {
                        viewModel.predictYield(
                            crop, region, area.toDouble(), precip.toDouble(),
                            temperature.toDouble(), irrigation.toDouble(),
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Bashorat qilish") }
                state.yieldPrediction?.let {
                    Text(
                        "Prognoz: ${Fmt.dec(it, 2)} t/ga",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }

            // ---- 2) Kasallik xavfi ----
            var humidity by remember { mutableFloatStateOf(65f) }
            var diseaseTemp by remember { mutableFloatStateOf(23f) }
            var diseasePrecip by remember { mutableFloatStateOf(60f) }
            var ndvi by remember { mutableFloatStateOf(0.5f) }

            ChartCard("Kasallik xavfi (zamburug'li)", "GradientBoosting klassifikator") {
                LabeledSlider("Namlik (%)", humidity, 10f..95f, { humidity = it })
                LabeledSlider("Harorat (°C)", diseaseTemp, 5f..40f, { diseaseTemp = it }, decimals = 1)
                LabeledSlider("Oylik yog'in (mm)", diseasePrecip, 0f..200f, { diseasePrecip = it })
                LabeledSlider("NDVI", ndvi, 0.05f..0.9f, { ndvi = it }, decimals = 2)
                Button(
                    onClick = {
                        viewModel.predictDisease(
                            humidity.toDouble(), diseaseTemp.toDouble(),
                            diseasePrecip.toDouble(), ndvi.toDouble(),
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Xavfni baholash") }
                state.diseaseRisk?.let { risk ->
                    Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally) {
                        GaugeChart(risk)
                        Text(
                            when {
                                risk > 60 -> "Profilaktik fungitsid ishlovi tavsiya etiladi."
                                risk > 30 -> "Monitoringni davom ettiring."
                                else -> "Xavf past."
                            },
                            style = MaterialTheme.typography.bodySmall,
                        )
                    }
                }
            }

            // ---- 3) Suv ehtiyoji ----
            var waterPrecip by remember { mutableFloatStateOf(150f) }
            var waterTemp by remember { mutableFloatStateOf(25f) }
            var waterArea by remember { mutableFloatStateOf(50f) }

            ChartCard("Suv ehtiyoji (mavsum)", "RandomForest regressor") {
                Dropdown("Ekin", crops, crop, { it.name }) { crop = it }
                LabeledSlider("Kutilayotgan yog'in (mm)", waterPrecip, 30f..500f, { waterPrecip = it })
                LabeledSlider("O'rtacha harorat (°C)", waterTemp, 15f..35f, { waterTemp = it }, decimals = 1)
                LabeledSlider("Maydon (ga)", waterArea, 1f..300f, { waterArea = it })
                Button(
                    onClick = {
                        viewModel.predictWater(crop, waterPrecip.toDouble(), waterTemp.toDouble(), waterArea.toDouble())
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Hisoblash") }
                state.waterNeed?.let {
                    Text(
                        "Jami: ${Fmt.num(it, 0)} m³ (${Fmt.num(it / waterArea, 0)} m³/ga)",
                        style = MaterialTheme.typography.titleMedium,
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                    )
                }
            }

            // ---- 4) Ekin tavsiyasi ----
            ChartCard("Ekin tavsiyasi", "RandomForest klassifikator · tarixiy foyda asosida") {
                Dropdown("Viloyat", regions, region, { it.name }) { region = it }
                Button(onClick = { viewModel.recommend(region) }, modifier = Modifier.fillMaxWidth()) {
                    Text("Tavsiya olish")
                }
                state.recommendations.forEachIndexed { index, item ->
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Badge { Text("${index + 1}") }
                        Spacer(Modifier.width(10.dp))
                        Text(item.crop, Modifier.weight(1f), fontWeight = FontWeight.SemiBold)
                        Text("${Fmt.dec(item.confidence, 1)}%", style = MaterialTheme.typography.bodySmall)
                    }
                    LinearProgressIndicator(
                        progress = { (item.confidence / 100).toFloat().coerceIn(0f, 1f) },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
        }
    }
}
