package com.smartmoliya.app.core.network.dto

data class TransactionDto(
    val id: String,
    val wallet_id: String,
    val category_id: String?,
    val type: String,
    val amount: Double,
    val currency: String,
    val note: String?,
    val source: String,
    val occurred_at: String,
    val sync_status: String,
    val version: Int
)

data class TransactionCreateDto(
    val id: String,
    val wallet_id: String,
    val category_id: String?,
    val type: String,
    val amount: Double,
    val currency: String = "UZS",
    val note: String?,
    val source: String = "manual",
    val occurred_at: String
)
