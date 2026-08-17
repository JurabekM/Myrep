package com.uzerp.mobile.ui.pos

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Divider
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted

private val PAYMENT_METHODS = listOf("cash" to "Naqd", "card" to "Karta", "click" to "Click", "payme" to "Payme")

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PosScreen(onBack: () -> Unit, viewModel: PosViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var method by remember { mutableStateOf(PAYMENT_METHODS.first()) }
    var methodExpanded by remember { mutableStateOf(false) }
    var productExpanded by remember { mutableStateOf(false) }

    LaunchedEffect(state.message) {
        if (state.message != null) {
            viewModel.clearMessages()
        }
    }

    ScreenScaffold(title = "POS kassa", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }

            OutlinedTextField(
                value = state.barcodeInput,
                onValueChange = viewModel::onBarcodeChange,
                label = { Text("Shtrix-kod (skanerlang yoki kiriting)") },
                singleLine = true,
                modifier = Modifier.fillMaxWidth(),
                trailingIcon = {
                    androidx.compose.material3.TextButton(onClick = viewModel::addByBarcode) { Text("Qo'shish") }
                },
            )

            Row(modifier = Modifier.fillMaxWidth().padding(top = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                ExposedDropdownMenuBox(
                    expanded = productExpanded,
                    onExpandedChange = { productExpanded = it },
                    modifier = Modifier.weight(1f),
                ) {
                    OutlinedTextField(
                        value = "Mahsulot tanlash",
                        onValueChange = {},
                        readOnly = true,
                        modifier = Modifier.fillMaxWidth().menuAnchor(),
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = productExpanded) },
                    )
                    DropdownMenu(expanded = productExpanded, onDismissRequest = { productExpanded = false }) {
                        state.allProducts.forEach { product ->
                            DropdownMenuItem(
                                text = { Text("${product.name} — ${money(product.salePrice)}") },
                                onClick = { viewModel.addProduct(product); productExpanded = false },
                            )
                        }
                    }
                }
            }

            Divider(modifier = Modifier.padding(vertical = 12.dp))

            if (state.cart.isEmpty()) {
                EmptyState("Savat bo'sh — mahsulot qo'shing.")
            } else {
                LazyColumn(modifier = Modifier.weight(1f)) {
                    items(state.cart, key = { it.product.id }) { line ->
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(vertical = 8.dp),
                            verticalAlignment = Alignment.CenterVertically,
                        ) {
                            Column(modifier = Modifier.weight(1f)) {
                                Text(line.product.name, color = MaterialTheme.colorScheme.onSurface)
                                Text("${line.quantity} x ${money(line.product.salePrice)}", color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                            }
                            Text(money(line.lineTotal), fontWeight = FontWeight.SemiBold)
                            IconButton(onClick = { viewModel.removeLine(line.product.id) }) {
                                Icon(Icons.Filled.Delete, contentDescription = "O'chirish")
                            }
                        }
                    }
                }
            }

            Divider(modifier = Modifier.padding(vertical = 8.dp))
            Text(
                "${money(state.total)} so'm",
                style = MaterialTheme.typography.titleLarge,
                color = UzGreen,
                modifier = Modifier.fillMaxWidth(),
            )

            Row(modifier = Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                ExposedDropdownMenuBox(
                    expanded = methodExpanded,
                    onExpandedChange = { methodExpanded = it },
                    modifier = Modifier.weight(1f),
                ) {
                    OutlinedTextField(
                        value = method.second, onValueChange = {}, readOnly = true, label = { Text("To'lov usuli") },
                        modifier = Modifier.fillMaxWidth().menuAnchor(),
                        trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = methodExpanded) },
                    )
                    DropdownMenu(expanded = methodExpanded, onDismissRequest = { methodExpanded = false }) {
                        PAYMENT_METHODS.forEach { m ->
                            DropdownMenuItem(text = { Text(m.second) }, onClick = { method = m; methodExpanded = false })
                        }
                    }
                }
            }

            Button(
                onClick = { viewModel.checkout(method.first) },
                enabled = state.cart.isNotEmpty() && !state.isCheckingOut,
                colors = ButtonDefaults.buttonColors(containerColor = UzGreen),
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            ) { Text("SOTISH") }
        }
    }
}
