package com.smartmoliya.app.feature.payments.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.network.dto.PaymentDto
import com.smartmoliya.app.feature.expense.domain.Transaction
import java.text.NumberFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

private val Providers = listOf("click" to "Click", "payme" to "Payme", "uzum" to "Uzum Bank")

@Composable
fun PaymentsScreen(viewModel: PaymentsViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val formatter = remember { NumberFormat.getNumberInstance(Locale("uz", "UZ")) }

    var selectedProvider by remember { mutableStateOf(Providers.first()) }
    var amountText by remember { mutableStateOf("") }
    var walletMenuExpanded by remember { mutableStateOf(false) }
    var selectedWalletId by remember { mutableStateOf<String?>(null) }

    val selectedWallet = state.wallets.find { it.id == selectedWalletId } ?: state.wallets.firstOrNull()

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        item {
            Text(text = "Hamyonni to'ldirish", style = MaterialTheme.typography.titleLarge)
            if (BuildConfig.OFFLINE_MODE) {
                Text(
                    text = "Offline rejim: naqd pul kiritilishi daromad sifatida yoziladi",
                    style = MaterialTheme.typography.labelSmall
                )
            }
        }

        item {
            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    if (!BuildConfig.OFFLINE_MODE) {
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Providers.forEach { provider ->
                                FilterChip(
                                    selected = selectedProvider == provider,
                                    onClick = { selectedProvider = provider },
                                    label = { Text(provider.second) }
                                )
                            }
                        }
                    }

                    TextButton(onClick = { walletMenuExpanded = true }) {
                        Text("Hamyon: ${selectedWallet?.name ?: "mavjud emas"}")
                    }
                    DropdownMenu(expanded = walletMenuExpanded, onDismissRequest = { walletMenuExpanded = false }) {
                        state.wallets.forEach { wallet ->
                            DropdownMenuItem(
                                text = { Text(wallet.name) },
                                onClick = { selectedWalletId = wallet.id; walletMenuExpanded = false }
                            )
                        }
                    }

                    OutlinedTextField(
                        value = amountText,
                        onValueChange = { amountText = it.filter { c -> c.isDigit() } },
                        label = { Text("Summa (so'm)") },
                        modifier = Modifier.fillMaxWidth()
                    )

                    Button(
                        onClick = {
                            val amount = amountText.toDoubleOrNull()
                            val walletId = selectedWallet?.id
                            if (amount != null && amount > 0 && walletId != null) {
                                viewModel.topUp(walletId, selectedProvider.first, amount)
                                amountText = ""
                            }
                        },
                        enabled = !state.isLoading && selectedWallet != null && amountText.isNotBlank(),
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    ) {
                        if (state.isLoading) {
                            CircularProgressIndicator(modifier = Modifier.padding(2.dp))
                        } else {
                            Text(
                                if (BuildConfig.OFFLINE_MODE) "To'ldirish (naqd)"
                                else "To'ldirish (${selectedProvider.second})"
                            )
                        }
                    }

                    state.message?.let { message ->
                        Text(text = message, style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        }

        item {
            Text(text = "To'lovlar tarixi", style = MaterialTheme.typography.titleLarge)
        }

        if (BuildConfig.OFFLINE_MODE) {
            if (state.localTopUps.isEmpty()) {
                item { Text(text = "Hozircha to'ldirishlar yo'q") }
            } else {
                items(state.localTopUps, key = { it.id }) { topUp ->
                    LocalTopUpRow(topUp, formatter)
                }
            }
        } else {
            if (state.payments.isEmpty()) {
                item { Text(text = "Hozircha to'lovlar yo'q") }
            } else {
                items(state.payments, key = { it.id }) { payment ->
                    PaymentRow(payment, formatter)
                }
            }
        }
    }
}

@Composable
private fun LocalTopUpRow(topUp: Transaction, formatter: NumberFormat) {
    val dateFormat = remember { SimpleDateFormat("dd.MM.yyyy HH:mm", Locale.getDefault()) }
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(text = "Naqd to'ldirish")
                Text(
                    text = dateFormat.format(Date(topUp.occurredAt)),
                    style = MaterialTheme.typography.labelSmall
                )
            }
            Text(text = "+${formatter.format(topUp.amount)} ${topUp.currency}")
        }
    }
}

@Composable
private fun PaymentRow(payment: PaymentDto, formatter: NumberFormat) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(12.dp),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(text = payment.provider.replaceFirstChar { it.uppercase() })
                Text(text = statusLabel(payment.status), style = MaterialTheme.typography.labelSmall)
            }
            Text(text = "+${formatter.format(payment.amount)} ${payment.currency}")
        }
    }
}

private fun statusLabel(status: String): String = when (status.lowercase()) {
    "paid" -> "To'landi ✅"
    "pending" -> "Kutilmoqda…"
    "failed" -> "Muvaffaqiyatsiz"
    "canceled" -> "Bekor qilingan"
    else -> status
}
