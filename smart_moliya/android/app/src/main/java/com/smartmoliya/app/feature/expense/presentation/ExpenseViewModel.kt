package com.smartmoliya.app.feature.expense.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.feature.expense.domain.Category
import com.smartmoliya.app.feature.expense.domain.CategoryRepository
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
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class ExpenseUiState(
    val transactions: List<Transaction> = emptyList(),
    val wallets: List<Wallet> = emptyList(),
    val categories: List<Category> = emptyList(),
    val isLoading: Boolean = false
)

@HiltViewModel
class ExpenseViewModel @Inject constructor(
    private val transactionRepository: TransactionRepository,
    private val walletRepository: WalletRepository,
    private val categoryRepository: CategoryRepository
) : ViewModel() {

    private val _isLoading = MutableStateFlow(false)

    val uiState: StateFlow<ExpenseUiState> = combine(
        transactionRepository.observeTransactions(),
        walletRepository.observeWallets(),
        categoryRepository.observeCategories(),
        _isLoading
    ) { transactions, wallets, categories, loading ->
        ExpenseUiState(transactions, wallets, categories, loading)
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), ExpenseUiState())

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            _isLoading.value = true
            categoryRepository.ensureSeedData()
            runCatching {
                transactionRepository.refresh()
                categoryRepository.refresh()
            }
            _isLoading.value = false
        }
    }

    fun addTransaction(walletId: String, categoryId: String?, type: TransactionType, amount: Double, note: String?) {
        viewModelScope.launch {
            transactionRepository.addTransaction(walletId, categoryId, type, amount, note)
        }
    }

    fun deleteTransaction(transactionId: String) {
        viewModelScope.launch {
            transactionRepository.deleteTransaction(transactionId)
        }
    }
}
