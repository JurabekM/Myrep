package com.agrovision.mobile.ui.irrigation

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.WaterDrop
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
fun IrrigationScreen(navController: NavHostController, viewModel: IrrigationViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Sug'orish tahlili", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ChipRow(state.years.map { it.toString() }) { viewModel.select(it.toInt()) }
            if (state.loading) { LoadingState(); return@AppScaffold }

            val totalWater = state.byRegion.sumOf { it.waterMlnM3 }
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                KpiCard(Icons.Filled.WaterDrop, "%.1f mln m³".format(totalWater), "Jami sug'orish suvi, ${state.selectedYear}")
            }

            SectionTitle("Viloyatlar bo'yicha suv sarfi (mln m³)")
            SimpleBarChart(labels = state.byRegion.map { it.region.take(4) }, values = state.byRegion.map { it.waterMlnM3 })

            SectionTitle("Sug'orish usullari")
            SimplePieChart(data = state.byMethod.map { it.method to it.waterMlnM3 })

            SectionTitle("Oylik suv sarfi (mln m³)")
            SimpleBarChart(labels = state.monthly.map { viewModel.monthLabel(it.month) }, values = state.monthly.map { it.waterMlnM3 })

            SectionTitle("Suv samaradorligi (m³/tonna)")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Ekin", "Ishlab chiqarish (t)", "m³/t"),
                        rows = state.efficiency.map { row ->
                            val perTonne = if (row.production > 0) row.waterM3 / row.production else 0.0
                            listOf(row.crop, "%.0f".format(row.production), "%.0f".format(perTonne))
                        },
                    )
                }
            }
        }
    }
}
