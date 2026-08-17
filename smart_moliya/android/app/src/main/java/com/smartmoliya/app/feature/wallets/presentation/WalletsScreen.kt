package com.smartmoliya.app.feature.wallets.presentation

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.ui.components.EmptyState
import com.smartmoliya.app.ui.components.GradientCard
import com.smartmoliya.app.ui.components.formatAmount

/** Har hamyonga o'z gradienti - kartalar vizual farqlanadi. */
private val WalletGradients = listOf(
    listOf(Color(0xFF059669), Color(0xFF34D399)),
    listOf(Color(0xFF2563EB), Color(0xFF38BDF8)),
    listOf(Color(0xFF7C3AED), Color(0xFFC084FC)),
    listOf(Color(0xFFD97706), Color(0xFFFBBF24)),
    listOf(Color(0xFFDB2777), Color(0xFFF472B6)),
    listOf(Color(0xFF0891B2), Color(0xFF22D3EE))
)

@Composable
fun WalletsScreen(viewModel: WalletsViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var showAddDialog by remember { mutableStateOf(false) }

    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        floatingActionButton = {
            FloatingActionButton(
                onClick = { showAddDialog = true },
                containerColor = MaterialTheme.colorScheme.primary
            ) {
                Icon(Icons.Default.Add, contentDescription = "Hamyon qo'shish")
            }
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            item {
                Text(text = "Hamyonlar", style = MaterialTheme.typography.headlineSmall)
                if (state.isLoading) {
                    CircularProgressIndicator(modifier = Modifier.padding(top = 8.dp))
                }
                state.errorMessage?.let {
                    Text(
                        text = it,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }

            if (state.wallets.isEmpty() && !state.isLoading) {
                item {
                    EmptyState(emoji = "👛", text = "Birinchi hamyoningizni + tugmasi bilan yarating")
                }
            } else {
                items(state.wallets, key = { it.id }) { wallet ->
                    val gradient = WalletGradients[
                        Math.floorMod(wallet.id.hashCode(), WalletGradients.size)
                    ]
                    WalletCard(
                        wallet = wallet,
                        gradient = gradient,
                        onDelete = { viewModel.deleteWallet(wallet.id) }
                    )
                }
            }
        }
    }

    if (showAddDialog) {
        AddWalletDialog(
            onDismiss = { showAddDialog = false },
            onConfirm = { name, currency ->
                viewModel.createWallet(name, currency)
                showAddDialog = false
            }
        )
    }
}

@Composable
private fun WalletCard(wallet: Wallet, gradient: List<Color>, onDelete: () -> Unit) {
    GradientCard(gradient = gradient) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(
                imageVector = Icons.Default.AccountBalanceWallet,
                contentDescription = null,
                tint = Color.White.copy(alpha = 0.9f)
            )
            Text(
                text = wallet.name,
                style = MaterialTheme.typography.titleMedium,
                color = Color.White,
                modifier = Modifier
                    .weight(1f)
                    .padding(start = 10.dp)
            )
            IconButton(onClick = onDelete) {
                Icon(
                    imageVector = Icons.Default.DeleteOutline,
                    contentDescription = "O'chirish",
                    tint = Color.White.copy(alpha = 0.8f)
                )
            }
        }
        Spacer(modifier = Modifier.height(14.dp))
        Text(
            text = formatAmount(wallet.balance),
            style = MaterialTheme.typography.headlineMedium,
            color = Color.White
        )
        Text(
            text = wallet.currency,
            style = MaterialTheme.typography.labelLarge,
            color = Color.White.copy(alpha = 0.85f)
        )
    }
}

@Composable
private fun AddWalletDialog(onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var currency by remember { mutableStateOf("UZS") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Yangi hamyon") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedTextField(
                    value = name,
                    onValueChange = { name = it },
                    label = { Text("Nomi (masalan: Asosiy, Jamg'arma)") },
                    modifier = Modifier.fillMaxWidth()
                )
                OutlinedTextField(
                    value = currency,
                    onValueChange = { currency = it.uppercase().take(3) },
                    label = { Text("Valyuta") },
                    modifier = Modifier.fillMaxWidth()
                )
            }
        },
        confirmButton = {
            TextButton(onClick = { if (name.isNotBlank()) onConfirm(name, currency) }) {
                Text("Qo'shish")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text("Bekor qilish") }
        }
    )
}
