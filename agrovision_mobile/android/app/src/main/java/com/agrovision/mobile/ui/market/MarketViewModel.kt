package com.agrovision.mobile.ui.market

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.core.Session
import com.agrovision.mobile.data.local.CropEntity
import com.agrovision.mobile.data.local.LatestPriceRow
import com.agrovision.mobile.data.repository.GeoRepository
import com.agrovision.mobile.data.repository.MarketRepository
import com.agrovision.mobile.data.repository.PriceForecast
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

data class MarketUiState(
    val loading: Boolean = true,
    val latest: List<LatestPriceRow> = emptyList(),
    val crops: List<CropEntity> = emptyList(),
    val selectedCrop: CropEntity? = null,
    val forecast: PriceForecast? = null,
)

@HiltViewModel
class MarketViewModel @Inject constructor(
    private val marketRepository: MarketRepository,
    private val geoRepository: GeoRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(MarketUiState())
    val state: StateFlow<MarketUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val latest = marketRepository.latestPrices()
            val crops = geoRepository.crops()
            _state.value = _state.value.copy(loading = false, latest = latest, crops = crops, selectedCrop = crops.firstOrNull())
            crops.firstOrNull()?.let { selectCrop(it) }
        }
    }

    fun selectCrop(crop: CropEntity) {
        viewModelScope.launch {
            val forecast = marketRepository.forecast(crop.id)
            _state.value = _state.value.copy(selectedCrop = crop, forecast = forecast)
        }
    }

    fun addPrice(price: Double, marketName: String) {
        val crop = _state.value.selectedCrop ?: return
        viewModelScope.launch {
            marketRepository.addPrice(crop.id, price, marketName)
            _state.value = _state.value.copy(latest = marketRepository.latestPrices())
            selectCrop(crop)
        }
    }

    fun canEdit(): Boolean = com.agrovision.mobile.core.Rbac.has(Session.current?.role, "edit_data")
}
