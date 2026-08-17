package com.uzerp.mobile.ui.pos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.PaymentRepository
import com.uzerp.mobile.data.repository.ProductRepository
import com.uzerp.mobile.data.repository.SaleItemInput
import com.uzerp.mobile.data.repository.SalesRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CartLine(val product: ProductEntity, val quantity: BigDecimal) {
    val lineTotal: BigDecimal get() = d(quantity.multiply(product.salePrice))
}

data class PosUiState(
    val cart: List<CartLine> = emptyList(),
    val allProducts: List<ProductEntity> = emptyList(),
    val barcodeInput: String = "",
    val isCheckingOut: Boolean = false,
    val message: String? = null,
    val error: String? = null,
) {
    val total: BigDecimal get() = d(cart.fold(BigDecimal.ZERO) { acc, l -> acc.add(l.lineTotal) })
}

@HiltViewModel
class PosViewModel @Inject constructor(
    private val productRepository: ProductRepository,
    private val salesRepository: SalesRepository,
    private val paymentRepository: PaymentRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(PosUiState())
    val state: StateFlow<PosUiState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val products = productRepository.list(search = null).items
            _state.value = _state.value.copy(allProducts = products)
        }
    }

    fun onBarcodeChange(value: String) {
        _state.value = _state.value.copy(barcodeInput = value)
    }

    fun addByBarcode() {
        val code = _state.value.barcodeInput.trim()
        if (code.isBlank()) return
        viewModelScope.launch {
            val product = productRepository.findByBarcode(code)
            if (product == null) {
                _state.value = _state.value.copy(error = "Shtrix-kod topilmadi: $code", barcodeInput = "")
                return@launch
            }
            addProduct(product)
            _state.value = _state.value.copy(barcodeInput = "")
        }
    }

    fun addProduct(product: ProductEntity, qty: BigDecimal = BigDecimal.ONE) {
        val cart = _state.value.cart.toMutableList()
        val idx = cart.indexOfFirst { it.product.id == product.id }
        if (idx >= 0) {
            cart[idx] = cart[idx].copy(quantity = d(cart[idx].quantity.add(qty)))
        } else {
            cart.add(CartLine(product, qty))
        }
        _state.value = _state.value.copy(cart = cart)
    }

    fun removeLine(productId: Long) {
        _state.value = _state.value.copy(cart = _state.value.cart.filterNot { it.product.id == productId })
    }

    fun clearCart() {
        _state.value = _state.value.copy(cart = emptyList())
    }

    fun checkout(method: String) {
        val cart = _state.value.cart
        if (cart.isEmpty()) return
        _state.value = _state.value.copy(isCheckingOut = true, error = null)
        viewModelScope.launch {
            try {
                val userId = authRepository.currentUser.value?.id
                val items = cart.map { SaleItemInput(it.product.id, it.quantity) }
                val docId = salesRepository.posSale(items, userId)
                paymentRepository.receiveForSale(docId, _state.value.total, method, userId)
                _state.value = PosUiState(
                    allProducts = _state.value.allProducts,
                    message = "Savdo yakunlandi (#$docId).",
                )
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(isCheckingOut = false, error = e.message)
            }
        }
    }

    fun clearMessages() {
        _state.value = _state.value.copy(message = null, error = null)
    }
}
