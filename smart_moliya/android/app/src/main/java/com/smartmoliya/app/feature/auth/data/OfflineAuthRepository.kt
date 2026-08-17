package com.smartmoliya.app.feature.auth.data

import com.smartmoliya.app.feature.auth.domain.AuthRepository
import javax.inject.Inject

/**
 * Offline flavor uchun auth: server yo'q, hisob ham yo'q - foydalanuvchi doim
 * "kirgan" hisoblanadi, ilova to'g'ridan-to'g'ri PIN o'rnatish/ochish bosqichidan
 * boshlanadi. Barcha ma'lumot faqat qurilmadagi shifrlangan bazada saqlanadi.
 */
class OfflineAuthRepository @Inject constructor() : AuthRepository {

    override fun isLoggedIn(): Boolean = true

    override suspend fun login(phone: String, password: String): Result<Unit> = Result.success(Unit)

    override suspend fun register(phone: String, password: String, fullName: String?): Result<Unit> =
        Result.success(Unit)

    override suspend fun requestOtp(phone: String): Result<String?> = Result.success(null)

    override suspend fun loginWithOtp(phone: String, code: String): Result<Unit> = Result.success(Unit)

    override suspend fun loginWithGoogle(idToken: String): Result<Unit> = Result.success(Unit)

    override fun logout() {
        // Offline rejimda chiqish tushunchasi yo'q
    }
}
