package com.agrovision.mobile.ui.satellite

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.FieldHealthRow
import com.agrovision.mobile.data.local.FieldLabelRow
import com.agrovision.mobile.data.local.NdviPointRow
import com.agrovision.mobile.data.repository.GeoRepository
import com.agrovision.mobile.data.repository.SatelliteRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class SatelliteUiState(
    val loading: Boolean = true,
    val health: List<FieldHealthRow> = emptyList(),
    val fields: List<FieldLabelRow> = emptyList(),
    val selectedField: FieldLabelRow? = null,
    val series: List<NdviPointRow> = emptyList(),
)

@HiltViewModel
class SatelliteViewModel @Inject constructor(
    private val satelliteRepository: SatelliteRepository,
    private val geoRepository: GeoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SatelliteUiState())
    val state: StateFlow<SatelliteUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            val health = satelliteRepository.fieldHealth()
            val fields = geoRepository.fieldOptions()
            _state.value = _state.value.copy(loading = false, health = health, fields = fields, selectedField = fields.firstOrNull())
            fields.firstOrNull()?.let { select(it) }
        }
    }

    fun select(field: FieldLabelRow) {
        viewModelScope.launch {
            val series = satelliteRepository.series(field.id)
            _state.value = _state.value.copy(selectedField = field, series = series)
        }
    }

    fun classify(ndvi: Double) = satelliteRepository.classify(ndvi)
}
