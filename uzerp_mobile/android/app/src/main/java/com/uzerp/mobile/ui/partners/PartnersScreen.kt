package com.uzerp.mobile.ui.partners

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.People
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
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
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.SearchField
import com.uzerp.mobile.ui.theme.UzCyan
import com.uzerp.mobile.ui.theme.UzIndigo

@Composable
fun CustomersScreen(onBack: () -> Unit, viewModel: CustomersViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showAdd by remember { mutableStateOf(false) }

    ScreenScaffold(title = "Mijozlar", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = { showAdd = true }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            SearchField(state.search, viewModel::onSearchChange)
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Mijozlar yo'q.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { c ->
                        ListRowCard(
                            title = c.name, subtitle = c.phone.ifBlank { c.tin },
                            trailing = if (c.discountPercent.signum() > 0) "${c.discountPercent}%" else null,
                            leadingIcon = Icons.Filled.People, iconTint = UzCyan,
                        )
                    }
                }
            }
        }
    }
    if (showAdd) {
        AddPartnerDialog("Yangi mijoz", onDismiss = { showAdd = false }, onConfirm = { n, p -> viewModel.create(n, p); showAdd = false })
    }
}

@Composable
fun SuppliersScreen(onBack: () -> Unit, viewModel: SuppliersViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showAdd by remember { mutableStateOf(false) }

    ScreenScaffold(title = "Ta'minotchilar", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = { showAdd = true }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            SearchField(state.search, viewModel::onSearchChange)
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Ta'minotchilar yo'q.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { s ->
                        ListRowCard(title = s.name, subtitle = s.phone.ifBlank { s.tin }, leadingIcon = Icons.Filled.Storefront, iconTint = UzIndigo)
                    }
                }
            }
        }
    }
    if (showAdd) {
        AddPartnerDialog("Yangi ta'minotchi", onDismiss = { showAdd = false }, onConfirm = { n, p -> viewModel.create(n, p); showAdd = false })
    }
}

@Composable
private fun AddPartnerDialog(title: String, onDismiss: () -> Unit, onConfirm: (String, String) -> Unit) {
    var name by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(title) },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nomi *") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Telefon") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
            }
        },
        confirmButton = { Button(onClick = { if (name.isNotBlank()) onConfirm(name, phone) }) { Text("Qo'shish") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}
