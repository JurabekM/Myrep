package com.agrovision.mobile.ui.analytics

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
fun AnalyticsScreen(navController: NavHostController, viewModel: AnalyticsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Analitika va prognozlash", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ChipRow(state.years.map { it.toString() }) { viewModel.selectYear(it.toInt()) }

            if (state.loading) { LoadingState(); return@AppScaffold }

            SectionTitle("Hosildorlik: trend va prognoz (t/ga)")
            SimpleLineChart(
                labels = state.forecastLabels,
                series = mapOf("Haqiqiy" to state.forecastActual, "Prognoz" to state.forecastLine),
            )

            SectionTitle("Viloyatlar — o'rtacha hosildorlik, ${state.selectedYear} (t/ga)")
            SimpleBarChart(
                labels = state.byRegion.map { it.region.take(4) },
                values = state.byRegion.map { it.avgYield },
            )

            SectionTitle("Hudud x ekin — hosildorlik matritsasi, ${state.selectedYear}")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Hudud", "Ekin", "t/ga"),
                        rows = state.matrix.sortedByDescending { it.avgYield }.take(20)
                            .map { listOf(it.region, it.crop, "%.2f".format(it.avgYield)) },
                    )
                }
            }

            SectionTitle("Viloyatlar jadvali")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Hudud", "t/ga", "Ishlab chiqarish (t)"),
                        rows = state.byRegion.map { listOf(it.region, "${it.avgYield}", "%.0f".format(it.production)) },
                    )
                }
            }
        }
    }
}
