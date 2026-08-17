package com.agrovision.app.ui.screens

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.navigation.NavHostController
import com.agrovision.app.core.Fmt
import com.agrovision.app.core.Rbac
import com.agrovision.app.data.local.AuditLogEntity
import com.agrovision.app.data.local.TableCountRow
import com.agrovision.app.data.local.UserEntity
import com.agrovision.app.data.repo.AuthRepository
import com.agrovision.app.data.repo.BackupFile
import com.agrovision.app.data.repo.BackupRepository
import com.agrovision.app.data.repo.BootstrapRepository
import com.agrovision.app.ui.common.*
import com.agrovision.app.ui.nav.AppScaffold
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class AdminUiState(
    val backups: List<BackupFile> = emptyList(),
    val tableCounts: List<TableCountRow> = emptyList(),
    val hasDemoData: Boolean = false,
    val busy: Boolean = false,
    val message: String? = null,
    val isError: Boolean = false,
    val seedingStep: String? = null,
)

@HiltViewModel
class AdminViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val backupRepository: BackupRepository,
    private val bootstrapRepository: BootstrapRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AdminUiState())
    val state: StateFlow<AdminUiState> = _state.asStateFlow()

    val users: StateFlow<List<UserEntity>> = authRepository.observeUsers()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val audit: StateFlow<List<AuditLogEntity>> = authRepository.observeAudit(150)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun refresh() {
        viewModelScope.launch {
            _state.value = _state.value.copy(
                backups = backupRepository.list(),
                tableCounts = bootstrapRepository.tableCounts(),
                hasDemoData = bootstrapRepository.hasDemoData(),
            )
        }
    }

    private fun report(message: String, isError: Boolean = false) {
        _state.value = _state.value.copy(message = message, isError = isError, busy = false)
        refresh()
    }

    fun createUser(username: String, fullName: String, password: String, role: String) {
        viewModelScope.launch {
            val error = authRepository.createUser(username, fullName, password, role)
            report(error ?: "Foydalanuvchi qo'shildi: $username", error != null)
        }
    }

    fun toggleUser(username: String) {
        viewModelScope.launch {
            val error = authRepository.toggleActive(username)
            report(error ?: "Foydalanuvchi holati o'zgartirildi.", error != null)
        }
    }

    fun resetPassword(username: String, password: String) {
        viewModelScope.launch {
            val error = authRepository.resetPassword(username, password)
            report(error ?: "Parol yangilandi: $username", error != null)
        }
    }

    fun createBackup() {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true)
            val backup = runCatching { backupRepository.create() }
            report(
                backup.getOrNull()?.let { "Zaxira yaratildi: ${it.name} (${it.sizeKb} KB)" }
                    ?: "Zaxira yaratib bo'lmadi.",
                backup.isFailure,
            )
        }
    }

    fun restoreBackup(name: String) {
        viewModelScope.launch {
            if (backupRepository.restore(name)) {
                authRepository.audit("backup_restored", details = name)
                report("Baza tiklandi. Ilova yopiladi — uni qaytadan oching.")
                kotlinx.coroutines.delay(2500)
                backupRepository.killProcess()
            } else {
                report("Tiklab bo'lmadi: $name", true)
            }
        }
    }

    fun deleteBackup(name: String) {
        viewModelScope.launch {
            backupRepository.delete(name)
            report("Zaxira o'chirildi: $name")
        }
    }

    fun loadDemoData() {
        viewModelScope.launch {
            _state.value = _state.value.copy(busy = true, seedingStep = "Boshlanmoqda")
            bootstrapRepository.loadDemoData { step, _ ->
                _state.value = _state.value.copy(seedingStep = step)
            }
            _state.value = _state.value.copy(seedingStep = null)
            report("Namuna ma'lumotlar yuklandi va ML modellari o'qitildi.")
        }
    }
}

