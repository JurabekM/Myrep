package com.agrovision.mobile.ui.ml

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.CropEntity
import com.agrovision.mobile.data.local.RegionEntity
import com.agrovision.mobile.data.repository.CropRecommendation
import com.agrovision.mobile.data.repository.GeoRepository
import com.agrovision.mobile.data.repository.KpiRepository
import com.agrovision.mobile.data.repository.MlRepository
import com.agrovision.mobile.data.repository.ModelStatus
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MlUiState(
    val loading: Boolean = true,
    val status: ModelStatus? = null,
    val crops: List<CropEntity> = emptyList(),
    val regions: List<RegionEntity> = emptyList(),
    val yieldPrediction: Double? = null,
    val diseaseRisk: Double? = null,
    val waterNeedResult: Double? = null,
    val recommendations: List<CropRecommendation> = emptyList(),
)

@HiltViewModel
class MlViewModel @Inject constructor(
    private val mlRepository: MlRepository,
    private val geoRepository: GeoRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MlUiState())
    val state: StateFlow<MlUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val status = mlRepository.modelStatus()
            val crops = geoRepository.crops()
            val regions = geoRepository.regions()
            _state.value = _state.value.copy(loading = false, status = status, crops = crops, regions = regions)
        }
    }

    fun retrain() = viewModelScope.launch {
        _state.value = _state.value.copy(loading = true)
        val status = mlRepository.trainYieldModel()
        _state.value = _state.value.copy(loading = false, status = status)
    }

    fun predictYield(crop: CropEntity, region: RegionEntity, areaHa: Double, precip: Double, tAvg: Double, irrigationMm: Double) {
        viewModelScope.launch {
            val value = mlRepository.predictYield(areaHa, crop.waterNeedMm, region.fertility, precip, tAvg, irrigationMm)
            _state.value = _state.value.copy(yieldPrediction = value)
        }
    }

    fun predictDisease(humidity: Double, tAvg: Double, ndvi: Double) {
        val risk = mlRepository.diseaseRisk(humidity, tAvg, ndvi) * 100
        _state.value = _state.value.copy(diseaseRisk = risk)
    }

    fun predictWater(crop: CropEntity, precip: Double, tAvg: Double, areaHa: Double) {
        val value = mlRepository.waterNeed(crop.waterNeedMm, precip, tAvg, areaHa)
        _state.value = _state.value.copy(waterNeedResult = value)
    }

    fun recommend(region: RegionEntity) {
        viewModelScope.launch {
            val year = kpiRepository.latestYear()
            val recs = mlRepository.recommendCrops(region.name, year)
            _state.value = _state.value.copy(recommendations = recs)
        }
    }
}
