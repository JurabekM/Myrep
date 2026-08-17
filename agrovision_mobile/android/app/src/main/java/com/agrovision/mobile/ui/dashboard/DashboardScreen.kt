package com.agrovision.mobile.ui.dashboard

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.core.Fmt
import com.agrovision.mobile.ui.common.*
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun DashboardScreen(navController: NavHostController, viewModel: DashboardViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.load() }

    AppScaffold(navController, "Bosh sahifa", onLogout = { navController.logoutAndReturn() }) { padding ->
        if (state.loading) {
            LoadingState()
            return@AppScaffold
        }
        val kpi = state.kpi ?: return@AppScaffold
        Column(
            Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                item { KpiCard(Icons.Filled.Landscape, "${Fmt.number(kpi.totalAreaHa)} ga", "Yer maydoni") }
                item { KpiCard(Icons.Filled.Groups, "${kpi.farmers}", "Fermerlar") }
                item { KpiCard(Icons.Filled.HomeWork, "${kpi.farms}", "Xo'jaliklar") }
                item { KpiCard(Icons.Filled.GridOn, "${kpi.fields}", "Dalalar") }
                item { KpiCard(Icons.Filled.Agriculture, "${kpi.avgYieldTHa} t/ga", "O'rtacha hosildorlik ${kpi.year}") }
                item { KpiCard(Icons.Filled.Inventory, "${Fmt.number(kpi.productionT)} t", "Ishlab chiqarish") }
                item {
                    KpiCard(
                        Icons.Filled.Payments, "${Fmt.money(kpi.profit)} so'm", "Sof foyda (ROI ${kpi.roiPercent}%)",
                        tint = if (kpi.profit >= 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    )
                }
                item { KpiCard(Icons.Filled.Eco, "${kpi.avgNdvi}", "O'rtacha NDVI") }
                item { KpiCard(Icons.Filled.WaterDrop, "${kpi.waterMillionM3} mln m³", "Sug'orish suvi") }
            }

            SectionTitle("Hosildorlik trendi (t/ga)")
            SimpleLineChart(
                labels = state.trend.map { it.year.toString() },
                series = mapOf("O'rtacha hosildorlik" to state.trend.map { it.avgYield }),
            )

            SectionTitle("Ogohlantirishlar")
            if (state.alerts.isEmpty()) {
                EmptyState("Faol ogohlantirishlar yo'q.")
            } else {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    state.alerts.forEach { AlertBanner(it.level, it.title, it.detail) }
                }
            }

            SectionTitle("Eng samarali xo'jaliklar, ${kpi.year}")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Xo'jalik", "Hudud", "t/ga"),
                        rows = state.topFarms.take(8).map { listOf(it.farm, it.region, "${it.avgYield}") },
                    )
                }
            }
        }
    }
}