@Composable
fun AdminScreen(
    navController: NavHostController,
    onLogout: () -> Unit,
    viewModel: AdminViewModel = hiltViewModel(),
) {
    val state by viewModel.state.collectAsState()
    val users by viewModel.users.collectAsState()
    val audit by viewModel.audit.collectAsState()
    var restoreTarget by remember { mutableStateOf<String?>(null) }
    LaunchedEffect(Unit) { viewModel.refresh() }

    AppScaffold(navController, "Administrator", onLogout) { padding ->
        ScreenColumn(padding, scrollToTopKey = state.message) {
            state.message?.let { InfoBanner(it, state.isError) }
            state.seedingStep?.let {
                LinearProgressIndicator(Modifier.fillMaxWidth())
                Text("$it…", style = MaterialTheme.typography.bodySmall)
            }

            // ---- Foydalanuvchilar ----
            ChartCard("Foydalanuvchilar (${users.size})") {
                DataTable(
                    headers = listOf("Login", "F.I.Sh.", "Rol", "Faol"),
                    rows = users.map {
                        listOf(it.username, it.fullName, Rbac.label(it.role), if (it.active) "Ha" else "Yo'q")
                    },
                    weights = listOf(1f, 1.4f, 1.1f, 0.6f),
                )
            }

            var newUsername by remember { mutableStateOf("") }
            var newFullName by remember { mutableStateOf("") }
            var newPassword by remember { mutableStateOf("") }
            var newRole by remember { mutableStateOf("viewer") }
            ChartCard("Yangi foydalanuvchi") {
                OutlinedTextField(newUsername, { newUsername = it }, label = { Text("Login") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(newFullName, { newFullName = it }, label = { Text("F.I.Sh.") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(newPassword, { newPassword = it }, label = { Text("Parol (kamida 6 belgi)") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Rbac.allRoles.forEach { role ->
                        FilterChip(
                            selected = newRole == role,
                            onClick = { newRole = role },
                            label = { Text(Rbac.label(role)) },
                        )
                    }
                }
                Button(
                    onClick = {
                        viewModel.createUser(newUsername, newFullName, newPassword, newRole)
                        newUsername = ""; newFullName = ""; newPassword = ""
                    },
                    modifier = Modifier.fillMaxWidth(),
                ) { Text("Qo'shish") }
            }

            var targetUser by remember { mutableStateOf("") }
            var targetPassword by remember { mutableStateOf("") }
            ChartCard("Faollik va parolni boshqarish") {
                OutlinedTextField(targetUser, { targetUser = it }, label = { Text("Login") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                OutlinedTextField(targetPassword, { targetPassword = it }, label = { Text("Yangi parol") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedButton(onClick = { viewModel.toggleUser(targetUser) }, modifier = Modifier.weight(1f)) {
                        Text("Faollik")
                    }
                    OutlinedButton(
                        onClick = { viewModel.resetPassword(targetUser, targetPassword); targetPassword = "" },
                        modifier = Modifier.weight(1f),
                    ) { Text("Parolni tiklash") }
                }
            }

            // ---- Zaxira ----
            ChartCard("Zaxira nusxalar", "Baza qurilma ichidagi files/backups papkasida saqlanadi") {
                Button(onClick = viewModel::createBackup, enabled = !state.busy, modifier = Modifier.fillMaxWidth()) {
                    Icon(Icons.Filled.Backup, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Zaxira yaratish")
                }
                if (state.backups.isEmpty()) {
                    EmptyState("Hali zaxira yaratilmagan.")
                } else {
                    state.backups.forEach { backup ->
                        Row(
                            Modifier.fillMaxWidth().padding(vertical = 3.dp),
                            verticalAlignment = androidx.compose.ui.Alignment.CenterVertically,
                        ) {
                            Column(Modifier.weight(1f)) {
                                Text(backup.name, style = MaterialTheme.typography.bodySmall, maxLines = 1)
                                Text(
                                    "${backup.sizeKb} KB · ${backup.createdAt}",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                )
                            }
                            TextButton(onClick = { restoreTarget = backup.name }) { Text("Tiklash") }
                            IconButton(onClick = { viewModel.deleteBackup(backup.name) }) {
                                Icon(Icons.Filled.Delete, contentDescription = "O'chirish")
                            }
                        }
                    }
                }
            }

            // ---- Namuna ma'lumotlar ----
            if (!state.hasDemoData) {
                ChartCard(
                    "Namuna ma'lumotlar",
                    "Desktop versiyasidagi to'liq test to'plamini yuklash (13 viloyat, 140 dala, 5 yillik tarix).",
                ) {
                    OutlinedButton(
                        onClick = viewModel::loadDemoData,
                        enabled = !state.busy,
                        modifier = Modifier.fillMaxWidth(),
                    ) {
                        Icon(Icons.Filled.DatasetLinked, contentDescription = null)
                        Spacer(Modifier.width(8.dp))
                        Text("Namuna ma'lumotlarni yuklash")
                    }
                }
            }

            // ---- Baza holati ----
            ChartCard("Ma'lumotlar bazasi holati") {
                DataTable(
                    headers = listOf("Jadval", "Yozuvlar"),
                    rows = state.tableCounts.map { listOf(it.table, Fmt.num(it.rows.toDouble(), 0)) },
                    maxRows = 15,
                )
            }

            // ---- Audit ----
            ChartCard("Audit jurnali (so'nggi ${audit.size})") {
                DataTable(
                    headers = listOf("Vaqt", "Foydalanuvchi", "Amal", "Tafsilot"),
                    rows = audit.map {
                        listOf(Fmt.dateTime(it.timestamp), it.username, it.action, it.details)
                    },
                    weights = listOf(1.2f, 1f, 1.1f, 1.4f),
                    maxRows = 20,
                )
            }
        }
    }

    restoreTarget?.let { name ->
        AlertDialog(
            onDismissRequest = { restoreTarget = null },
            title = { Text("Bazani tiklash") },
            text = {
                Text(
                    "\"$name\" zaxirasidan tiklansinmi? Joriy ma'lumotlar almashtiriladi va " +
                        "ilova yopiladi — keyin uni qaytadan oching.",
                )
            },
            confirmButton = {
                TextButton(onClick = { viewModel.restoreBackup(name) }) { Text("Tiklash") }
            },
            dismissButton = {
                TextButton(onClick = { restoreTarget = null }) { Text("Bekor qilish") }
            },
        )
    }
}
