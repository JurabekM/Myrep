package com.agrovision.mobile.ui.finance

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Percent
import androidx.compose.material.icons.filled.Savings
import androidx.compose.material.icons.filled.TrendingDown
import androidx.compose.material.icons.filled.TrendingUp
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
fun FinanceScreen(navController: NavHostController, viewModel: FinanceViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Moliya va iqtisod", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            ChipRow(state.years.map { it.toString() }) { viewModel.select(it.toInt()) }
            if (state.loading) { LoadingState(); return@AppScaffold }

            val record = state.summary.firstOrNull { it.year == state.selectedYear }
            if (record != null) {
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    KpiCard(Icons.Filled.TrendingUp, "${Fmt.money(record.income)} so'm", "Daromad")
                    KpiCard(Icons.Filled.TrendingDown, "${Fmt.money(record.expense)} so'm", "Xarajat")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    KpiCard(
                        Icons.Filled.Savings, "${Fmt.money(record.profit)} so'm", "Sof foyda",
                        tint = if (record.profit >= 0) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error,
                    )
                    KpiCard(Icons.Filled.Percent, "${record.roi}%", "ROI")
                }
            }

            SectionTitle("Daromad va xarajat dinamikasi (mlrd so'm)")
            SimpleBarChart(
                labels = state.summary.map { it.year.toString() },
                values = state.summary.map { it.income / 1e9 },
                barColor = MaterialTheme.colorScheme.primary,
            )

            SectionTitle("Viloyatlar bo'yicha sof foyda, ${state.selectedYear}")
            SimpleBarChart(
                labels = state.byRegion.map { it.region.take(4) },
                values = state.byRegion.map { (it.income - it.expense) / 1e6 },
            )

            SectionTitle("Xo'jaliklar reytingi (mln so'm)")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Xo'jalik", "Daromad", "Foyda"),
                        rows = state.farmRanking.take(15).map {
                            listOf(it.farm, "%.0f".format(it.income / 1e6), "%.0f".format((it.income - it.expense) / 1e6))
                        },
                    )
                }
            }
        }
    }
}
