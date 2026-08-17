package com.agrovision.mobile.ui.records

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.core.toSafeDouble
import com.agrovision.mobile.core.toSafeInt
import com.agrovision.mobile.data.local.CropEntity
import com.agrovision.mobile.data.local.DistrictEntity
import com.agrovision.mobile.data.local.FarmEntity
import com.agrovision.mobile.data.local.FarmerEntity
import com.agrovision.mobile.data.local.FieldEntity
import com.agrovision.mobile.ui.common.DataTable
import com.agrovision.mobile.ui.common.LoadingState
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.common.SimpleDropdown
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn
import java.time.LocalDate

@Composable
fun RecordsScreen(navController: NavHostController, viewModel: RecordsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refreshAll() }

    AppScaffold(navController, "Ma'lumotlar (qo'lda kiritish)", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) { LoadingState(); return@AppScaffold }
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(20.dp)) {
            state.message?.let {
                ElevatedCard { Text(it, Modifier.padding(10.dp), style = MaterialTheme.typography.bodySmall) }
                LaunchedEffect(it) { kotlinx.coroutines.delay(3500); viewModel.clearMessage() }
            }

            FarmerSection(state, viewModel)
            FarmSection(state, viewModel)
            FieldSection(state, viewModel)
            YieldSection(state, viewModel)
            IrrigationSection(state, viewModel)
            FinanceSection(state, viewModel)
            SatelliteSection(state, viewModel)
        }
    }
}

@Composable
private fun FarmerSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Fermerlar")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Ism", "Telefon", "Tuman"), state.farmers.take(10).map { listOf(it.name, it.phone, it.district) })
            var name by remember { mutableStateOf("") }
            var phone by remember { mutableStateOf("") }
            var district by remember { mutableStateOf<DistrictEntity?>(null) }
            OutlinedTextField(name, { name = it }, label = { Text("Ism-familiya") }, modifier = Modifier.fillMaxWidth())
            OutlinedTextField(phone, { phone = it }, label = { Text("Telefon") }, modifier = Modifier.fillMaxWidth())
            SimpleDropdown("Tuman", state.districts, district, { it.name }, { district = it })
            Button(onClick = { viewModel.addFarmer(name, phone, district?.id); name = ""; phone = "" }) { Text("Fermer qo'shish") }
        }
    }
}

@Composable
private fun FarmSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Fermer xo'jaliklari")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Nomi", "Fermer", "Maydon (ga)"), state.farms.take(10).map { listOf(it.name, it.farmer, "%.1f".format(it.areaHa)) })
            if (state.farmerEntities.isEmpty()) {
                Text("Avval kamida bitta fermer qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var name by remember { mutableStateOf("") }
                var farmer by remember { mutableStateOf<FarmerEntity?>(null) }
                OutlinedTextField(name, { name = it }, label = { Text("Xo'jalik nomi") }, modifier = Modifier.fillMaxWidth())
                SimpleDropdown("Fermer", state.farmerEntities, farmer, { it.name }, { farmer = it })
                Button(onClick = { viewModel.addFarm(name, farmer?.id); name = "" }) { Text("Xo'jalik qo'shish") }
            }
        }
    }
}

@Composable
private fun FieldSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Dalalar")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Nomi", "Xo'jalik", "Maydon (ga)", "Tuproq"), state.fields.take(10).map { listOf(it.name, it.farm, "%.1f".format(it.areaHa), it.soilType) })
            if (state.farmEntities.isEmpty()) {
                Text("Avval kamida bitta xo'jalik qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var name by remember { mutableStateOf("") }
                var area by remember { mutableStateOf("") }
                var soil by remember { mutableStateOf("bo'z tuproq") }
                var farm by remember { mutableStateOf<FarmEntity?>(null) }
                OutlinedTextField(name, { name = it }, label = { Text("Dala nomi/raqami") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(area, { area = it }, label = { Text("Maydon (ga)") }, modifier = Modifier.fillMaxWidth())
                SimpleDropdown(
                    "Tuproq turi",
                    listOf("bo'z tuproq", "o'tloq tuproq", "sho'rlangan tuproq", "qumloq tuproq", "gilli tuproq"),
                    soil, { it }, { soil = it },
                )
                SimpleDropdown("Xo'jalik", state.farmEntities, farm, { it.name }, { farm = it })
                Button(onClick = { viewModel.addField(name, farm?.id, area.toSafeDouble(), soil); name = ""; area = "" }) { Text("Dala qo'shish") }
            }
        }
    }
}

