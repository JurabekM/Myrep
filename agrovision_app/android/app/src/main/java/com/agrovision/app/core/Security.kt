package com.agrovision.app.core

import com.agrovision.app.config.Constants
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * Parol xeshlash — desktop `core/security.py` bilan AYNAN bir xil format:
 * `pbkdf2$iterations$salt_hex$digest_hex`, PBKDF2-HMAC-SHA256, 120 000 iteratsiya.
 */
object Security {
    private const val ITERATIONS = 120_000
    private const val KEY_LENGTH = 256

    fun hashPassword(password: String): String {
        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val digest = pbkdf2(password, salt, ITERATIONS)
        return "pbkdf2$$ITERATIONS$${salt.toHex()}$${digest.toHex()}"
    }

    fun verifyPassword(password: String, stored: String): Boolean = try {
        val parts = stored.split("$")
        if (parts.size != 4 || parts[0] != "pbkdf2") {
            false
        } else {
            val candidate = pbkdf2(password, parts[2].hexToBytes(), parts[1].toInt()).toHex()
            constantTimeEquals(candidate, parts[3])
        }
    } catch (e: Exception) {
        false
    }

    private fun pbkdf2(password: String, salt: ByteArray, iterations: Int): ByteArray =
        SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(PBEKeySpec(password.toCharArray(), salt, iterations, KEY_LENGTH))
            .encoded

    private fun constantTimeEquals(a: String, b: String): Boolean {
        if (a.length != b.length) return false
        var diff = 0
        for (i in a.indices) diff = diff or (a[i].code xor b[i].code)
        return diff == 0
    }

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
    private fun String.hexToBytes(): ByteArray = chunked(2).map { it.toInt(16).toByte() }.toByteArray()
}

/** Rol → ruxsatlar (desktop `ROLES` bilan aynan bir xil). */
object Rbac {
    private val roles: Map<String, Set<String>> = mapOf(
        "admin" to setOf(
            "view_dashboard", "edit_data", "import_data", "export_reports",
            "manage_users", "manage_settings", "backup", "use_ai", "view_finance",
        ),
        "manager" to setOf(
            "view_dashboard", "edit_data", "import_data", "export_reports", "use_ai", "view_finance",
        ),
        "viewer" to setOf("view_dashboard", "use_ai"),
    )

    val allRoles = listOf("admin", "manager", "viewer")

    fun has(role: String?, permission: String): Boolean = roles[role]?.contains(permission) == true

    fun label(role: String): String = when (role) {
        "admin" -> "Administrator"
        "manager" -> "Menejer"
        else -> "Kuzatuvchi"
    }
}

data class SessionUser(val id: Long, val username: String, val fullName: String, val role: String)

/** Joriy sessiya — yagona qurilma, server-sessiya kerak emas. */
object Session {
    @Volatile
    var current: SessionUser? = null
        private set

    fun login(user: SessionUser) { current = user }
    fun logout() { current = null }
    fun can(permission: String): Boolean = Rbac.has(current?.role, permission)
}

/**
 * Login urinishlarini cheklash (desktop `RateLimiter`): N marta xato → vaqtincha bloklash.
 */
class RateLimiter(
    private val maxAttempts: Int = Constants.LOGIN_MAX_ATTEMPTS,
    private val lockMinutes: Int = Constants.LOGIN_LOCK_MINUTES,
) {
    private val attempts = mutableMapOf<String, MutableList<Long>>()
    private val lockedUntil = mutableMapOf<String, Long>()

    @Synchronized
    fun isLocked(key: String): Boolean {
        val until = lockedUntil[key] ?: return false
        if (until > System.currentTimeMillis()) return true
        lockedUntil.remove(key)
        return false
    }

    @Synchronized
    fun lockRemainingMinutes(key: String): Int {
        val until = lockedUntil[key] ?: return 0
        val remaining = until - System.currentTimeMillis()
        return if (remaining <= 0) 0 else ((remaining / 60_000) + 1).toInt()
    }

    @Synchronized
    fun registerFailure(key: String) {
        val now = System.currentTimeMillis()
        val history = (attempts[key] ?: mutableListOf()).filter { now - it < 600_000 }.toMutableList()
        history += now
        attempts[key] = history
        if (history.size >= maxAttempts) {
            lockedUntil[key] = now + lockMinutes * 60_000L
            attempts[key] = mutableListOf()
        }
    }

    @Synchronized
    fun registerSuccess(key: String) {
        attempts.remove(key)
        lockedUntil.remove(key)
    }
}
