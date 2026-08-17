package com.uzerp.mobile.ui.products

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.repository.ProductRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ProductsUiState(
    val items: List<ProductEntity> = emptyList(),
    val search: String = "",
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class ProductsViewModel @Inject constructor(
    private val repository: ProductRepository,
) : ViewModel() {
    private val _uiState = MutableStateFlow(ProductsUiState())
    val uiState: StateFlow<ProductsUiState> = _uiState.asStateFlow()

    init { reload() }

    fun onSearchChange(value: String) {
        _uiState.value = _uiState.value.copy(search = value)
        reload()
    }

    fun reload() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(isLoading = true)
            try {
                val page = repository.list(search = _uiState.value.search.ifBlank { null })
                _uiState.value = _uiState.value.copy(items = page.items, isLoading = false, error = null)
            } catch (e: Exception) {
                _uiState.value = _uiState.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}

data class ProductFormUiState(
    val id: Long? = null,
    val name: String = "",
    val barcode: String = "",
    val unit: String = "dona",
    val salePrice: String = "",
    val costPrice: String = "",
    val vatRate: String = "12",
    val minStock: String = "0",
    val isSaving: Boolean = false,
    val error: String? = null,
    val saved: Boolean = false,
)

@HiltViewModel
class ProductFormViewModel @Inject constructor(
    private val repository: ProductRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(ProductFormUiState())
    val state: StateFlow<ProductFormUiState> = _state.asStateFlow()

    fun load(id: Long) {
        viewModelScope.launch {
            try {
                val p = repository.get(id)
                _state.value = ProductFormUiState(
                    id = p.id, name = p.name, barcode = p.barcode, unit = p.unit,
                    salePrice = p.salePrice.toPlainString(), costPrice = p.costPrice.toPlainString(),
                    vatRate = p.vatRate.toPlainString(), minStock = p.minStock.toPlainString(),
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun update(transform: (ProductFormUiState) -> ProductFormUiState) {
        _state.value = transform(_state.value)
    }

    fun save() {
        val s = _state.value
        _state.value = s.copy(isSaving = true, error = null)
        viewModelScope.launch {
            try {
                val salePrice = s.salePrice.toBigDecimalOrNull() ?: BigDecimal.ZERO
                val costPrice = s.costPrice.toBigDecimalOrNull() ?: BigDecimal.ZERO
                val vatRate = s.vatRate.toBigDecimalOrNull() ?: BigDecimal("12")
                val minStock = s.minStock.toBigDecimalOrNull() ?: BigDecimal.ZERO
                if (s.id == null) {
                    repository.create(s.name, salePrice, costPrice, s.barcode, s.unit, vatRate, minStock)
                } else {
                    val existing = repository.get(s.id)
                    repository.update(
                        existing.copy(
                            name = s.name, barcode = s.barcode, unit = s.unit, salePrice = salePrice,
                            costPrice = costPrice, vatRate = vatRate, minStock = minStock,
                        ),
                    )
                }
                _state.value = _state.value.copy(isSaving = false, saved = true)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(isSaving = false, error = e.message)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isSaving = false, error = "Xato: ${e.message}")
            }
        }
    }
}
