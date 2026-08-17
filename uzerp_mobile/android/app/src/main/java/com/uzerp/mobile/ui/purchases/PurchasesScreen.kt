package com.uzerp.mobile.ui.purchases

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.LocalShipping
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.MoneyText
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.StatusChip
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzOrange

@Composable
fun PurchasesListScreen(onBack: () -> Unit, onOpen: (Long) -> Unit, onCreate: () -> Unit, viewModel: PurchasesListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.reload() }
    ScreenScaffold(title = "Xaridlar", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = onCreate) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Xaridlar yo'q.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { purchase ->
                        ListRowCard(
                            title = purchase.number,
                            subtitle = "${purchase.supplierName ?: "—"} · ${purchase.docDate}",
                            trailing = money(purchase.total),
                            badge = { StatusChip(purchase.status) },
                            onClick = { onOpen(purchase.id) },
                            leadingIcon = Icons.Filled.LocalShipping,
                            iconTint = UzOrange,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun PurchaseDetailScreen(purchaseId: Long, onBack: () -> Unit, viewModel: PurchaseDetailViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showPaymentDialog by remember { mutableStateOf(false) }
    LaunchedEffect(purchaseId) { viewModel.load(purchaseId) }

    val detail = state.detail
    ScreenScaffold(title = detail?.purchase?.number ?: "Xarid", onBack = onBack) { padding ->
        if (state.isLoading || detail == null) {
            LoadingState()
            return@ScreenScaffold
        }
        val purchase = detail.purchase
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }
            Row(modifier = Modifier.fillMaxWidth()) {
                Text("Ta'minotchi: ${state.supplierName ?: "—"}", modifier = Modifier.weight(1f))
                StatusChip(purchase.status)
            }
            Divider(modifier = Modifier.padding(vertical = 10.dp))
            Text("Pozitsiyalar", fontWeight = FontWeight.SemiBold)
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(detail.items, key = { it.id }) { item ->
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        Text("${item.productName} (${item.quantity} ${item.unit})", modifier = Modifier.weight(1f))
                        MoneyText(item.total)
                    }
                }
            }
            Divider(modifier = Modifier.padding(vertical = 8.dp))
            Row(modifier = Modifier.fillMaxWidth()) {
                Text("JAMI", modifier = Modifier.weight(1f), fontWeight = FontWeight.Bold)
                Text(money(purchase.total), fontWeight = FontWeight.Bold)
            }
            Text("To'langan: ${money(purchase.paidAmount)}", color = MaterialTheme.colorScheme.onSurfaceVariant)

            Row(modifier = Modifier.fillMaxWidth().padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (purchase.status == "draft") {
                    Button(onClick = viewModel::receive, colors = ButtonDefaults.buttonColors(containerColor = UzGreen)) { Text("Qabul qilish") }
                }
                if (purchase.status in setOf("received", "partial")) {
                    Button(onClick = { showPaymentDialog = true }) { Text("To'lash") }
                }
                if (purchase.status != "cancelled" && purchase.paidAmount.signum() == 0) {
                    TextButton(onClick = viewModel::cancel) { Text("Bekor qilish", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }

    if (showPaymentDialog && detail != null) {
        val remaining = detail.purchase.total.subtract(detail.purchase.paidAmount)
        var amount by remember { mutableStateOf(remaining.toPlainString()) }
        AlertDialog(
            onDismissRequest = { showPaymentDialog = false },
            title = { Text("To'lov") },
            text = { OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text("Summa") }, singleLine = true) },
            confirmButton = {
                Button(onClick = { amount.toBigDecimalOrNull()?.let(viewModel::pay); showPaymentDialog = false }) { Text("To'lash") }
            },
            dismissButton = { TextButton(onClick = { showPaymentDialog = false }) { Text("Bekor qilish") } },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PurchaseFormScreen(onBack: () -> Unit, onSaved: (Long) -> Unit, viewModel: PurchaseFormViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var supplierExpanded by remember { mutableStateOf(false) }
    var productExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(state.savedId) { state.savedId?.let(onSaved) }

    ScreenScaffold(title = "Yangi xarid", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }

            ExposedDropdownMenuBox(expanded = supplierExpanded, onExpandedChange = { supplierExpanded = it }) {
                OutlinedTextField(
                    value = state.suppliers.firstOrNull { it.id == state.supplierId }?.name ?: "— tanlanmagan —",
                    onValueChange = {}, readOnly = true, label = { Text("Ta'minotchi") },
                    modifier = Modifier.fillMaxWidth().menuAnchor(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = supplierExpanded) },
                )
                DropdownMenu(expanded = supplierExpanded, onDismissRequest = { supplierExpanded = false }) {
                    state.suppliers.forEach { s ->
                        DropdownMenuItem(text = { Text(s.name) }, onClick = { viewModel.setSupplier(s.id); supplierExpanded = false })
                    }
                }
            }

            ExposedDropdownMenuBox(expanded = productExpanded, onExpandedChange = { productExpanded = it }, modifier = Modifier.padding(top = 10.dp)) {
                OutlinedTextField(
                    value = "+ Mahsulot qo'shish", onValueChange = {}, readOnly = true,
                    modifier = Modifier.fillMaxWidth().menuAnchor(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = productExpanded) },
                )
                DropdownMenu(expanded = productExpanded, onDismissRequest = { productExpanded = false }) {
                    state.products.forEach { p ->
                        DropdownMenuItem(text = { Text(p.name) }, onClick = { viewModel.addLine(p); productExpanded = false })
                    }
                }
            }

            Divider(modifier = Modifier.padding(vertical = 10.dp))
            LazyColumn(modifier = Modifier.weight(1f)) {
                items(state.lines, key = { it.product.id }) { line ->
                    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
                        Text(line.product.name, modifier = Modifier.weight(1f))
                        OutlinedTextField(
                            value = line.quantity.toPlainString(),
                            onValueChange = { v -> v.toBigDecimalOrNull()?.let { viewModel.updateLine(line.product.id, quantity = it) } },
                            modifier = Modifier.width(70.dp), singleLine = true,
                        )
                        OutlinedTextField(
                            value = line.price.toPlainString(),
                            onValueChange = { v -> v.toBigDecimalOrNull()?.let { viewModel.updateLine(line.product.id, price = it) } },
                            modifier = Modifier.width(90.dp), singleLine = true,
                        )
                        TextButton(onClick = { viewModel.removeLine(line.product.id) }) { Text("✕") }
                    }
                }
            }

            Row(modifier = Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { viewModel.save(false) }, enabled = !state.isSaving) { Text("Saqlash") }
                Button(onClick = { viewModel.save(true) }, enabled = !state.isSaving, colors = ButtonDefaults.buttonColors(containerColor = UzGreen)) {
                    Text("Saqlash va qabul qilish")
                }
            }
        }
    }
}
