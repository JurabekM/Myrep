package com.agrovision.mobile.ui.reports

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Description
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.ChipRow
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun ReportsScreen(navController: NavHostController, viewModel: ReportsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Hisobotlar va eksport", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(
                "Barcha eksportlar qurilma xotirasidagi Downloads/AgroVision papkasiga yoziladi — " +
                    "hech qanday tarmoq/bulut yuklash yo'q.",
                style = MaterialTheme.typography.bodySmall,
            )
            ChipRow(state.years.map { it.toString() }) { viewModel.selectYear(it.toInt()) }
            Text("Tanlangan yil: ${state.selectedYear}", style = MaterialTheme.typography.titleMedium)

            SectionTitle("Yakuniy KPI hisoboti")
            ElevatedCard {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Button(onClick = viewModel::exportPdf, modifier = Modifier.fillMaxWidth()) {
                        Icon(Icons.Filled.PictureAsPdf, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("PDF hisobot yaratish")
                    }
                    OutlinedButton(onClick = viewModel::exportCsv, modifier = Modifier.fillMaxWidth()) {
                        Icon(Icons.Filled.Description, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("CSV eksport (hosildorlik jadvali)")
                    }
                }
            }

            state.lastMessage?.let {
                Card { Text(it, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall) }
            }
        }
    }
}
