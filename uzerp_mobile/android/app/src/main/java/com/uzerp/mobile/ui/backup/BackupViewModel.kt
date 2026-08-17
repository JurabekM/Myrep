package com.uzerp.mobile.ui.backup

import android.net.Uri
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.data.repository.BackupRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class BackupUiState(
    val isLoading: Boolean = false,
    val message: String? = null,
    val error: String? = null,
    val restoring: Boolean = false,
)

@HiltViewModel
class BackupViewModel @Inject constructor(
    private val backupRepository: BackupRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(BackupUiState())
    val state: StateFlow<BackupUiState> = _state.asStateFlow()

    fun clearMessages() {
        _state.value = _state.value.copy(message = null, error = null)
    }

    fun backup() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, message = null)
            try {
                val result = backupRepository.backup()
                _state.value = _state.value.copy(isLoading = false, message = "Zaxira nusxa saqlandi: Yuklab olinganlar/UzERP/${result.fileName}")
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Zaxiralashda xato yuz berdi.")
            }
        }
    }

    /** Faylni bazaga tiklaydi va — Room yopilgan bazani qayta ochmagani uchun — jarayonni to'xtatadi. */
    fun restore(uri: Uri, onExit: () -> Unit) {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true, error = null, message = null)
            try {
                backupRepository.restore(uri)
                _state.value = _state.value.copy(isLoading = false, restoring = true, message = "Tiklandi. Ilova hozir yopiladi — uni qayta oching.")
                delay(1500)
                onExit()
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message ?: "Tiklashda xato yuz berdi.")
            }
        }
    }
}
