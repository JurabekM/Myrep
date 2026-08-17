package com.agrovision.mobile.ui.map

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.FieldEntity
import com.agrovision.mobile.data.local.RegionEntity
import com.agrovision.mobile.data.repository.GeoRepository
import com.agrovision.mobile.data.repository.KpiRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class RegionPoint(val region: RegionEntity, val avgYield: Double, val production: Double)

data class MapUiState(
    val loading: Boolean = true,
    val points: List<RegionPoint> = emptyList(),
    val selectedRegionId: Long? = null,
    val fields: List<FieldEntity> = emptyList(),
    val farmNameById: Map<Long, String> = emptyMap(),
)

@HiltViewModel
class MapViewModel @Inject constructor(
    private val geoRepository: GeoRepository,
    private val kpiRepository: KpiRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MapUiState())
    val state: StateFlow<MapUiState> = _state.asStateFlow()

    private var allFields: List<FieldEntity> = emptyList()
    private var farmDistrict: Map<Long, Long> = emptyMap()
    private var districtRegion: Map<Long, Long> = emptyMap()

    fun refresh() {
        viewModelScope.launch {
            val year = kpiRepository.latestYear()
            val regions = geoRepository.regions()
            val byRegion = kpiRepository.byRegion(year).associateBy { it.region }
            val points = regions.map { region ->
                val row = byRegion[region.name]
                RegionPoint(region, row?.avgYield ?: 0.0, row?.production ?: 0.0)
            }
            allFields = geoRepository.fields()
            val farms = geoRepository.farms()
            farmDistrict = farms.associate { it.id to it.districtId }
            val districts = geoRepository.districts()
            districtRegion = districts.associate { it.id to it.regionId }
            val farmNames = farms.associate { it.id to it.name }
            _state.value = MapUiState(loading = false, points = points, fields = allFields.take(30), farmNameById = farmNames)
        }
    }

    fun selectRegion(regionId: Long?) {
        val filtered = if (regionId == null) allFields.take(30) else {
            allFields.filter { field ->
                val farmId = field.farmId
                val districtId = farmDistrict[farmId]
                districtRegion[districtId] == regionId
            }.take(30)
        }
        _state.value = _state.value.copy(selectedRegionId = regionId, fields = filtered)
    }
}
