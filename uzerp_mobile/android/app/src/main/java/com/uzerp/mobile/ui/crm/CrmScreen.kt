package com.uzerp.mobile.ui.crm

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
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
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.StatusChip

private val LEAD_STATUS_LABELS = listOf(
    "new" to "Yangi", "contacted" to "Aloqa qilindi", "qualified" to "Malakali", "won" to "Yutildi", "lost" to "Yo'qotildi",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun CrmLeadsScreen(onBack: () -> Unit, viewModel: CrmViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showAdd by remember { mutableStateOf(false) }

    ScreenScaffold(title = "Leadlar (savdo voronkasi)", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = { showAdd = true }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            state.error?.let { ErrorBanner(it) }
            state.message?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.items.isEmpty() -> EmptyState("Leadlar yo'q.")
                else -> LazyColumn {
                    items(state.items, key = { it.id }) { lead ->
                        LeadCard(lead, onStatusChange = { status -> viewModel.changeStatus(lead.id, status) })
                    }
                }
            }
        }
    }

    if (showAdd) {
        var name by remember { mutableStateOf("") }
        var phone by remember { mutableStateOf("") }
        var source by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showAdd = false },
            title = { Text("Yangi lead") },
            text = {
                Column {
                    OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("Nomi *") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Telefon") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                    OutlinedTextField(value = source, onValueChange = { source = it }, label = { Text("Manba") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                }
            },
            confirmButton = {
                Button(onClick = { if (name.isNotBlank()) { viewModel.createLead(name, phone, source); showAdd = false } }) { Text("Qo'shish") }
            },
            dismissButton = { TextButton(onClick = { showAdd = false }) { Text("Bekor qilish") } },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun LeadCard(lead: com.uzerp.mobile.data.local.entity.LeadEntity, onStatusChange: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    val finished = lead.status in setOf("won", "lost")

    Card(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(lead.name, color = MaterialTheme.colorScheme.onSurface)
                    if (lead.phone.isNotBlank()) Text(lead.phone, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                }
                StatusChip(lead.status)
            }
            if (!finished) {
                Row(modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
                    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }, modifier = Modifier.weight(1f)) {
                        OutlinedTextField(
                            value = "Holatni o'zgartirish", onValueChange = {}, readOnly = true,
                            modifier = Modifier.fillMaxWidth().menuAnchor(),
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = expanded) },
                        )
                        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                            LEAD_STATUS_LABELS.forEach { (value, label) ->
                                DropdownMenuItem(text = { Text(label) }, onClick = { onStatusChange(value); expanded = false })
                            }
                        }
                    }
                }
            }
        }
    }
}
