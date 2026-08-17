package com.uzerp.mobile.ui.purchases

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.dao.PurchaseWithSupplier
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.local.entity.SupplierEntity
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.InventoryRepository
import com.uzerp.mobile.data.repository.PaymentRepository
import com.uzerp.mobile.data.repository.ProductRepository
import com.uzerp.mobile.data.repository.PurchaseDetail
import com.uzerp.mobile.data.repository.PurchaseItemInput
import com.uzerp.mobile.data.repository.PurchaseRepository
import com.uzerp.mobile.data.repository.SupplierRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class PurchasesListUiState(val items: List<PurchaseWithSupplier> = emptyList(), val isLoading: Boolean = true, val error: String? = null)

@HiltViewModel
class PurchasesListViewModel @Inject constructor(private val repository: PurchaseRepository) : ViewModel() {
    private val _state = MutableStateFlow(PurchasesListUiState())
    val state: StateFlow<PurchasesListUiState> = _state.asStateFlow()

    init { reload() }

    fun reload() {
        viewModelScope.launch {
            try {
                _state.value = PurchasesListUiState(items = repository.list().items, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}

data class PurchaseDetailUiState(
    val detail: PurchaseDetail? = null,
    val supplierName: String? = null,
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class PurchaseDetailViewModel @Inject constructor(
    private val repository: PurchaseRepository,
    private val supplierRepository: SupplierRepository,
    private val paymentRepository: PaymentRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(PurchaseDetailUiState())
    val state: StateFlow<PurchaseDetailUiState> = _state.asStateFlow()
    private var purchaseId: Long = 0

    fun load(id: Long) {
        purchaseId = id
        viewModelScope.launch {
            try {
                val detail = repository.get(id)
                val supplierName = detail.purchase.supplierId?.let { sid -> runCatching { supplierRepository.get(sid).name }.getOrNull() }
                _state.value = PurchaseDetailUiState(detail = detail, supplierName = supplierName, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    private fun userId() = authRepository.currentUser.value?.id

    fun receive() = act { repository.receive(purchaseId, userId()) }
    fun cancel() = act { repository.cancel(purchaseId, userId()) }
    fun pay(amount: BigDecimal, method: String = "bank") =
        act { paymentRepository.payForPurchase(purchaseId, amount, method, userId()) }

    private fun act(block: suspend () -> Unit) {
        viewModelScope.launch {
            try {
                block()
                load(purchaseId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}

data class PurchaseFormLine(val product: ProductEntity, val quantity: BigDecimal, val price: BigDecimal)

data class PurchaseFormUiState(
    val suppliers: List<SupplierEntity> = emptyList(),
    val products: List<ProductEntity> = emptyList(),
    val supplierId: Long? = null,
    val lines: List<PurchaseFormLine> = emptyList(),
    val isSaving: Boolean = false,
    val error: String? = null,
    val savedId: Long? = null,
)

@HiltViewModel
class PurchaseFormViewModel @Inject constructor(
    private val purchaseRepository: PurchaseRepository,
    private val supplierRepository: SupplierRepository,
    private val productRepository: ProductRepository,
    private val inventoryRepository: InventoryRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(PurchaseFormUiState())
    val state: StateFlow<PurchaseFormUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            _state.value = _state.value.copy(
                suppliers = supplierRepository.list(search = null).items,
                products = productRepository.list(search = null).items,
            )
        }
    }

    fun setSupplier(id: Long?) {
        _state.value = _state.value.copy(supplierId = id)
    }

    fun addLine(product: ProductEntity) {
        val lines = _state.value.lines.toMutableList()
        val idx = lines.indexOfFirst { it.product.id == product.id }
        if (idx >= 0) {
            lines[idx] = lines[idx].copy(quantity = lines[idx].quantity.add(BigDecimal.ONE))
        } else {
            lines.add(PurchaseFormLine(product, BigDecimal.ONE, product.costPrice))
        }
        _state.value = _state.value.copy(lines = lines)
    }

    fun updateLine(productId: Long, quantity: BigDecimal? = null, price: BigDecimal? = null) {
        _state.value = _state.value.copy(
            lines = _state.value.lines.map {
                if (it.product.id == productId) it.copy(quantity = quantity ?: it.quantity, price = price ?: it.price) else it
            },
        )
    }

    fun removeLine(productId: Long) {
        _state.value = _state.value.copy(lines = _state.value.lines.filterNot { it.product.id == productId })
    }

    fun save(receiveImmediately: Boolean) {
        val s = _state.value
        if (s.lines.isEmpty()) {
            _state.value = s.copy(error = "Kamida bitta pozitsiya qo'shing.")
            return
        }
        _state.value = s.copy(isSaving = true, error = null)
        viewModelScope.launch {
            try {
                val userId = authRepository.currentUser.value?.id
                val warehouseId = inventoryRepository.defaultWarehouseId()
                val items = s.lines.map { PurchaseItemInput(it.product.id, it.quantity, it.price) }
                val purchaseId = purchaseRepository.create(s.supplierId, warehouseId, items, userId)
                if (receiveImmediately) purchaseRepository.receive(purchaseId, userId)
                _state.value = _state.value.copy(isSaving = false, savedId = purchaseId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(isSaving = false, error = e.message)
            }
        }
    }
}
