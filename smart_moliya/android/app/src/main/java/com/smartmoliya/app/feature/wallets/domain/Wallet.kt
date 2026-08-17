package com.smartmoliya.app.feature.wallets.domain

data class Wallet(
    val id: String,
    val name: String,
    val currency: String,
    val balance: Double,
    val isShared: Boolean
)
