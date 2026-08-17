package com.agrovision.mobile.ui.market

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
import com.agrovision.mobile.ui.common.*
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun MarketScreen(navController: NavHostController, viewModel: MarketViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()

    AppScaffold(navController, "Bozor narxlari", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) { LoadingState(); return@AppScaffold }
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            SectionTitle("So'nggi narxlar")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Ekin", "Narx (so'm/kg)"),
                        rows = state.latest.map { listOf(it.crop, "%,.0f".format(it.price)) },
                    )
                }
            }

            SimpleDropdown("Ekin", state.crops, state.selectedCrop, { it.name }, viewModel::selectCrop)

            state.forecast?.let { forecast ->
                SectionTitle("${state.selectedCrop?.name} — narx tarixi va prognozi")
                if (forecast.history.isEmpty()) {
                    EmptyState("Bu ekin uchun narx tarixi hali kiritilmagan.")
                } else {
                    val labels = (1..forecast.history.size).map { "T-${forecast.history.size - it}" } +
                        (1..forecast.forecast.size).map { "+$it hafta" }
                    val historySeries: List<Double?> = forecast.history.map { it } + List(forecast.forecast.size) { null }
                    val forecastSeries: List<Double?> = List(forecast.history.size - 1) { null } +
                        listOf(forecast.history.lastOrNull()) + forecast.forecast
                    SimpleLineChart(labels, mapOf("Narx" to historySeries, "Prognoz" to forecastSeries))
                }
            }

            if (viewModel.canEdit()) {
                SectionTitle("Narx kiritish (qo'lda)")
                var price by remember { mutableStateOf("") }
                var marketName by remember { mutableStateOf("Mahalliy bozor") }
                ElevatedCard {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(value = price, onValueChange = { price = it }, label = { Text("Narx (so'm/kg)") }, modifier = Modifier.fillMaxWidth())
                        OutlinedTextField(value = marketName, onValueChange = { marketName = it }, label = { Text("Bozor nomi") }, modifier = Modifier.fillMaxWidth())
                        var priceError by remember { mutableStateOf(false) }
                        if (priceError) Text("Narxni to'g'ri kiriting (masalan: 5000)", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                        Button(onClick = {
                            val value = price.toSafeDouble()
                            if (value == null || value <= 0) {
                                priceError = true
                            } else {
                                priceError = false
                                viewModel.addPrice(value, marketName.ifBlank { "Mahalliy bozor" })
                                price = ""
                            }
                        }) { Text("Saqlash") }
                    }
                }
            }
        }
    }
}
