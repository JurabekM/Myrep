package com.agrovision.mobile.ui.satellite

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.*
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun SatelliteScreen(navController: NavHostController, viewModel: SatelliteViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Sun'iy yo'ldosh monitoringi", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) { LoadingState(); return@AppScaffold }
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(
                "NDVI/EVI qiymatlari dron/sun'iy yo'ldosh tasvirini yuklab (\"Ma'lumotlar\" bo'limida " +
                    "yoki quyida) yoki qo'lda kiritish orqali qo'shiladi.",
                style = MaterialTheme.typography.bodySmall,
            )

            if (state.fields.isEmpty()) {
                EmptyState("Hali birorta dala qo'shilmagan. Avval \"Ma'lumotlar\" bo'limida dala qo'shing.")
                return@AppScaffold
            }

            SimpleDropdown("Dala", state.fields, state.selectedField, { it.label }, viewModel::select)

            if (state.series.isNotEmpty()) {
                SectionTitle("NDVI/EVI dinamikasi")
                SimpleLineChart(
                    labels = state.series.mapIndexed { i, _ -> if (i % 4 == 0) "T${i}" else "" },
                    series = mapOf("NDVI" to state.series.map { it.ndvi }, "EVI" to state.series.map { it.evi }),
                )
            }

            SectionTitle("Dalalar salomatligi (so'nggi NDVI)")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Dala", "Xo'jalik", "NDVI", "Holat"),
                        rows = state.health.take(20).map {
                            listOf(it.field, it.farm, "%.2f".format(it.ndvi), viewModel.classify(it.ndvi))
                        },
                    )
                }
            }
        }
    }
}
