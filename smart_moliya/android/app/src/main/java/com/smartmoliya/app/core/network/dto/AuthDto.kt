package com.smartmoliya.app.core.network.dto

data class RegisterRequestDto(
    val phone: String,
    val password: String,
    val full_name: String?,
    val language: String = "uz"
)

data class LoginRequestDto(val phone: String, val password: String, val device_id: String)

data class RefreshRequestDto(val refresh_token: String, val device_id: String)

data class TokenPairDto(
    val access_token: String,
    val refresh_token: String,
    val token_type: String
)

data class OtpRequestDto(val phone: String)

data class OtpRequestResponseDto(
    val message: String,
    val dev_code: String? // faqat dev backend qaytaradi - SMS provayder o'rniga
)

data class OtpVerifyDto(val phone: String, val code: String, val device_id: String)

data class GoogleLoginDto(val id_token: String, val device_id: String)

data class UserDto(
    val id: String,
    val phone: String?,
    val email: String?,
    val full_name: String?,
    val auth_provider: String,
    val language: String,
    val is_active: Boolean
)