@Composable
private fun YieldSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Hosildorlik yozuvlari")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Dala", "Ekin", "Yil", "t/ga"), state.yields.take(10).map { listOf(it.field, it.crop, "${it.year}", "${it.yieldTHa}") })
            if (state.fieldEntities.isEmpty()) {
                Text("Avval kamida bitta dala qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var field by remember { mutableStateOf<FieldEntity?>(null) }
                var crop by remember { mutableStateOf<CropEntity?>(state.crops.firstOrNull()) }
                var year by remember { mutableStateOf(LocalDate.now().year.toString()) }
                var yieldValue by remember { mutableStateOf("") }
                SimpleDropdown("Dala", state.fieldEntities, field, { it.name }, { field = it })
                SimpleDropdown("Ekin", state.crops, crop, { it.name }, { crop = it })
                OutlinedTextField(year, { year = it }, label = { Text("Yil") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(yieldValue, { yieldValue = it }, label = { Text("Hosildorlik (t/ga)") }, modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    viewModel.addYield(field?.id, crop?.id, year.toSafeInt(), yieldValue.toSafeDouble())
                    yieldValue = ""
                }) { Text("Hosildorlik qo'shish") }
            }
        }
    }
}

@Composable
private fun IrrigationSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Sug'orish yozuvlari")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Dala", "Sana", "m³", "Usul"), state.irrigation.take(10).map { listOf(it.field, com.agrovision.mobile.core.Fmt.date(it.epochDay), "${it.waterM3}", it.method) })
            if (state.fieldEntities.isEmpty()) {
                Text("Avval kamida bitta dala qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var field by remember { mutableStateOf<FieldEntity?>(null) }
                var date by remember { mutableStateOf(LocalDate.now().toString()) }
                var water by remember { mutableStateOf("") }
                var method by remember { mutableStateOf(IRRIGATION_METHODS.first()) }
                SimpleDropdown("Dala", state.fieldEntities, field, { it.name }, { field = it })
                OutlinedTextField(date, { date = it }, label = { Text("Sana (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(water, { water = it }, label = { Text("Suv hajmi (m³)") }, modifier = Modifier.fillMaxWidth())
                SimpleDropdown("Usul", IRRIGATION_METHODS, method, { it }, { method = it })
                Button(onClick = {
                    viewModel.addIrrigation(field?.id, date, water.toSafeDouble(), method)
                    water = ""
                }) { Text("Sug'orish yozuvini qo'shish") }
            }
        }
    }
}

@Composable
private fun FinanceSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("Moliya yozuvlari")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            DataTable(listOf("Xo'jalik", "Yil", "Turi", "Summa"), state.finance.take(10).map { listOf(it.farm, "${it.year}", it.category, "%.0f".format(it.amount)) })
            if (state.farmEntities.isEmpty()) {
                Text("Avval kamida bitta xo'jalik qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var farm by remember { mutableStateOf<FarmEntity?>(null) }
                var year by remember { mutableStateOf(LocalDate.now().year.toString()) }
                var category by remember { mutableStateOf(FINANCE_CATEGORIES.first().first) }
                var amount by remember { mutableStateOf("") }
                var note by remember { mutableStateOf("") }
                SimpleDropdown("Xo'jalik", state.farmEntities, farm, { it.name }, { farm = it })
                OutlinedTextField(year, { year = it }, label = { Text("Yil") }, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    FINANCE_CATEGORIES.forEach { (key, label) ->
                        FilterChip(selected = category == key, onClick = { category = key }, label = { Text(label) })
                    }
                }
                OutlinedTextField(amount, { amount = it }, label = { Text("Summa (so'm)") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(note, { note = it }, label = { Text("Izoh (ixtiyoriy)") }, modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    viewModel.addFinance(farm?.id, year.toSafeInt(), category, amount.toSafeDouble(), note)
                    amount = ""; note = ""
                }) { Text("Moliya yozuvini qo'shish") }
            }
        }
    }
}

@Composable
private fun SatelliteSection(state: RecordsUiState, viewModel: RecordsViewModel) {
    SectionTitle("NDVI (o'simlik indeksi) yozuvlari")
    ElevatedCard {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                "Dron/sun'iy yo'ldosh tasviri bo'lmasa, NDVI qiymatini (0.0-1.0) qo'lda kiriting. " +
                    "Tasvirdan avtomatik hisoblash uchun Sun'iy yo'ldosh sahifasidagi yuklash funksiyasidan foydalaning.",
                style = MaterialTheme.typography.bodySmall,
            )
            DataTable(listOf("Dala", "Sana", "NDVI"), state.satellite.take(10).map { listOf(it.field, com.agrovision.mobile.core.Fmt.date(it.epochDay), "${it.ndvi}") })
            if (state.fieldEntities.isEmpty()) {
                Text("Avval kamida bitta dala qo'shing.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
            } else {
                var field by remember { mutableStateOf<FieldEntity?>(null) }
                var date by remember { mutableStateOf(LocalDate.now().toString()) }
                var ndvi by remember { mutableStateOf("") }
                SimpleDropdown("Dala", state.fieldEntities, field, { it.name }, { field = it })
                OutlinedTextField(date, { date = it }, label = { Text("Sana (YYYY-MM-DD)") }, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(ndvi, { ndvi = it }, label = { Text("NDVI (0.0 - 1.0)") }, modifier = Modifier.fillMaxWidth())
                Button(onClick = {
                    viewModel.addSatellite(field?.id, date, ndvi.toSafeDouble())
                    ndvi = ""
                }) { Text("NDVI qo'shish") }
            }
        }
    }
}
