package com.uzerp.mobile.ui.products

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.SearchField
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzViolet

@Composable
fun ProductsScreen(
    onBack: () -> Unit,
    onOpenProduct: (Long) -> Unit,
    onAddProduct: () -> Unit,
    viewModel: ProductsViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    // Har safar bu ekran qayta ko'rinishga kirganda (masalan, forma ekranidan
    // qaytganda) ro'yxatni yangilaydi — ViewModel NavBackStackEntry'ga
    // bog'langani uchun saqlanib qoladi va o'z-o'zidan yangilanmaydi.
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Mahsulotlar", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = onAddProduct) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            SearchField(state.search, viewModel::onSearchChange, "Nom, SKU yoki shtrix-kod")
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Mahsulot topilmadi. + tugmasi bilan qo'shing.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { product ->
                        ListRowCard(
                            title = product.name,
                            subtitle = "${product.sku ?: ""} · ${product.unit} · tannarx ${money(product.costPrice)}",
                            trailing = money(product.salePrice),
                            onClick = { onOpenProduct(product.id) },
                            leadingIcon = Icons.Filled.Inventory2,
                            iconTint = UzViolet,
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun ProductFormScreen(
    productId: Long?,
    onBack: () -> Unit,
    viewModel: ProductFormViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()

    LaunchedEffect(productId) { if (productId != null) viewModel.load(productId) }
    LaunchedEffect(state.saved) { if (state.saved) onBack() }

    ScreenScaffold(title = if (productId == null) "Yangi mahsulot" else "Mahsulotni tahrirlash", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            state.error?.let { ErrorBanner(it) }

            LabeledField("Nomi *", state.name) { v -> viewModel.update { it.copy(name = v) } }
            LabeledField("Shtrix-kod", state.barcode) { v -> viewModel.update { it.copy(barcode = v) } }
            LabeledField("O'lchov birligi", state.unit) { v -> viewModel.update { it.copy(unit = v) } }
            LabeledField("Sotish narxi", state.salePrice, numeric = true) { v -> viewModel.update { it.copy(salePrice = v) } }
            LabeledField("Tannarx", state.costPrice, numeric = true) { v -> viewModel.update { it.copy(costPrice = v) } }
            LabeledField("QQS stavkasi (%)", state.vatRate, numeric = true) { v -> viewModel.update { it.copy(vatRate = v) } }
            LabeledField("Minimal zaxira", state.minStock, numeric = true) { v -> viewModel.update { it.copy(minStock = v) } }

            Button(
                onClick = viewModel::save,
                enabled = !state.isSaving && state.name.isNotBlank(),
                modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
            ) { Text("Saqlash") }
        }
    }
}

@Composable
internal fun LabeledField(label: String, value: String, numeric: Boolean = false, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
        keyboardOptions = if (numeric) {
            androidx.compose.foundation.text.KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Decimal)
        } else {
            androidx.compose.foundation.text.KeyboardOptions.Default
        },
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = UzAccent, unfocusedBorderColor = MaterialTheme.colorScheme.outline),
    )
}
