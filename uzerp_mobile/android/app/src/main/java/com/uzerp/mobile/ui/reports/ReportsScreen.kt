package com.uzerp.mobile.ui.reports

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzRed

@Composable
fun ReportsScreen(onBack: () -> Unit, viewModel: ReportsViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Hisobotlar", onBack = onBack) { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                OutlinedTextField(
                    value = state.dateFrom, onValueChange = viewModel::setDateFrom,
                    label = { Text("Davr boshi") }, singleLine = true, modifier = Modifier.weight(1f),
                )
                OutlinedTextField(
                    value = state.dateTo, onValueChange = viewModel::setDateTo,
                    label = { Text("Davr oxiri") }, singleLine = true, modifier = Modifier.weight(1f),
                )
            }
            OutlinedButton(onClick = viewModel::reload, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                Text("Qo'llash")
            }
            state.error?.let { ErrorBanner(it) }
            state.message?.let { ErrorBanner(it) }

            if (state.isLoading) {
                LoadingState()
                return@Column
            }

            state.sales?.let { s ->
                ReportSection(title = "Savdo hisoboti", onExport = viewModel::exportSales) {
                    KeyValueRow("Hujjatlar soni", s.count.toString())
                    KeyValueRow("Sof summa", money(s.netTotal))
                }
            }
            state.purchases?.let { p ->
                ReportSection(title = "Xaridlar hisoboti", onExport = viewModel::exportPurchases) {
                    KeyValueRow("Hujjatlar soni", p.count.toString())
                    KeyValueRow("Jami summa", money(p.total))
                }
            }
            ReportSection(title = "Kam qolgan mahsulotlar (${state.lowStock.size})", onExport = viewModel::exportLowStock) {
                if (state.lowStock.isEmpty()) {
                    Text("Kam qolgan mahsulot yo'q.", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                } else {
                    state.lowStock.forEach { item ->
                        KeyValueRow(
                            "${item.name} (${item.sku ?: "—"})",
                            "${item.currentStock.toPlainString()} / ${item.minStock.toPlainString()} ${item.unit}",
                            valueColor = UzRed,
                        )
                    }
                }
            }
            ReportSection(title = "Eng ko'p sotilgan mahsulotlar (TOP ${state.topProducts.size})", onExport = viewModel::exportTopProducts) {
                if (state.topProducts.isEmpty()) {
                    Text("Ma'lumot yo'q.", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                } else {
                    state.topProducts.forEach { item ->
                        KeyValueRow("${item.productName} (${item.totalQty.toPlainString()} ${item.unit})", money(item.totalRevenue))
                    }
                }
            }
            ReportSection(title = "Mijozlar qarzi (${state.customerDebts.size})", onExport = viewModel::exportCustomerDebts) {
                if (state.customerDebts.isEmpty()) {
                    Text("Qarzdor mijozlar yo'q.", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                } else {
                    state.customerDebts.forEach { item -> KeyValueRow(item.partnerName, money(item.debt), valueColor = UzRed) }
                }
            }
            ReportSection(title = "Ta'minotchilar qarzi (${state.supplierDebts.size})", onExport = viewModel::exportSupplierDebts) {
                if (state.supplierDebts.isEmpty()) {
                    Text("Qarz yo'q.", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                } else {
                    state.supplierDebts.forEach { item -> KeyValueRow(item.partnerName, money(item.debt), valueColor = UzRed) }
                }
            }
        }
    }
}

@Composable
private fun ReportSection(title: String, onExport: () -> Unit, content: @Composable () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Divider(modifier = Modifier.padding(vertical = 8.dp))
            content()
            OutlinedButton(onClick = onExport, modifier = Modifier.fillMaxWidth().padding(top = 10.dp)) {
                Text("CSV eksport qilish")
            }
        }
    }
}

@Composable
private fun KeyValueRow(key: String, value: String, valueColor: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onSurface) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(key, style = MaterialTheme.typography.bodyMedium, color = UzMuted, modifier = Modifier.weight(1f))
        Text(value, style = MaterialTheme.typography.bodyMedium, color = valueColor, fontWeight = FontWeight.Medium)
    }
}
