package com.uzerp.mobile.ui.sales

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.dao.SalesDocWithCustomer
import com.uzerp.mobile.data.local.entity.CustomerEntity
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.CustomerRepository
import com.uzerp.mobile.data.repository.PaymentRepository
import com.uzerp.mobile.data.repository.ProductRepository
import com.uzerp.mobile.data.repository.SaleItemInput
import com.uzerp.mobile.data.repository.SalesDocDetail
import com.uzerp.mobile.data.repository.SalesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

// -------------------------------------------------------------------- //
//  Ro'yxat
// -------------------------------------------------------------------- //

data class SalesListUiState(
    val items: List<SalesDocWithCustomer> = emptyList(),
    val isLoading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class SalesListViewModel @Inject constructor(
    private val repository: SalesRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SalesListUiState())
    val state: StateFlow<SalesListUiState> = _state.asStateFlow()

    init { reload() }

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val page = repository.list()
                _state.value = SalesListUiState(items = page.items, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }
}

// -------------------------------------------------------------------- //
//  Tafsilot
// -------------------------------------------------------------------- //

data class SalesDetailUiState(
    val detail: SalesDocDetail? = null,
    val customerName: String? = null,
    val isLoading: Boolean = true,
    val message: String? = null,
    val error: String? = null,
)

@HiltViewModel
class SalesDetailViewModel @Inject constructor(
    private val repository: SalesRepository,
    private val customerRepository: CustomerRepository,
    private val paymentRepository: PaymentRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SalesDetailUiState())
    val state: StateFlow<SalesDetailUiState> = _state.asStateFlow()
    private var docId: Long = 0

    fun load(id: Long) {
        docId = id
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                val detail = repository.getDoc(id)
                val customerName = detail.doc.customerId?.let { cid ->
                    runCatching { customerRepository.get(cid).name }.getOrNull()
                }
                _state.value = SalesDetailUiState(detail = detail, customerName = customerName, isLoading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    private fun userId() = authRepository.currentUser.value?.id

    fun confirm() = act { repository.confirm(docId, userId()) }
    fun cancel() = act { repository.cancel(docId, userId()) }
    fun registerPayment(amount: BigDecimal, method: String = "cash") =
        act { paymentRepository.receiveForSale(docId, amount, method, userId()) }

    fun convert(onNewDoc: (Long) -> Unit) {
        viewModelScope.launch {
            try {
                val newId = repository.convert(docId, userId())
                onNewDoc(newId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    private fun act(block: suspend () -> Unit) {
        viewModelScope.launch {
            try {
                block()
                load(docId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}

// -------------------------------------------------------------------- //
//  Yangi hujjat
// -------------------------------------------------------------------- //

data class SalesFormLine(val product: ProductEntity, val quantity: BigDecimal, val price: BigDecimal)

data class SalesFormUiState(
    val docType: String = "invoice",
    val customers: List<CustomerEntity> = emptyList(),
    val products: List<ProductEntity> = emptyList(),
    val customerId: Long? = null,
    val lines: List<SalesFormLine> = emptyList(),
    val note: String = "",
    val isSaving: Boolean = false,
    val error: String? = null,
    val savedDocId: Long? = null,
) {
    val total: BigDecimal get() = d(lines.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.quantity.multiply(l.price)) })
}

@HiltViewModel
class SalesFormViewModel @Inject constructor(
    private val salesRepository: SalesRepository,
    private val customerRepository: CustomerRepository,
    private val productRepository: ProductRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(SalesFormUiState())
    val state: StateFlow<SalesFormUiState> = _state.asStateFlow()

    fun init(docType: String) {
        _state.value = _state.value.copy(docType = docType)
        viewModelScope.launch {
            val customers = customerRepository.list(search = null).items
            val products = productRepository.list(search = null).items
            _state.value = _state.value.copy(customers = customers, products = products)
        }
    }

    fun setCustomer(id: Long?) {
        _state.value = _state.value.copy(customerId = id)
    }

    fun addLine(product: ProductEntity) {
        val lines = _state.value.lines.toMutableList()
        val idx = lines.indexOfFirst { it.product.id == product.id }
        if (idx >= 0) {
            lines[idx] = lines[idx].copy(quantity = d(lines[idx].quantity.add(BigDecimal.ONE)))
        } else {
            lines.add(SalesFormLine(product, BigDecimal.ONE, product.salePrice))
        }
        _state.value = _state.value.copy(lines = lines)
    }

    fun updateQuantity(productId: Long, quantity: BigDecimal) {
        _state.value = _state.value.copy(
            lines = _state.value.lines.map { if (it.product.id == productId) it.copy(quantity = quantity) else it },
        )
    }

    fun removeLine(productId: Long) {
        _state.value = _state.value.copy(lines = _state.value.lines.filterNot { it.product.id == productId })
    }

    fun setNote(value: String) {
        _state.value = _state.value.copy(note = value)
    }

    fun save(confirmImmediately: Boolean) {
        val s = _state.value
        if (s.lines.isEmpty()) {
            _state.value = s.copy(error = "Kamida bitta pozitsiya qo'shing.")
            return
        }
        _state.value = s.copy(isSaving = true, error = null)
        viewModelScope.launch {
            try {
                val userId = authRepository.currentUser.value?.id
                val items = s.lines.map { SaleItemInput(it.product.id, it.quantity, it.price) }
                val docId = salesRepository.createDoc(s.docType, s.customerId, null, items, userId, note = s.note)
                if (confirmImmediately) salesRepository.confirm(docId, userId)
                _state.value = _state.value.copy(isSaving = false, savedDocId = docId)
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(isSaving = false, error = e.message)
            }
        }
    }
}
