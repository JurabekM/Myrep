package com.agrovision.mobile.ui.admin

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import com.agrovision.mobile.ui.common.DataTable
import com.agrovision.mobile.ui.common.SectionTitle
import com.agrovision.mobile.ui.nav.AppScaffold
import com.agrovision.mobile.ui.nav.logoutAndReturn

@Composable
fun AdminScreen(navController: NavHostController, viewModel: AdminViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    val users by viewModel.users.collectAsState()
    val audit by viewModel.audit.collectAsState()
    var showRestoreConfirm by remember { mutableStateOf<String?>(null) }

    AppScaffold(navController, "Administrator paneli", onLogout = { navController.logoutAndReturn() }) { padding ->
        Column(Modifier.padding(padding).padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(16.dp)) {
            state.message?.let { Card { Text(it, Modifier.padding(10.dp)) } }

            SectionTitle("Foydalanuvchilar")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Login", "Rol", "Faol"),
                        rows = users.map { listOf(it.username, it.role, if (it.active) "Ha" else "Yo'q") },
                    )
                }
            }

            var newUsername by remember { mutableStateOf("") }
            var newFullName by remember { mutableStateOf("") }
            var newPassword by remember { mutableStateOf("") }
            var newRole by remember { mutableStateOf("viewer") }
            ElevatedCard {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Yangi foydalanuvchi", style = MaterialTheme.typography.titleSmall)
                    OutlinedTextField(newUsername, { newUsername = it }, label = { Text("Login") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(newFullName, { newFullName = it }, label = { Text("F.I.Sh.") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(newPassword, { newPassword = it }, label = { Text("Parol") }, modifier = Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        listOf("admin", "manager", "viewer").forEach { role ->
                            FilterChip(selected = newRole == role, onClick = { newRole = role }, label = { Text(role) })
                        }
                    }
                    Button(onClick = {
                        viewModel.createUser(newUsername, newFullName, newPassword, newRole)
                        newUsername = ""; newFullName = ""; newPassword = ""
                    }) { Text("Qo'shish") }
                }
            }

            var toggleUsername by remember { mutableStateOf("") }
            var resetPassword by remember { mutableStateOf("") }
            ElevatedCard {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Faollik / parolni tiklash", style = MaterialTheme.typography.titleSmall)
                    OutlinedTextField(toggleUsername, { toggleUsername = it }, label = { Text("Login") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(resetPassword, { resetPassword = it }, label = { Text("Yangi parol") }, modifier = Modifier.fillMaxWidth())
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedButton(onClick = { viewModel.toggleActive(toggleUsername) }) { Text("Faollikni almashtirish") }
                        OutlinedButton(onClick = { viewModel.resetPassword(toggleUsername, resetPassword) }) { Text("Parolni tiklash") }
                    }
                }
            }

            SectionTitle("Zaxira nusxa (Backup / Restore)")
            ElevatedCard {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Button(onClick = viewModel::createBackup) { Text("Zaxira yaratish") }
                    DataTable(
                        headers = listOf("Fayl", "Hajm (KB)", "Sana"),
                        rows = state.backups.map { listOf(it.name, "${it.sizeKb}", it.createdAt) },
                    )
                    state.backups.forEach { backup ->
                        OutlinedButton(onClick = { showRestoreConfirm = backup.name }) { Text("Tiklash: ${backup.name}") }
                    }
                }
            }

            SectionTitle("Audit jurnali (so'nggi 100)")
            ElevatedCard {
                Column(Modifier.padding(12.dp)) {
                    DataTable(
                        headers = listOf("Foydalanuvchi", "Amal", "Tafsilot"),
                        rows = audit.map { listOf(it.username, it.action, it.details.take(40)) },
                    )
                }
            }
        }
    }

    showRestoreConfirm?.let { name ->
        AlertDialog(
            onDismissRequest = { showRestoreConfirm = null },
            title = { Text("Bazani tiklash") },
            text = { Text("\"$name\" zaxirasidan tiklansinmi? Ilova qayta ishga tushadi.") },
            confirmButton = {
                TextButton(onClick = { viewModel.restoreBackup(name) }) { Text("Tiklash") }
            },
            dismissButton = { TextButton(onClick = { showRestoreConfirm = null }) { Text("Bekor qilish") } },
        )
    }
}
