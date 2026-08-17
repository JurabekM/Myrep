package com.smartmoliya.app.core.network.dto

data class WalletDto(
    val id: String,
    val name: String,
    val currency: String,
    val balance: Double,
    val is_shared: Boolean,
    val version: Int
)

data class WalletCreateDto(
    val id: String,
    val name: String,
    val currency: String = "UZS",
    val is_shared: Boolean = false
)
