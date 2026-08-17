package com.smartmoliya.app.feature.expense.domain

enum class TransactionType { INCOME, EXPENSE, TRANSFER }

data class Transaction(
    val id: String,
    val walletId: String,
    val categoryId: String?,
    val type: TransactionType,
    val amount: Double,
    val currency: String,
    val note: String?,
    val occurredAt: Long
)
