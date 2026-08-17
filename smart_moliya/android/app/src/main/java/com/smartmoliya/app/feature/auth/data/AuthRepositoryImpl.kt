package com.smartmoliya.app.feature.auth.data

import com.smartmoliya.app.core.datastore.TokenManager
import com.smartmoliya.app.core.network.ApiService
import com.smartmoliya.app.core.network.dto.GoogleLoginDto
import com.smartmoliya.app.core.network.dto.LoginRequestDto
import com.smartmoliya.app.core.network.dto.OtpRequestDto
import com.smartmoliya.app.core.network.dto.OtpVerifyDto
import com.smartmoliya.app.core.network.dto.RegisterRequestDto
import com.smartmoliya.app.core.network.dto.TokenPairDto
import com.smartmoliya.app.core.security.DeviceIdProvider
import com.smartmoliya.app.feature.auth.domain.AuthRepository
import javax.inject.Inject

class AuthRepositoryImpl @Inject constructor(
    private val api: ApiService,
    private val tokenManager: TokenManager,
    private val deviceIdProvider: DeviceIdProvider
) : AuthRepository {

    override fun isLoggedIn(): Boolean = tokenManager.isLoggedIn()

    override suspend fun login(phone: String, password: String): Result<Unit> = runCatching {
        val tokens = api.login(LoginRequestDto(phone, password, deviceIdProvider.deviceId))
        saveTokens(tokens)
    }

    override suspend fun requestOtp(phone: String): Result<String?> = runCatching {
        api.requestOtp(OtpRequestDto(phone)).dev_code
    }

    override suspend fun loginWithOtp(phone: String, code: String): Result<Unit> = runCatching {
        val tokens = api.verifyOtp(OtpVerifyDto(phone, code, deviceIdProvider.deviceId))
        saveTokens(tokens)
    }

    override suspend fun loginWithGoogle(idToken: String): Result<Unit> = runCatching {
        val tokens = api.googleLogin(GoogleLoginDto(idToken, deviceIdProvider.deviceId))
        saveTokens(tokens)
    }

    private fun saveTokens(tokens: TokenPairDto) {
        tokenManager.accessToken = tokens.access_token
        tokenManager.refreshToken = tokens.refresh_token
    }

    override suspend fun register(phone: String, password: String, fullName: String?): Result<Unit> = runCatching {
        api.register(RegisterRequestDto(phone = phone, password = password, full_name = fullName))
        // Ro'yxatdan o'tgach avtomatik login qilamiz
        login(phone, password).getOrThrow()
    }

    override fun logout() {
        tokenManager.clearSession()
    }
}
