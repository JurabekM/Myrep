package com.agrovision.mobile.ui.records

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.*
import com.agrovision.mobile.data.repository.GeoRepository
import com.agrovision.mobile.data.repository.RecordsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.time.LocalDate
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

val IRRIGATION_METHODS = listOf("egat", "tomchilatib", "yomg'irlatib", "bostirib")
val FINANCE_CATEGORIES = listOf("income" to "Daromad", "expense" to "Xarajat", "credit" to "Kredit", "subsidy" to "Subsidiya")

data class RecordsUiState(
    val loading: Boolean = true,
    val districts: List<DistrictEntity> = emptyList(),
    val farmerEntities: List<FarmerEntity> = emptyList(),
    val farmEntities: List<FarmEntity> = emptyList(),
    val fieldEntities: List<FieldEntity> = emptyList(),
    val crops: List<CropEntity> = emptyList(),
    val farmers: List<FarmerListRow> = emptyList(),
    val farms: List<FarmListRow> = emptyList(),
    val fields: List<FieldListRow> = emptyList(),
    val yields: List<YieldListRow> = emptyList(),
    val irrigation: List<IrrigationListRow> = emptyList(),
    val finance: List<FinanceListRow> = emptyList(),
    val satellite: List<SatelliteListRow> = emptyList(),
    val message: String? = null,
)

@HiltViewModel
class RecordsViewModel @Inject constructor(
    private val geoRepository: GeoRepository,
    private val recordsRepository: RecordsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(RecordsUiState())
    val state: StateFlow<RecordsUiState> = _state.asStateFlow()

    init { refreshAll() }

    fun refreshAll() {
        viewModelScope.launch {
            _state.value = _state.value.copy(loading = true)
            _state.value = RecordsUiState(
                loading = false,
                districts = geoRepository.districts(),
                farmerEntities = geoRepository.farmers(),
                farmEntities = geoRepository.farms(),
                fieldEntities = geoRepository.fields(),
                crops = geoRepository.crops(),
                farmers = geoRepository.farmerList(),
                farms = geoRepository.farmList(),
                fields = geoRepository.fieldList(),
                yields = recordsRepository.yieldList(),
                irrigation = recordsRepository.irrigationList(),
                finance = recordsRepository.financeList(),
                satellite = recordsRepository.satelliteList(),
            )
        }
    }

    fun addFarmer(name: String, phone: String, districtId: Long?) {
        if (name.isBlank() || districtId == null) {
            _state.value = _state.value.copy(message = "Ism va tumanni to'ldiring.")
            return
        }
        viewModelScope.launch {
            geoRepository.createFarmer(name.trim(), phone.trim(), districtId)
            _state.value = _state.value.copy(message = "Fermer qo'shildi.")
            refreshAll()
        }
    }

    fun addFarm(name: String, farmerId: Long?) {
        val farmer = _state.value.farmerEntities.firstOrNull { it.id == farmerId }
        if (name.isBlank() || farmer == null) {
            _state.value = _state.value.copy(message = "Nom va fermerni tanlang.")
            return
        }
        viewModelScope.launch {
            geoRepository.createFarm(name.trim(), farmer.id, farmer.districtId)
            _state.value = _state.value.copy(message = "Xo'jalik qo'shildi.")
            refreshAll()
        }
    }

    fun addField(name: String, farmId: Long?, areaHa: Double?, soilType: String) {
        val farm = _state.value.farmEntities.firstOrNull { it.id == farmId }
        if (name.isBlank() || farm == null || areaHa == null || areaHa <= 0) {
            _state.value = _state.value.copy(message = "Nom, xo'jalik va maydonni to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            val district = _state.value.districts.firstOrNull { it.id == farm.districtId }
            geoRepository.createField(farm.id, name.trim(), areaHa, soilType, district?.lat ?: 41.3, district?.lon ?: 64.5)
            _state.value = _state.value.copy(message = "Dala qo'shildi.")
            refreshAll()
        }
    }

    fun addYield(fieldId: Long?, cropId: Long?, year: Int?, yieldTHa: Double?) {
        val field = _state.value.fieldEntities.firstOrNull { it.id == fieldId }
        if (field == null || cropId == null || year == null || yieldTHa == null || yieldTHa <= 0) {
            _state.value = _state.value.copy(message = "Dala, ekin, yil va hosildorlikni to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addYieldRecord(field, cropId, year, yieldTHa)
            _state.value = _state.value.copy(message = "Hosildorlik yozuvi qo'shildi.")
            refreshAll()
        }
    }

    fun addIrrigation(fieldId: Long?, dateText: String, waterM3: Double?, method: String) {
        if (fieldId == null || waterM3 == null || waterM3 <= 0) {
            _state.value = _state.value.copy(message = "Dala va suv hajmini to'g'ri kiriting.")
            return
        }
        val date = runCatching { LocalDate.parse(dateText) }.getOrDefault(LocalDate.now())
        viewModelScope.launch {
            recordsRepository.addIrrigationRecord(fieldId, date, waterM3, method)
            _state.value = _state.value.copy(message = "Sug'orish yozuvi qo'shildi.")
            refreshAll()
        }
    }

    fun addFinance(farmId: Long?, year: Int?, category: String, amount: Double?, note: String) {
        if (farmId == null || year == null || amount == null || amount <= 0) {
            _state.value = _state.value.copy(message = "Xo'jalik, yil va summani to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addFinanceRecord(farmId, year, category, amount, note.trim())
            _state.value = _state.value.copy(message = "Moliya yozuvi qo'shildi.")
            refreshAll()
        }
    }

    fun addSatellite(fieldId: Long?, dateText: String, ndvi: Double?) {
        if (fieldId == null || ndvi == null || ndvi < 0 || ndvi > 1) {
            _state.value = _state.value.copy(message = "Dala va NDVI (0-1 oralig'ida) ni to'g'ri kiriting.")
            return
        }
        val date = runCatching { LocalDate.parse(dateText) }.getOrDefault(LocalDate.now())
        viewModelScope.launch {
            recordsRepository.addSatelliteRecord(fieldId, date, ndvi)
            _state.value = _state.value.copy(message = "NDVI yozuvi qo'shildi.")
            refreshAll()
        }
    }

    fun clearMessage() { _state.value = _state.value.copy(message = null) }
}
