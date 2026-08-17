package com.uzerp.mobile.ui.cash

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.StatusChip
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzRed

@Composable
fun CashScreen(onBack: () -> Unit, viewModel: CashViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showExpense by remember { mutableStateOf(false) }
    var showIncome by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Kassa / Bank", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Row(modifier = Modifier.fillMaxWidth().padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                Card(modifier = Modifier.weight(1f), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text("Kassa (5010)", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall)
                        Text(money(state.cashBalance), style = MaterialTheme.typography.titleMedium, color = UzGreen)
                    }
                }
                Card(modifier = Modifier.weight(1f), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Text("Bank (5110)", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelSmall)
                        Text(money(state.bankBalance), style = MaterialTheme.typography.titleMedium)
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = { showExpense = true }, colors = ButtonDefaults.buttonColors(containerColor = UzRed), modifier = Modifier.weight(1f)) {
                    Text("Xarajat")
                }
                Button(onClick = { showIncome = true }, colors = ButtonDefaults.buttonColors(containerColor = UzGreen), modifier = Modifier.weight(1f)) {
                    Text("Kirim")
                }
            }
            state.error?.let { ErrorBanner(it) }
            state.message?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("To'lovlar yo'q.")
                else -> LazyColumn(modifier = Modifier.padding(top = 8.dp)) {
                    items(state.items, key = { it.id }) { payment ->
                        ListRowCard(
                            title = payment.number,
                            subtitle = "${payment.method} · ${payment.note.ifBlank { payment.refType }}",
                            trailing = money(payment.amount),
                            badge = { StatusChip(payment.paymentType) },
                            leadingIcon = Icons.Filled.Payments,
                            iconTint = if (payment.paymentType == "in") UzGreen else UzRed,
                        )
                    }
                }
            }
        }
    }

    if (showExpense) {
        MoneyDialog("Xarajat", onDismiss = { showExpense = false }, onConfirm = { amount, note, method ->
            viewModel.expense(amount, note, method); showExpense = false
        })
    }
    if (showIncome) {
        MoneyDialog("Boshqa kirim", onDismiss = { showIncome = false }, onConfirm = { amount, note, method ->
            viewModel.income(amount, note, method); showIncome = false
        })
    }
}

@Composable
private fun MoneyDialog(title: String, onDismiss: () -> Unit, onConfirm: (java.math.BigDecimal, String, String) -> Unit) {
    var amount by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var method by remember { mutableStateOf("cash") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column {
                OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text("Summa *") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = note, onValueChange = { note = it }, label = { Text("Izoh *") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                Row(modifier = Modifier.padding(top = 8.dp)) {
                    TextButton(onClick = { method = "cash" }) { Text(if (method == "cash") "● Naqd" else "○ Naqd") }
                    TextButton(onClick = { method = "bank" }) { Text(if (method == "bank") "● Bank" else "○ Bank") }
                }
            }
        },
        confirmButton = {
            Button(onClick = {
                val value = amount.toBigDecimalOrNull()
                if (value != null && value.signum() > 0 && note.isNotBlank()) onConfirm(value, note, method)
            }) { Text("Saqlash") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}
