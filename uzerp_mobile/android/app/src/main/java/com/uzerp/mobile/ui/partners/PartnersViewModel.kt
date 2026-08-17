package com.uzerp.mobile.ui.partners

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.CustomerEntity
import com.uzerp.mobile.data.local.entity.SupplierEntity
import com.uzerp.mobile.data.repository.CustomerRepository
import com.uzerp.mobile.data.repository.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CustomersUiState(
    val items: List<CustomerEntity> = emptyList(),
    val search: String = "",
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class CustomersViewModel @Inject constructor(private val repository: CustomerRepository) : ViewModel() {
    private val _state = MutableStateFlow(CustomersUiState())
    val state: StateFlow<CustomersUiState> = _state.asStateFlow()

    init { reload() }

    fun onSearchChange(value: String) {
        _state.value = _state.value.copy(search = value)
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val page = repository.list(search = _state.value.search.ifBlank { null })
                _state.value = _state.value.copy(items = page.items, isLoading = false, error = null)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun create(name: String, phone: String) {
        viewModelScope.launch {
            try {
                repository.create(name, phone)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}

data class SuppliersUiState(
    val items: List<SupplierEntity> = emptyList(),
    val search: String = "",
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class SuppliersViewModel @Inject constructor(private val repository: SupplierRepository) : ViewModel() {
    private val _state = MutableStateFlow(SuppliersUiState())
    val state: StateFlow<SuppliersUiState> = _state.asStateFlow()

    init { reload() }

    fun onSearchChange(value: String) {
        _state.value = _state.value.copy(search = value)
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val page = repository.list(search = _state.value.search.ifBlank { null })
                _state.value = _state.value.copy(items = page.items, isLoading = false, error = null)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun create(name: String, phone: String) {
        viewModelScope.launch {
            try {
                repository.create(name, phone)
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
