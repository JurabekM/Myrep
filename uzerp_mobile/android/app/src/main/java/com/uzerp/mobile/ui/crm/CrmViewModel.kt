package com.uzerp.mobile.ui.crm

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.LeadEntity
import com.uzerp.mobile.data.repository.CrmRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class LeadsUiState(
    val items: List<LeadEntity> = emptyList(),
    val isLoading: Boolean = true,
    val message: String? = null,
    val error: String? = null,
)

@HiltViewModel
class CrmViewModel @Inject constructor(private val repository: CrmRepository) : ViewModel() {
    private val _state = MutableStateFlow(LeadsUiState())
    val state: StateFlow<LeadsUiState> = _state.asStateFlow()

    init { reload() }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                _state.value = LeadsUiState(items = repository.listLeads().items, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun createLead(name: String, phone: String, source: String) {
        viewModelScope.launch {
            try {
                repository.createLead(name, phone, source = source)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun changeStatus(leadId: Long, status: String) {
        viewModelScope.launch {
            try {
                val customerId = repository.changeLeadStatus(leadId, status)
                _state.value = _state.value.copy(
                    message = if (status == "won" && customerId != null) "Lead yutildi — mijoz yaratildi!" else "Holat yangilandi.",
                )
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
