package uz.dehqonkomakchi.app.ui.diagnose

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.dehqonkomakchi.app.data.remote.diagnosis.PhotoQualityIssue
import uz.dehqonkomakchi.app.data.repo.DiagnosisRecord
import uz.dehqonkomakchi.app.data.repo.DiagnosisRepository
import javax.inject.Inject

sealed interface DiagnoseUiState {
    data object Idle : DiagnoseUiState
    data object Analyzing : DiagnoseUiState
    data class RetakeNeeded(val issue: PhotoQualityIssue) : DiagnoseUiState
    data class Done(val record: DiagnosisRecord) : DiagnoseUiState
    data class Failed(val message: String) : DiagnoseUiState
}

@HiltViewModel
class DiagnoseViewModel @Inject constructor(
    private val repository: DiagnosisRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow<DiagnoseUiState>(DiagnoseUiState.Idle)
    val uiState: StateFlow<DiagnoseUiState> = _uiState.asStateFlow()

    private val _history = MutableStateFlow<List<DiagnosisRecord>>(emptyList())
    val history: StateFlow<List<DiagnosisRecord>> = _history.asStateFlow()

    init {
        viewModelScope.launch {
            repository.observeHistory().collect { list -> _history.value = list }
        }
    }

    fun analyze(imageBytes: ByteArray, photoPath: String) {
        viewModelScope.launch {
            _uiState.value = DiagnoseUiState.Analyzing
            try {
                val issue = repository.checkPhotoQuality(imageBytes)
                if (issue != null) {
                    _uiState.value = DiagnoseUiState.RetakeNeeded(issue)
                    return@launch
                }
                val record = repository.diagnoseAndSave(imageBytes, photoPath)
                _uiState.value = DiagnoseUiState.Done(record)
            } catch (e: Exception) {
                _uiState.value = DiagnoseUiState.Failed(e.message ?: "unknown_error")
            }
        }
    }

    fun rate(id: String, useful: Boolean) {
        viewModelScope.launch { repository.rate(id, useful) }
    }

    fun reset() {
        _uiState.value = DiagnoseUiState.Idle
    }
}
