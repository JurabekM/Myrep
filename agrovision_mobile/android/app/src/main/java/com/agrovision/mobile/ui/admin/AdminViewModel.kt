package com.agrovision.mobile.ui.admin

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.agrovision.mobile.data.local.AuditLogEntity
import com.agrovision.mobile.data.local.UserEntity
import com.agrovision.mobile.data.repository.AuthRepository
import com.agrovision.mobile.data.repository.BackupFile
import com.agrovision.mobile.data.repository.BackupRepository
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
    val message: String? = null,
)

@HiltViewModel
class AdminViewModel @Inject constructor(
    private val authRepository: AuthRepository,
    private val backupRepository: BackupRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(AdminUiState(backups = backupRepository.listBackups()))
    val state: StateFlow<AdminUiState> = _state.asStateFlow()

    val users: StateFlow<List<UserEntity>> = authRepository.observeUsers()
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())
    val audit: StateFlow<List<AuditLogEntity>> = authRepository.observeAudit(100)
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createUser(username: String, fullName: String, password: String, role: String) {
        viewModelScope.launch {
            val ok = authRepository.createUser(username, fullName, password, role)
            _state.value = _state.value.copy(message = if (ok) "Foydalanuvchi qo'shildi." else "Bunday login mavjud.")
        }
    }

    fun toggleActive(username: String) {
        viewModelScope.launch {
            val ok = authRepository.toggleActive(username)
            _state.value = _state.value.copy(message = if (ok) "Holat o'zgartirildi." else "Bajarilmadi.")
        }
    }

    fun resetPassword(username: String, newPassword: String) {
        viewModelScope.launch {
            val ok = authRepository.resetPassword(username, newPassword)
            _state.value = _state.value.copy(message = if (ok) "Parol yangilandi." else "Bajarilmadi.")
        }
    }

    fun createBackup() {
        val backup = backupRepository.createBackup("manual")
        _state.value = _state.value.copy(backups = backupRepository.listBackups(), message = "Zaxira yaratildi: ${backup.name}")
    }

    /** Diqqat: bu funksiya jarayonni majburan tugatadi (baza qayta ochilishi uchun). */
    fun restoreBackup(name: String) {
        backupRepository.restoreBackup(name)
    }
}
