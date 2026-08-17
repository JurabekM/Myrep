package com.smartmoliya.app.feature.dashboard.presentation

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.smartmoliya.app.feature.expense.domain.Category
import com.smartmoliya.app.feature.expense.domain.CategoryRepository
import com.smartmoliya.app.feature.expense.domain.Transaction
import com.smartmoliya.app.feature.expense.domain.TransactionRepository
import com.smartmoliya.app.feature.expense.domain.TransactionType
import com.smartmoliya.app.feature.wallets.domain.WalletRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import javax.inject.Inject

data class DashboardUiState(
    val totalBalance: Double = 0.0,
    val currency: String = "UZS",
    val monthIncome: Double = 0.0,
    val monthExpense: Double = 0.0,
    val recentTransactions: List<Transaction> = emptyList(),
    val categories: Map<String, Category> = emptyMap()
)

@HiltViewModel
class DashboardViewModel @Inject constructor(
    private val walletRepository: WalletRepository,
    private val transactionRepository: TransactionRepository,
    private val categoryRepository: CategoryRepository
) : ViewModel() {

    val uiState: StateFlow<DashboardUiState> = combine(
        walletRepository.observeWallets(),
        transactionRepository.observeTransactions(),
        categoryRepository.observeCategories()
    ) { wallets, transactions, categories ->
        val monthStart = currentMonthStartMillis()
        val monthTransactions = transactions.filter { it.occurredAt >= monthStart }

        DashboardUiState(
            totalBalance = wallets.sumOf { it.balance },
            currency = wallets.firstOrNull()?.currency ?: "UZS",
            monthIncome = monthTransactions.filter { it.type == TransactionType.INCOME }.sumOf { it.amount },
            monthExpense = monthTransactions.filter { it.type == TransactionType.EXPENSE }.sumOf { it.amount },
            recentTransactions = transactions.sortedByDescending { it.occurredAt }.take(6),
            categories = categories.associateBy { it.id }
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), DashboardUiState())

    init {
        viewModelScope.launch {
            categoryRepository.ensureSeedData()
            runCatching {
                walletRepository.refresh()
                transactionRepository.refresh()
                categoryRepository.refresh()
            }
        }
    }

    private fun currentMonthStartMillis(): Long {
        val calendar = java.util.Calendar.getInstance()
        calendar.set(java.util.Calendar.DAY_OF_MONTH, 1)
        calendar.set(java.util.Calendar.HOUR_OF_DAY, 0)
        calendar.set(java.util.Calendar.MINUTE, 0)
        calendar.set(java.util.Calendar.SECOND, 0)
        calendar.set(java.util.Calendar.MILLISECOND, 0)
        return calendar.timeInMillis
    }
}
