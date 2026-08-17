package com.smartmoliya.app.feature.expense.domain

import kotlinx.coroutines.flow.Flow

interface TransactionRepository {
    fun observeTransactions(): Flow<List<Transaction>>
    suspend fun refresh()
    suspend fun addTransaction(
        walletId: String,
        categoryId: String?,
        type: TransactionType,
        amount: Double,
        note: String?
    )
    suspend fun deleteTransaction(transactionId: String)
}
