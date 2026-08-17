package com.uzerp.mobile.ui.stock

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.local.entity.WarehouseEntity
import com.uzerp.mobile.data.repository.InventoryRepository
import com.uzerp.mobile.data.repository.ProductRepository
import com.uzerp.mobile.data.repository.StockOverviewRow
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StockUiState(
    val rows: List<StockOverviewRow> = emptyList(),
    val warehouses: List<WarehouseEntity> = emptyList(),
    val products: List<ProductEntity> = emptyList(),
    val search: String = "",
    val totalValue: BigDecimal = BigDecimal.ZERO,
    val isLoading: Boolean = true,
    val message: String? = null,
    val error: String? = null,
)

@HiltViewModel
class StockViewModel @Inject constructor(
    private val inventoryRepository: InventoryRepository,
    private val productRepository: ProductRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(StockUiState())
    val state: StateFlow<StockUiState> = _state.asStateFlow()

    init { reload() }

    fun onSearchChange(value: String) {
        _state.value = _state.value.copy(search = value)
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val rows = inventoryRepository.stockOverview(search = _state.value.search.ifBlank { null }).items
                val warehouses = inventoryRepository.warehouses()
                val products = productRepository.list(search = null).items
                val value = inventoryRepository.stockValue()
                _state.value = _state.value.copy(
                    rows = rows, warehouses = warehouses, products = products,
                    totalValue = value, isLoading = false, error = null,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun transfer(productId: Long, fromWarehouse: Long, toWarehouse: Long, qty: BigDecimal) {
        viewModelScope.launch {
            try {
                inventoryRepository.transfer(productId, fromWarehouse, toWarehouse, qty)
                _state.value = _state.value.copy(message = "Ko'chirildi.")
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun clearMessages() {
        _state.value = _state.value.copy(message = null, error = null)
    }
}
