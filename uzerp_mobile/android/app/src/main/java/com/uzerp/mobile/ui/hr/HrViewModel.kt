package com.uzerp.mobile.ui.hr

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.dao.DepartmentWithCount
import com.uzerp.mobile.data.local.entity.EmployeeEntity
import com.uzerp.mobile.data.repository.HrRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch

data class HrUiState(
    val employees: List<EmployeeEntity> = emptyList(),
    val departments: List<DepartmentWithCount> = emptyList(),
    val search: String = "",
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class HrViewModel @Inject constructor(
    private val repository: HrRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(HrUiState())
    val state: StateFlow<HrUiState> = _state.asStateFlow()

    fun onSearchChange(value: String) {
        _state.value = _state.value.copy(search = value)
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                _state.value = _state.value.copy(
                    employees = repository.listEmployees(search = _state.value.search.ifBlank { null }).items,
                    departments = repository.departments().first(),
                    isLoading = false, error = null,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun createEmployee(fullName: String, departmentId: Long?, position: String, salary: BigDecimal, phone: String) {
        viewModelScope.launch {
            try {
                repository.createEmployee(fullName, departmentId, position, salary, phone)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun createDepartment(name: String) {
        viewModelScope.launch {
            try {
                repository.createDepartment(name)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
