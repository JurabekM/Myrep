package com.uzerp.mobile.ui.sales

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
import androidx.compose.material.icons.filled.ReceiptLong
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
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzGreen

private val DOC_TYPE_LABELS = mapOf(
    "quotation" to "Taklif", "order" to "Buyurtma", "invoice" to "Hisob-faktura",
    "pos" to "POS savdo", "return" to "Qaytarish",
)

@Composable
fun SalesListScreen(onBack: () -> Unit, onOpen: (Long) -> Unit, onCreate: () -> Unit, viewModel: SalesListViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Savdo hujjatlari", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = onCreate) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Hujjatlar yo'q.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { doc ->
                        ListRowCard(
                            title = "${doc.number} · ${DOC_TYPE_LABELS[doc.docType] ?: doc.docType}",
                            subtitle = "${doc.customerName ?: "—"} · ${doc.docDate}",
                            trailing = money(doc.total),
                            badge = { StatusChip(doc.status) },
                            onClick = { onOpen(doc.id) },
                            leadingIcon = Icons.Filled.ReceiptLong,
                            iconTint = UzAccent,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun SalesDetailScreen(
    docId: Long,
    onBack: () -> Unit,
    onNavigateToDoc: (Long) -> Unit,
    onReturn: (Long) -> Unit,
    viewModel: SalesDetailViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    var showPaymentDialog by remember { mutableStateOf(false) }

    LaunchedEffect(docId) { viewModel.load(docId) }

    val detail = state.detail
    ScreenScaffold(title = detail?.doc?.number ?: "Hujjat", onBack = onBack) { padding ->
        if (state.isLoading || detail == null) {
            LoadingState()
            return@ScreenScaffold
        }
        val doc = detail.doc
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }

            Row(modifier = Modifier.fillMaxWidth()) {
                Text(DOC_TYPE_LABELS[doc.docType] ?: doc.docType, modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurface)
                StatusChip(doc.status)
            }
            Text("Mijoz: ${state.customerName ?: "umumiy xaridor"}", color = MaterialTheme.colorScheme.onSurfaceVariant)
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
            SummaryRow("Oraliq jami", doc.subtotal)
            SummaryRow("Chegirma", doc.discount)
            SummaryRow("QQS (ichida)", doc.vatAmount)
            SummaryRow("JAMI", doc.total, bold = true)
            SummaryRow("To'langan", doc.paidAmount)

            Row(modifier = Modifier.fillMaxWidth().padding(top = 14.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (doc.status == "draft") {
                    Button(onClick = viewModel::confirm, colors = ButtonDefaults.buttonColors(containerColor = UzGreen)) {
                        Text("Tasdiqlash")
                    }
                }
                if (doc.status in setOf("confirmed", "partial") && doc.docType in setOf("invoice", "pos", "order")) {
                    Button(onClick = { showPaymentDialog = true }) { Text("To'lov") }
                }
                if (doc.docType in setOf("quotation", "order") && doc.status != "cancelled") {
                    TextButton(onClick = { viewModel.convert(onNavigateToDoc) }) { Text("Keyingi bosqich") }
                }
                if (doc.docType in setOf("invoice", "pos") && doc.status in setOf("confirmed", "partial", "paid")) {
                    TextButton(onClick = { onReturn(docId) }) { Text("Qaytarish") }
                }
                if (doc.status != "cancelled" && doc.paidAmount.signum() == 0) {
                    TextButton(onClick = viewModel::cancel) { Text("Bekor qilish", color = MaterialTheme.colorScheme.error) }
                }
            }
        }
    }

    if (showPaymentDialog && detail != null) {
        val remaining = detail.doc.total.subtract(detail.doc.paidAmount)
        PaymentDialog(
            remaining = remaining,
            onDismiss = { showPaymentDialog = false },
            onConfirm = { amount -> viewModel.registerPayment(amount); showPaymentDialog = false },
        )
    }
}

@Composable
private fun SummaryRow(label: String, value: java.math.BigDecimal, bold: Boolean = false) {
    Row(modifier = Modifier.fillMaxWidth().padding(vertical = 2.dp)) {
        Text(label, modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(money(value), fontWeight = if (bold) FontWeight.Bold else FontWeight.Normal)
    }
}

@Composable
private fun PaymentDialog(remaining: java.math.BigDecimal, onDismiss: () -> Unit, onConfirm: (java.math.BigDecimal) -> Unit) {
    var amount by remember { mutableStateOf(remaining.toPlainString()) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("To'lov qabul qilish") },
        text = {
            OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text("Summa (qoldiq: ${money(remaining)})") }, singleLine = true)
        },
        confirmButton = {
            Button(onClick = { amount.toBigDecimalOrNull()?.let(onConfirm) }) { Text("Qabul qilish") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SalesFormScreen(docType: String, onBack: () -> Unit, onSaved: (Long) -> Unit, viewModel: SalesFormViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var customerExpanded by remember { mutableStateOf(false) }
    var productExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(docType) { viewModel.init(docType) }
    LaunchedEffect(state.savedDocId) { state.savedDocId?.let(onSaved) }

    ScreenScaffold(title = "Yangi: ${DOC_TYPE_LABELS[docType] ?: docType}", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }

            ExposedDropdownMenuBox(expanded = customerExpanded, onExpandedChange = { customerExpanded = it }) {
                OutlinedTextField(
                    value = state.customers.firstOrNull { it.id == state.customerId }?.name ?: "— tanlanmagan —",
                    onValueChange = {}, readOnly = true, label = { Text("Mijoz") },
                    modifier = Modifier.fillMaxWidth().menuAnchor(),
                    trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = customerExpanded) },
                )
                DropdownMenu(expanded = customerExpanded, onDismissRequest = { customerExpanded = false }) {
                    state.customers.forEach { c ->
                        DropdownMenuItem(text = { Text(c.name) }, onClick = { viewModel.setCustomer(c.id); customerExpanded = false })
                    }
                }
            }

            Row(modifier = Modifier.fillMaxWidth().padding(top = 10.dp)) {
                ExposedDropdownMenuBox(expanded = productExpanded, onExpandedChange = { productExpanded = it }, modifier = Modifier.weight(1f)) {
                    OutlinedTextField(
                        value = "+ Mahsulot qo'shish", onValueChange = {}, readOnly = true,
                        modifier = Modifier.fillMaxWidth().menuAnchor(),
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = productExpanded) },
                    )
                    DropdownMenu(expanded = productExpanded, onDismissRequest = { productExpanded = false }) {
                        state.products.forEach { p ->
                            DropdownMenuItem(text = { Text("${p.name} — ${money(p.salePrice)}") }, onClick = { viewModel.addLine(p); productExpanded = false })
                        }
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
                            onValueChange = { v -> v.toBigDecimalOrNull()?.let { viewModel.updateQuantity(line.product.id, it) } },
                            modifier = Modifier.width(80.dp),
                            singleLine = true,
                        )
                        TextButton(onClick = { viewModel.removeLine(line.product.id) }) { Text("✕") }
                    }
                }
            }

            Divider(modifier = Modifier.padding(vertical = 8.dp))
            Text("Jami: ${money(state.total)} so'm", style = MaterialTheme.typography.titleMedium)

            Row(modifier = Modifier.fillMaxWidth().padding(top = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { viewModel.save(false) }, enabled = !state.isSaving) { Text("Saqlash") }
                Button(onClick = { viewModel.save(true) }, enabled = !state.isSaving, colors = ButtonDefaults.buttonColors(containerColor = UzGreen)) {
                    Text("Saqlash va tasdiqlash")
                }
            }
        }
    }
}
