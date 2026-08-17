package com.smartmoliya.app.feature.auth.domain

interface AuthRepository {
    fun isLoggedIn(): Boolean
    suspend fun login(phone: String, password: String): Result<Unit>
    suspend fun register(phone: String, password: String, fullName: String?): Result<Unit>

    /** SMS kod so'raydi. Dev backend'da kod natijada qaytadi (SMS o'rniga). */
    suspend fun requestOtp(phone: String): Result<String?>

    suspend fun loginWithOtp(phone: String, code: String): Result<Unit>

    suspend fun loginWithGoogle(idToken: String): Result<Unit>

    fun logout()
}
