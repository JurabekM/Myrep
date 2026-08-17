package com.agrovision.mobile.core

import java.security.SecureRandom
import java.security.spec.KeySpec
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * PBKDF2-HMAC-SHA256 parol xeshlash — desktop AgroVision (core/security.py)
 * bilan bir xil format: "pbkdf2$iterations$salt_hex$digest_hex".
 */
object Security {
    private const val ITERATIONS = 120_000
    private const val KEY_LENGTH = 256

    fun hashPassword(password: String): String {
        val salt = ByteArray(16).also { SecureRandom().nextBytes(it) }
        val digest = pbkdf2(password, salt, ITERATIONS)
        return "pbkdf2$$ITERATIONS$${salt.toHex()}$${digest.toHex()}"
    }

    fun verifyPassword(password: String, stored: String): Boolean {
        return try {
            val parts = stored.split("$")
            if (parts.size != 4 || parts[0] != "pbkdf2") return false
            val iterations = parts[1].toInt()
            val salt = parts[2].hexToBytes()
            val expected = parts[3]
            val candidate = pbkdf2(password, salt, iterations).toHex()
            constantTimeEquals(candidate, expected)
        } catch (e: Exception) {
            false
        }
    }

    private fun pbkdf2(password: String, salt: ByteArray, iterations: Int): ByteArray {
        val spec: KeySpec = PBEKeySpec(password.toCharArray(), salt, iterations, KEY_LENGTH)
        val factory = SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
        return factory.generateSecret(spec).encoded
    }

    private fun constantTimeEquals(a: String, b: String): Boolean {
        if (a.length != b.length) return false
        var result = 0
        for (i in a.indices) result = result or (a[i].code xor b[i].code)
        return result == 0
    }

    private fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }
    private fun String.hexToBytes(): ByteArray =
        chunked(2).map { it.toInt(16).toByte() }.toByteArray()
}

/** Rol-asosli ruxsatlar — desktop core/security.py ROLES bilan bir xil. */
object Rbac {
    private val roles: Map<String, Set<String>> = mapOf(
        "admin" to setOf(
            "view_dashboard", "edit_data", "import_data", "export_reports",
            "manage_users", "manage_settings", "backup", "use_ai", "view_finance",
        ),
        "manager" to setOf(
            "view_dashboard", "edit_data", "import_data", "export_reports",
            "use_ai", "view_finance",
        ),
        "viewer" to setOf("view_dashboard", "use_ai"),
    )

    fun has(role: String?, permission: String): Boolean =
        roles[role]?.contains(permission) == true
}

/** Joriy sessiya — yagona qurilma, server-sessiya kerak emas. */
data class SessionUser(val id: Long, val username: String, val fullName: String, val role: String)

object Session {
    @Volatile var current: SessionUser? = null
        private set

    fun login(user: SessionUser) {
        current = user
    }

    fun logout() {
        current = null
    }
}
