package com.smartmoliya.app.core.security

import com.smartmoliya.app.core.datastore.TokenManager
import java.security.MessageDigest
import javax.inject.Inject
import javax.inject.Singleton

/** Ilova qulfi uchun 4-6 xonali PIN - faqat qurilmada tekshiriladi, serverga yuborilmaydi. */
@Singleton
class PinManager @Inject constructor(private val tokenManager: TokenManager) {

    fun isPinSet(): Boolean = tokenManager.hasPinConfigured()

    fun setPin(pin: String) {
        tokenManager.pinHash = hash(pin)
    }

    fun verifyPin(pin: String): Boolean = tokenManager.pinHash == hash(pin)

    fun clearPin() {
        tokenManager.pinHash = null
    }

    private fun hash(pin: String): String {
        val digest = MessageDigest.getInstance("SHA-256").digest(pin.toByteArray(Charsets.UTF_8))
        return digest.joinToString("") { "%02x".format(it) }
    }
}
