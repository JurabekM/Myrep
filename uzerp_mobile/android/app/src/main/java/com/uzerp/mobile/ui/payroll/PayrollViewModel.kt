package com.uzerp.mobile.ui.payroll

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.PayrollRunEntity
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.PayrollRepository
import com.uzerp.mobile.data.repository.PayrollRunDetail
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PayrollListUiState(val runs: List<PayrollRunEntity> = emptyList(), val isLoading: Boolean = true, val error: String? = null)

@HiltViewModel
class PayrollListViewModel @Inject constructor(private val repository: PayrollRepository) : ViewModel() {
    private val _state = MutableStateFlow(PayrollListUiState())
    val state: StateFlow<PayrollListUiState> = _state.asStateFlow()

    fun reload() {
        viewModelScope.launch {
            try {
                _state.value = PayrollListUiState(runs = repository.listRuns().items, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}

data class PayrollDetailUiState(val detail: PayrollRunDetail? = null, val isLoading: Boolean = true, val error: String? = null)

@HiltViewModel
class PayrollDetailViewModel @Inject constructor(
    private val repository: PayrollRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(PayrollDetailUiState())
    val state: StateFlow<PayrollDetailUiState> = _state.asStateFlow()
    private var runId: Long = 0

    fun load(id: Long) {
        runId = id
        viewModelScope.launch {
            try {
                _state.value = PayrollDetailUiState(detail = repository.getRun(id), isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun approve() {
        viewModelScope.launch {
            try {
                repository.approve(runId, authRepository.currentUser.value?.id)
                load(runId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun pay(method: String) {
        viewModelScope.launch {
            try {
                repository.pay(runId, method, authRepository.currentUser.value?.id)
                load(runId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}

@HiltViewModel
class PayrollCreateViewModel @Inject constructor(
    private val repository: PayrollRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _period = MutableStateFlow(DateUtils.todayStr().substring(0, 7))
    val period: StateFlow<String> = _period.asStateFlow()
    private val _error = MutableStateFlow<String?>(null)
    val error: StateFlow<String?> = _error.asStateFlow()
    private val _createdRunId = MutableStateFlow<Long?>(null)
    val createdRunId: StateFlow<Long?> = _createdRunId.asStateFlow()

    fun setPeriod(value: String) {
        _period.value = value
    }

    fun create() {
        viewModelScope.launch {
            try {
                _createdRunId.value = repository.createRun(_period.value, authRepository.currentUser.value?.id)
            } catch (e: UzErpException) {
                _error.value = e.message
            }
        }
    }
}
