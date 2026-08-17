package com.smartmoliya.app.feature.payments.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.PaymentCreateDto
import com.smartmoliya.app.core.network.dto.PaymentDto
import com.smartmoliya.app.feature.expense.domain.Transaction
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import com.smartmoliya.app.feature.wallets.domain.Wallet
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

const val TOPUP_NOTE_PREFIX = "Hamyonni to'ldirish"

data class PaymentsUiState(
    val wallets: List<Wallet> = emptyList(),
    val payments: List<PaymentDto> = emptyList(),
    /** Offline rejimda to'ldirishlar tarixi - income tranzaksiyalar. */
    val localTopUps: List<Transaction> = emptyList(),
    val isLoading: Boolean = false,
    val message: String? = null
)

@HiltViewModel
class PaymentsViewModel @Inject constructor(
    private val api: ApiService,
    private val transactionRepository: TransactionRepository,
    private val categoryRepository: com.smartmoliya.app.feature.expense.domain.CategoryRepository,
    walletRepository: WalletRepository
) : ViewModel() {

    private val _payments = MutableStateFlow<List<PaymentDto>>(emptyList())
    private val _isLoading = MutableStateFlow(false)
    private val _message = MutableStateFlow<String?>(null)

    private val localTopUpsFlow = transactionRepository.observeTransactions().map { transactions ->
        transactions.filter {
            it.type == TransactionType.INCOME && it.note?.startsWith(TOPUP_NOTE_PREFIX) == true
        }
    }

    val uiState: StateFlow<PaymentsUiState> = combine(
        walletRepository.observeWallets(), _payments, localTopUpsFlow, _isLoading, _message
    ) { wallets, payments, topUps, loading, message ->
        PaymentsUiState(wallets, payments, topUps, loading, message)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), PaymentsUiState())

    init {
        if (BuildConfig.OFFLINE_MODE) {
            // To'ldirish tranzaksiyasi seed kategoriyaga bog'lanadi - mavjudligini kafolatlaymiz
            viewModelScope.launch { categoryRepository.ensureSeedData() }
        }
        refresh()
    }

    fun refresh() {
        if (BuildConfig.OFFLINE_MODE) return
        viewModelScope.launch {
            _isLoading.value = true
            runCatching { api.listPayments() }
                .onSuccess { _payments.value = it }
                .onFailure { _message.value = "To'lovlar tarixini yuklab bo'lmadi" }
            _isLoading.value = false
        }
    }

    /** Online: mock provayder orqali; Offline: to'g'ridan-to'g'ri income tranzaksiya. */
    fun topUp(walletId: String, provider: String, amount: Double) {
        viewModelScope.launch {
            if (BuildConfig.OFFLINE_MODE) {
                transactionRepository.addTransaction(
                    walletId = walletId,
                    categoryId = "seed-inc-other",
                    type = TransactionType.INCOME,
                    amount = amount,
                    note = "$TOPUP_NOTE_PREFIX (naqd)"
                )
                _message.value = "Hamyon to'ldirildi ✅"
                return@launch
            }

            _isLoading.value = true
            runCatching {
                val payment = api.createPayment(
                    PaymentCreateDto(wallet_id = walletId, provider = provider, amount = amount)
                )
                // Mock muhitda haqiqiy checkout yo'q - to'lovni darhol simulyatsiya qilamiz
                api.simulatePayment(payment.id)
            }.onSuccess {
                _message.value = "To'lov muvaffaqiyatli (mock): hamyon balansi yangilandi"
                refresh()
            }.onFailure {
                _message.value = "To'lov amalga oshmadi"
            }
            _isLoading.value = false
        }
    }

    fun clearMessage() {
        _message.value = null
    }
}
