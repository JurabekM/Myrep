package com.smartmoliya.app.feature.expense.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.feature.expense.domain.Category
import com.smartmoliya.app.feature.expense.domain.TransactionType
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.ui.components.EmptyState
import com.smartmoliya.app.ui.components.TransactionRow
import com.smartmoliya.app.ui.components.formatShortDate

@Composable
fun ExpenseScreen(viewModel: ExpenseViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }
    val categoriesById = remember(state.categories) { state.categories.associateBy { it.id } }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Tranzaksiya qo'shish")
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            item {
                Text(text = "Tranzaksiyalar", style = MaterialTheme.typography.headlineSmall)
            }

            if (state.transactions.isEmpty()) {
                item {
                    EmptyState(
                        emoji = "🧾",
                        text = "Hozircha yozuvlar yo'q.\n+ tugmasi bilan birinchi daromad yoki xarajatni kiriting"
                    )
                }
            } else {
                items(state.transactions, key = { it.id }) { transaction ->
                    val category = transaction.categoryId?.let { categoriesById[it] }
                    val isIncome = transaction.type == TransactionType.INCOME
                    TransactionRow(
                        title = transaction.note ?: category?.name ?: if (isIncome) "Daromad" else "Xarajat",
                        subtitle = listOfNotNull(category?.name, formatShortDate(transaction.occurredAt))
                            .joinToString(" • "),
                        amount = transaction.amount,
                        currency = transaction.currency,
                        isIncome = isIncome,
                        icon = category?.icon,
                        trailing = {
                            IconButton(
                                onClick = { viewModel.deleteTransaction(transaction.id) },
                                modifier = Modifier.padding(0.dp)
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Close,
                                    contentDescription = "O'chirish",
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    )
                }
            }
        }
    }

    if (showAddDialog && state.wallets.isNotEmpty()) {
        AddTransactionDialog(
            wallets = state.wallets,
            categories = state.categories,
            onDismiss = { showAddDialog = false },
            onConfirm = { walletId, categoryId, type, amount, note ->
                viewModel.addTransaction(walletId, categoryId, type, amount, note)
                showAddDialog = false
            }
        )
    } else if (showAddDialog) {
        AlertDialog(
            onDismissRequest = { showAddDialog = false },
            title = { Text("Hamyon kerak") },
            text = { Text("Avval \"Hamyonlar\" bo'limida hamyon yarating") },
            confirmButton = {
                TextButton(onClick = { showAddDialog = false }) { Text("Tushunarli") }
            }
        )
    }
}

@Composable
private fun AddTransactionDialog(
    wallets: List<Wallet>,
    categories: List<Category>,
    onDismiss: () -> Unit,
    onConfirm: (String, String?, TransactionType, Double, String?) -> Unit
) {
    var selectedWallet by remember { mutableStateOf(wallets.first()) }
    var selectedCategory by remember { mutableStateOf<Category?>(null) }
    var type by remember { mutableStateOf(TransactionType.EXPENSE) }
    var amountText by remember { mutableStateOf("") }
    var note by remember { mutableStateOf("") }
    var walletMenuExpanded by remember { mutableStateOf(false) }
    var categoryMenuExpanded by remember { mutableStateOf(false) }

    val filteredCategories = categories.filter { it.type.equals(type.name, ignoreCase = true) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Yangi tranzaksiya") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = type == TransactionType.EXPENSE,
                        onClick = { type = TransactionType.EXPENSE; selectedCategory = null },
                        label = { Text("Xarajat") }
                    )
                    FilterChip(
                        selected = type == TransactionType.INCOME,
                        onClick = { type = TransactionType.INCOME; selectedCategory = null },
                        label = { Text("Daromad") }
                    )
                }

                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it.filter { c -> c.isDigit() || c == '.' } },
                    label = { Text("Summa (so'm)") },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = note,
                    onValueChange = { note = it },
                    label = { Text("Izoh (ixtiyoriy)") },
                    modifier = Modifier.fillMaxWidth()
                )

                TextButton(onClick = { walletMenuExpanded = true }) {
                    Text("Hamyon: ${selectedWallet.name}")
                }
                DropdownMenu(expanded = walletMenuExpanded, onDismissRequest = { walletMenuExpanded = false }) {
                    wallets.forEach { wallet ->
                        DropdownMenuItem(
                            text = { Text(wallet.name) },
                            onClick = { selectedWallet = wallet; walletMenuExpanded = false }
                        )
                    }
                }

                TextButton(onClick = { categoryMenuExpanded = true }) {
                    Text("Kategoriya: ${selectedCategory?.name ?: "tanlanmagan"}")
                }
                DropdownMenu(expanded = categoryMenuExpanded, onDismissRequest = { categoryMenuExpanded = false }) {
                    filteredCategories.forEach { category ->
                        DropdownMenuItem(
                            text = { Text(category.name) },
                            onClick = { selectedCategory = category; categoryMenuExpanded = false }
                        )
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = {
                val amount = amountText.toDoubleOrNull()
                if (amount != null && amount > 0) {
                    onConfirm(selectedWallet.id, selectedCategory?.id, type, amount, note.ifBlank { null })
                }
            }) { Text("Saqlash") }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Bekor qilish") }
        }
    )
}
