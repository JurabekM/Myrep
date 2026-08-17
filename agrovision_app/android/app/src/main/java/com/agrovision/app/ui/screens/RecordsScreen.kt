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
import com.agrovision.app.config.Constants
import com.agrovision.app.core.Fmt
import com.agrovision.app.core.toSafeDouble
import com.agrovision.app.core.toSafeInt
import com.agrovision.app.data.local.*
import com.agrovision.app.data.repo.GeoRepository
import com.agrovision.app.data.repo.RecordsRepository
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import javax.inject.Inject

data class RecordsUiState(
    val loading: Boolean = true,
    val districts: List<Pair<DistrictEntity, String>> = emptyList(),
    val farmers: List<FarmerEntity> = emptyList(),
    val farms: List<FarmEntity> = emptyList(),
    val fields: List<FieldEntity> = emptyList(),
    val crops: List<CropEntity> = emptyList(),
    val farmerRows: List<FarmerListRow> = emptyList(),
    val farmRows: List<FarmListRow> = emptyList(),
    val fieldRows: List<FieldListRow> = emptyList(),
    val yieldRows: List<YieldListRow> = emptyList(),
    val irrigationRows: List<IrrigationListRow> = emptyList(),
    val financeRows: List<FinanceListRow> = emptyList(),
    val ndviRows: List<NdviListRow> = emptyList(),
    val message: String? = null,
)

