package com.smartmoliya.app.core.network.dto

data class PaymentDto(
    val id: String,
    val wallet_id: String,
    val provider: String,
    val amount: Double,
    val currency: String,
    val status: String, // pending | paid | failed | canceled
    val checkout_url: String?
)

data class PaymentCreateDto(
    val wallet_id: String,
    val provider: String, // click | payme | uzum
    val amount: Double,
    val return_url: String = "smartmoliya://payment-result"
)
