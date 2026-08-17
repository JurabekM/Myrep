package com.uzerp.mobile.ui.stock

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material.icons.filled.Warehouse
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.d
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.SearchField
import com.uzerp.mobile.ui.theme.UzAmber
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzRed
import com.uzerp.mobile.ui.theme.UzTeal

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
fun StockScreen(onBack: () -> Unit, viewModel: StockViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showTransfer by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Ombor qoldiqlari", onBack = onBack, fabIcon = Icons.Filled.SwapHoriz, onFabClick = { showTransfer = true }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            SearchField(state.search, viewModel::onSearchChange)
            Text(
                "Jami qiymat: ${money(state.totalValue)} so'm",
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp),
            )
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.rows.isEmpty() -> EmptyState("Qoldiq topilmadi.")
                else -> LazyColumn {
                    items(state.rows, key = { it.productId }) { row ->
                        ListRowCard(
                            title = row.name + if (row.isLow) "  ⚠" else "",
                            subtitle = "${row.sku ?: ""} · ${row.quantity} ${row.unit}",
                            trailing = money(row.stockValue),
                            leadingIcon = Icons.Filled.Warehouse,
                            iconTint = if (row.isLow) UzAmber else UzTeal,
                        )
                    }
                }
            }
        }
    }

    if (showTransfer) {
        TransferDialog(
            products = state.products,
            warehouses = state.warehouses,
            onDismiss = { showTransfer = false },
            onConfirm = { productId, from, to, qty ->
                viewModel.transfer(productId, from, to, qty)
                showTransfer = false
            },
        )
    }
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun TransferDialog(
    products: List<com.uzerp.mobile.data.local.entity.ProductEntity>,
    warehouses: List<com.uzerp.mobile.data.local.entity.WarehouseEntity>,
    onDismiss: () -> Unit,
    onConfirm: (Long, Long, Long, java.math.BigDecimal) -> Unit,
) {
    var productId by remember { mutableStateOf(products.firstOrNull()?.id) }
    var fromWarehouse by remember { mutableStateOf(warehouses.firstOrNull()?.id) }
    var toWarehouse by remember { mutableStateOf(warehouses.getOrNull(1)?.id ?: warehouses.firstOrNull()?.id) }
    var qty by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Ombordan omborga ko'chirish") },
        text = {
            Column {
                SimplePicker("Mahsulot", products.map { it.id to it.name }, productId) { productId = it }
                SimplePicker("Qayerdan", warehouses.map { it.id to it.name }, fromWarehouse) { fromWarehouse = it }
                SimplePicker("Qayerga", warehouses.map { it.id to it.name }, toWarehouse) { toWarehouse = it }
                OutlinedTextField(
                    value = qty, onValueChange = { qty = it }, label = { Text("Miqdor") },
                    singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
                )
            }
        },
        confirmButton = {
            Button(onClick = {
                val pid = productId
                val from = fromWarehouse
                val to = toWarehouse
                val amount = qty.toBigDecimalOrNull()
                if (pid != null && from != null && to != null && amount != null && amount.signum() > 0) {
                    onConfirm(pid, from, to, d(amount))
                }
            }) { Text("Ko'chirish") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}

@OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)
@Composable
private fun SimplePicker(label: String, options: List<Pair<Long, String>>, selected: Long?, onSelect: (Long) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val selectedLabel = options.firstOrNull { it.first == selected }?.second ?: ""
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(
            value = selectedLabel, onValueChange = {}, readOnly = true, label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
            modifier = Modifier.fillMaxWidth().padding(top = 6.dp).menuAnchor(),
        )
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { (id, name) ->
                DropdownMenuItem(text = { Text(name) }, onClick = { onSelect(id); expanded = false })
            }
        }
    }
}
