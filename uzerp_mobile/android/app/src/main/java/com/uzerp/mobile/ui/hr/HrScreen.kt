package com.uzerp.mobile.ui.hr

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Badge
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
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
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.common.EmptyState
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ListRowCard
import com.uzerp.mobile.ui.common.LoadingState
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.common.SearchField
import com.uzerp.mobile.ui.theme.UzViolet

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HrScreen(onBack: () -> Unit, viewModel: HrViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var showAdd by remember { mutableStateOf(false) }
    LaunchedEffect(Unit) { viewModel.reload() }

    ScreenScaffold(title = "Xodimlar", onBack = onBack, fabIcon = Icons.Filled.Add, onFabClick = { showAdd = true }) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            SearchField(state.search, viewModel::onSearchChange)
            state.error?.let { ErrorBanner(it) }
            when {
                state.isLoading -> LoadingState()
                state.employees.isEmpty() -> EmptyState("Xodimlar yo'q.")
                else -> LazyColumn {
                    items(state.employees, key = { it.id }) { emp ->
                        ListRowCard(
                            title = emp.fullName,
                            subtitle = "${emp.code ?: ""} · ${emp.position.ifBlank { "—" }}",
                            trailing = money(emp.salary),
                            leadingIcon = Icons.Filled.Badge,
                            iconTint = UzViolet,
                        )
                    }
                }
            }
        }
    }

    if (showAdd) {
        AddEmployeeDialog(
            departments = state.departments.map { it.id to it.name },
            onDismiss = { showAdd = false },
            onCreateDepartment = viewModel::createDepartment,
            onConfirm = { name, deptId, position, salary, phone ->
                viewModel.createEmployee(name, deptId, position, salary, phone)
                showAdd = false
            },
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun AddEmployeeDialog(
    departments: List<Pair<Long, String>>,
    onDismiss: () -> Unit,
    onCreateDepartment: (String) -> Unit,
    onConfirm: (String, Long?, String, java.math.BigDecimal, String) -> Unit,
) {
    var name by remember { mutableStateOf("") }
    var position by remember { mutableStateOf("") }
    var salary by remember { mutableStateOf("") }
    var phone by remember { mutableStateOf("") }
    var deptId by remember { mutableStateOf(departments.firstOrNull()?.first) }
    var deptExpanded by remember { mutableStateOf(false) }
    var newDept by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Yangi xodim") },
        text = {
            Column {
                OutlinedTextField(value = name, onValueChange = { name = it }, label = { Text("F.I.Sh. *") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(value = position, onValueChange = { position = it }, label = { Text("Lavozim") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                OutlinedTextField(value = salary, onValueChange = { salary = it }, label = { Text("Oylik maosh") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))
                OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("Telefon") }, singleLine = true, modifier = Modifier.fillMaxWidth().padding(top = 8.dp))

                if (departments.isNotEmpty()) {
                    ExposedDropdownMenuBox(expanded = deptExpanded, onExpandedChange = { deptExpanded = it }, modifier = Modifier.padding(top = 8.dp)) {
                        OutlinedTextField(
                            value = departments.firstOrNull { it.first == deptId }?.second ?: "",
                            onValueChange = {}, readOnly = true, label = { Text("Bo'lim") },
                            modifier = Modifier.fillMaxWidth().menuAnchor(),
                            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded = deptExpanded) },
                        )
                        DropdownMenu(expanded = deptExpanded, onDismissRequest = { deptExpanded = false }) {
                            departments.forEach { (id, n) -> DropdownMenuItem(text = { Text(n) }, onClick = { deptId = id; deptExpanded = false }) }
                        }
                    }
                } else {
                    NewDepartmentRow(newDept, { newDept = it }, onCreateDepartment)
                }
            }
        },
        confirmButton = {
            Button(onClick = {
                val salaryValue = salary.toBigDecimalOrNull() ?: java.math.BigDecimal.ZERO
                if (name.isNotBlank()) onConfirm(name, deptId, position, salaryValue, phone)
            }) { Text("Qo'shish") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}

@Composable
private fun NewDepartmentRow(value: String, onChange: (String) -> Unit, onCreate: (String) -> Unit) {
    androidx.compose.foundation.layout.Row(modifier = Modifier.padding(top = 8.dp)) {
        OutlinedTextField(value = value, onValueChange = onChange, label = { Text("Yangi bo'lim nomi") }, singleLine = true, modifier = Modifier.weight(1f))
        TextButton(onClick = { if (value.isNotBlank()) onCreate(value) }) { Text("Qo'shish") }
    }
}