@HiltViewModel
class RecordsViewModel @Inject constructor(
    private val geoRepository: GeoRepository,
    private val recordsRepository: RecordsRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(RecordsUiState())
    val state: StateFlow<RecordsUiState> = _state.asStateFlow()

    fun refresh() {
        viewModelScope.launch {
            _state.value = RecordsUiState(
                loading = false,
                districts = geoRepository.districtOptions(),
                farmers = geoRepository.farmers(),
                farms = geoRepository.farms(),
                fields = geoRepository.fields(),
                crops = geoRepository.crops(),
                farmerRows = geoRepository.farmerList(),
                farmRows = geoRepository.farmList(),
                fieldRows = geoRepository.fieldList(),
                yieldRows = recordsRepository.yieldList(),
                irrigationRows = recordsRepository.irrigationList(),
                financeRows = recordsRepository.financeList(),
                ndviRows = recordsRepository.ndviList(),
                message = _state.value.message,
            )
        }
    }

    private fun done(message: String) {
        _state.value = _state.value.copy(message = message)
        refresh()
    }

    fun addFarmer(name: String, phone: String, district: DistrictEntity?) {
        if (name.isBlank() || district == null) {
            _state.value = _state.value.copy(message = "Ism va tumanni to'ldiring.")
            return
        }
        viewModelScope.launch {
            geoRepository.createFarmer(name, phone, district.id)
            done("Fermer qo'shildi: $name")
        }
    }

    fun addFarm(name: String, farmer: FarmerEntity?) {
        if (name.isBlank() || farmer == null) {
            _state.value = _state.value.copy(message = "Nom va fermerni tanlang.")
            return
        }
        viewModelScope.launch {
            geoRepository.createFarm(name, farmer.id, farmer.districtId)
            done("Xo'jalik qo'shildi: $name")
        }
    }

    fun addField(name: String, farm: FarmEntity?, areaHa: Double?, soil: String) {
        if (name.isBlank() || farm == null || areaHa == null || areaHa <= 0) {
            _state.value = _state.value.copy(message = "Nom, xo'jalik va maydonni to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            val district = geoRepository.district(farm.districtId)
            geoRepository.createField(
                farmId = farm.id, name = name, areaHa = areaHa, soilType = soil,
                lat = district?.lat ?: 41.3, lon = district?.lon ?: 64.5,
            )
            done("Dala qo'shildi: $name (${Fmt.dec(areaHa, 1)} ga)")
        }
    }

    fun addYield(field: FieldEntity?, crop: CropEntity?, year: Int?, value: Double?) {
        if (field == null || crop == null || year == null || value == null || value <= 0) {
            _state.value = _state.value.copy(message = "Dala, ekin, yil va hosildorlikni to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addYield(field, crop.id, year, value)
            done("Hosildorlik yozuvi qo'shildi.")
        }
    }

    fun addIrrigation(field: FieldEntity?, dateText: String, water: Double?, method: String) {
        if (field == null || water == null || water <= 0) {
            _state.value = _state.value.copy(message = "Dala va suv hajmini to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addIrrigation(field.id, parseDate(dateText), water, method)
            done("Sug'orish yozuvi qo'shildi.")
        }
    }

    fun addFinance(farm: FarmEntity?, year: Int?, category: String, amount: Double?, note: String) {
        if (farm == null || year == null || amount == null || amount <= 0) {
            _state.value = _state.value.copy(message = "Xo'jalik, yil va summani to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addFinance(farm.id, year, category, amount, note)
            done("Moliya yozuvi qo'shildi.")
        }
    }

    fun addNdvi(field: FieldEntity?, dateText: String, ndvi: Double?) {
        if (field == null || ndvi == null || ndvi < 0 || ndvi > 1) {
            _state.value = _state.value.copy(message = "Dala va NDVI (0.0–1.0) qiymatini to'g'ri kiriting.")
            return
        }
        viewModelScope.launch {
            recordsRepository.addNdvi(field.id, parseDate(dateText), ndvi)
            done("NDVI yozuvi qo'shildi.")
        }
    }

    private fun parseDate(text: String): LocalDate =
        runCatching { LocalDate.parse(text.trim()) }.getOrDefault(LocalDate.now())
}

@Composable
fun RecordsScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: RecordsViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Ma'lumotlar", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = state.message) {
            if (state.loading) {
                LoadingState()
                return@ScreenColumn
            }
            state.message?.let { InfoBanner(it) }

            // ---- Fermerlar ----
            var farmerName by remember { mutableStateOf("") }
            var farmerPhone by remember { mutableStateOf("") }
            var farmerDistrict by remember { mutableStateOf<Pair<DistrictEntity, String>?>(null) }
            ChartCard("Fermerlar (${state.farmerRows.size})") {
                DataTable(
                    listOf("Ism", "Telefon", "Tuman"),
                    state.farmerRows.map { listOf(it.name, it.phone, it.district) },
                    maxRows = 6,
                )
                HorizontalDivider()
                OutlinedTextField(
                    farmerName, { farmerName = it }, label = { Text("Ism-familiya") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
                OutlinedTextField(
                    farmerPhone, { farmerPhone = it }, label = { Text("Telefon") },
                    singleLine = true, modifier = Modifier.fillMaxWidth(),
                )
                Dropdown("Tuman", state.districts, farmerDistrict, { it.second }) { farmerDistrict = it }
                Button(
                    onClick = {
                        viewModel.addFarmer(farmerName, farmerPhone, farmerDistrict?.first)
                        farmerName = ""; farmerPhone = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Fermer qo'shish") }
            }

            // ---- Xo'jaliklar ----
            var farmName by remember { mutableStateOf("") }
            var selectedFarmer by remember { mutableStateOf<FarmerEntity?>(null) }
            ChartCard("Fermer xo'jaliklari (${state.farmRows.size})") {
                DataTable(
                    listOf("Nomi", "Fermer", "Maydon (ga)"),
                    state.farmRows.map { listOf(it.name, it.farmer, Fmt.dec(it.areaHa, 1)) },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.farmers.isEmpty()) {
                    Text(
                        "Avval kamida bitta fermer qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    OutlinedTextField(
                        farmName, { farmName = it }, label = { Text("Xo'jalik nomi") },
                        singleLine = true, modifier = Modifier.fillMaxWidth(),
                    )
                    Dropdown("Fermer", state.farmers, selectedFarmer, { it.name }) { selectedFarmer = it }
                    Button(
                        onClick = { viewModel.addFarm(farmName, selectedFarmer); farmName = "" },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Xo'jalik qo'shish") }
                }
            }

            // ---- Dalalar ----
            var fieldName by remember { mutableStateOf("") }
            var fieldArea by remember { mutableStateOf("") }
            var fieldSoil by remember { mutableStateOf(Constants.SOIL_TYPES.first()) }
            var selectedFarm by remember { mutableStateOf<FarmEntity?>(null) }
            ChartCard("Dalalar (${state.fieldRows.size})") {
                DataTable(
                    listOf("Nomi", "Xo'jalik", "Maydon", "Tuproq"),
                    state.fieldRows.map { listOf(it.name, it.farm, Fmt.dec(it.areaHa, 1), it.soilType) },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.farms.isEmpty()) {
                    Text(
                        "Avval kamida bitta xo'jalik qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    OutlinedTextField(
                        fieldName, { fieldName = it }, label = { Text("Dala nomi/raqami") },
                        singleLine = true, modifier = Modifier.fillMaxWidth(),
                    )
                    NumberField("Maydon", fieldArea, { fieldArea = it }, suffix = "ga")
                    Dropdown("Tuproq turi", Constants.SOIL_TYPES, fieldSoil, { it }) { fieldSoil = it }
                    Dropdown("Xo'jalik", state.farms, selectedFarm, { it.name }) { selectedFarm = it }
                    Button(
                        onClick = {
                            viewModel.addField(fieldName, selectedFarm, fieldArea.toSafeDouble(), fieldSoil)
                            fieldName = ""; fieldArea = ""
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Dala qo'shish") }
                }
            }

            // ---- Hosildorlik ----
            var selectedField by remember { mutableStateOf<FieldEntity?>(null) }
            var selectedCrop by remember { mutableStateOf<CropEntity?>(null) }
            var yieldYear by remember { mutableStateOf(LocalDate.now().year.toString()) }
            var yieldValue by remember { mutableStateOf("") }
            ChartCard("Hosildorlik yozuvlari (${state.yieldRows.size})") {
                DataTable(
                    listOf("Dala", "Ekin", "Yil", "t/ga"),
                    state.yieldRows.map { listOf(it.field, it.crop, it.year.toString(), Fmt.dec(it.yieldTHa, 2)) },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.fields.isEmpty()) {
                    Text(
                        "Avval kamida bitta dala qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Dropdown("Dala", state.fields, selectedField, { it.name }) { selectedField = it }
                    Dropdown("Ekin", state.crops, selectedCrop, { it.name }) { selectedCrop = it }
                    NumberField("Yil", yieldYear, { yieldYear = it })
                    NumberField("Hosildorlik", yieldValue, { yieldValue = it }, suffix = "t/ga")
                    Button(
                        onClick = {
                            viewModel.addYield(
                                selectedField, selectedCrop, yieldYear.toSafeInt(), yieldValue.toSafeDouble(),
                            )
                            yieldValue = ""
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Hosildorlik qo'shish") }
                }
            }

            // ---- Sug'orish ----
            var irrigationField by remember { mutableStateOf<FieldEntity?>(null) }
            var irrigationDate by remember { mutableStateOf(LocalDate.now().toString()) }
            var irrigationWater by remember { mutableStateOf("") }
            var irrigationMethod by remember { mutableStateOf(Constants.IRRIGATION_METHODS.first()) }
            ChartCard("Sug'orish yozuvlari (${state.irrigationRows.size})") {
                DataTable(
                    listOf("Dala", "Sana", "m³", "Usul"),
                    state.irrigationRows.map {
                        listOf(it.field, Fmt.date(it.epochDay), Fmt.num(it.waterM3, 0), it.method)
                    },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.fields.isEmpty()) {
                    Text(
                        "Avval kamida bitta dala qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Dropdown("Dala", state.fields, irrigationField, { it.name }) { irrigationField = it }
                    OutlinedTextField(
                        irrigationDate, { irrigationDate = it },
                        label = { Text("Sana (YYYY-MM-DD)") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    NumberField("Suv hajmi", irrigationWater, { irrigationWater = it }, suffix = "m³")
                    Dropdown("Usul", Constants.IRRIGATION_METHODS, irrigationMethod, { it }) { irrigationMethod = it }
                    Button(
                        onClick = {
                            viewModel.addIrrigation(
                                irrigationField, irrigationDate, irrigationWater.toSafeDouble(), irrigationMethod,
                            )
                            irrigationWater = ""
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Sug'orish yozuvini qo'shish") }
                }
            }

            // ---- Moliya ----
            var financeFarm by remember { mutableStateOf<FarmEntity?>(null) }
            var financeYear by remember { mutableStateOf(LocalDate.now().year.toString()) }
            var financeCategory by remember { mutableStateOf(Constants.FINANCE_CATEGORIES.first().first) }
            var financeAmount by remember { mutableStateOf("") }
            var financeNote by remember { mutableStateOf("") }
            ChartCard("Moliya yozuvlari (${state.financeRows.size})") {
                DataTable(
                    listOf("Xo'jalik", "Yil", "Turi", "Summa"),
                    state.financeRows.map {
                        listOf(it.farm, it.year.toString(), it.category, Fmt.money(it.amount))
                    },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.farms.isEmpty()) {
                    Text(
                        "Avval kamida bitta xo'jalik qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Dropdown("Xo'jalik", state.farms, financeFarm, { it.name }) { financeFarm = it }
                    NumberField("Yil", financeYear, { financeYear = it })
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        Constants.FINANCE_CATEGORIES.forEach { (key, label) ->
                            FilterChip(
                                selected = financeCategory == key,
                                onClick = { financeCategory = key },
                                label = { Text(label) },
                            )
                        }
                    }
                    NumberField("Summa", financeAmount, { financeAmount = it }, suffix = "so'm")
                    OutlinedTextField(
                        financeNote, { financeNote = it }, label = { Text("Izoh (ixtiyoriy)") },
                        singleLine = true, modifier = Modifier.fillMaxWidth(),
                    )
                    Button(
                        onClick = {
                            viewModel.addFinance(
                                financeFarm, financeYear.toSafeInt(), financeCategory,
                                financeAmount.toSafeDouble(), financeNote,
                            )
                            financeAmount = ""; financeNote = ""
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Moliya yozuvini qo'shish") }
                }
            }

            // ---- NDVI ----
            var ndviField by remember { mutableStateOf<FieldEntity?>(null) }
            var ndviDate by remember { mutableStateOf(LocalDate.now().toString()) }
            var ndviValue by remember { mutableStateOf("") }
            ChartCard(
                "NDVI yozuvlari (${state.ndviRows.size})",
                "Tasvirdan avtomatik hisoblash uchun Sun'iy yo'ldosh bo'limidan foydalaning.",
            ) {
                DataTable(
                    listOf("Dala", "Sana", "NDVI"),
                    state.ndviRows.map { listOf(it.field, Fmt.date(it.epochDay), Fmt.dec(it.ndvi, 3)) },
                    maxRows = 6,
                )
                HorizontalDivider()
                if (state.fields.isEmpty()) {
                    Text(
                        "Avval kamida bitta dala qo'shing.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.error,
                    )
                } else {
                    Dropdown("Dala", state.fields, ndviField, { it.name }) { ndviField = it }
                    OutlinedTextField(
                        ndviDate, { ndviDate = it },
                        label = { Text("Sana (YYYY-MM-DD)") }, singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    NumberField("NDVI (0.0–1.0)", ndviValue, { ndviValue = it })
                    Button(
                        onClick = {
                            viewModel.addNdvi(ndviField, ndviDate, ndviValue.toSafeDouble())
                            ndviValue = ""
                        },
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("NDVI qo'shish") }
                }
            }
        }
    }
}
