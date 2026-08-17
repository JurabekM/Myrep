package com.uzerp.mobile.ui.cash

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.uzerp.mobile.core.UzErpException
import com.uzerp.mobile.data.local.entity.PaymentEntity
import com.uzerp.mobile.data.repository.AuthRepository
import com.uzerp.mobile.data.repository.PaymentRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import java.math.BigDecimal
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class CashUiState(
    val items: List<PaymentEntity> = emptyList(),
    val cashBalance: BigDecimal = BigDecimal.ZERO,
    val bankBalance: BigDecimal = BigDecimal.ZERO,
    val isLoading: Boolean = true,
    val error: String? = null,
    val message: String? = null,
)

@HiltViewModel
class CashViewModel @Inject constructor(
    private val paymentRepository: PaymentRepository,
    private val authRepository: AuthRepository,
) : ViewModel() {
    private val _state = MutableStateFlow(CashUiState())
    val state: StateFlow<CashUiState> = _state.asStateFlow()

    fun reload() {
        viewModelScope.launch {
            _state.value = _state.value.copy(isLoading = true)
            try {
                _state.value = _state.value.copy(
                    items = paymentRepository.cashbook().items,
                    cashBalance = paymentRepository.cashBalance(),
                    bankBalance = paymentRepository.bankBalance(),
                    isLoading = false, error = null,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(isLoading = false, error = e.message)
            }
        }
    }

    fun expense(amount: BigDecimal, note: String, method: String) {
        viewModelScope.launch {
            try {
                paymentRepository.expense(amount, note, method, userId = authRepository.currentUser.value?.id)
                _state.value = _state.value.copy(message = "Xarajat qayd etildi.")
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }

    fun income(amount: BigDecimal, note: String, method: String) {
        viewModelScope.launch {
            try {
                paymentRepository.otherIncome(amount, note, method, userId = authRepository.currentUser.value?.id)
                _state.value = _state.value.copy(message = "Kirim qayd etildi.")
                reload()
            } catch (e: UzErpException) {
                _state.value = _state.value.copy(error = e.message)
            }
        }
    }
}
