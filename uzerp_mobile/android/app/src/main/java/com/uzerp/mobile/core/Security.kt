package com.uzerp.mobile.core

import java.security.SecureRandom
import java.security.spec.KeySpec
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec
import kotlin.random.Random

/**
 * Parol xavfsizligi — PBKDF2-HMAC-SHA256 (240 000 iteratsiya), Python
 * backend bilan bir xil tamoyil (tuz + iteratsiya soni saqlanadi).
 *
 * Format: `pbkdf2_sha256$<iteratsiya>$<tuz_hex>$<xesh_hex>`
 */
object PasswordHasher {
    private const val ALGO = "pbkdf2_sha256"
    private const val ITERATIONS = 240_000
    private const val KEY_LENGTH = 256
    private val random = SecureRandom()

    fun hash(password: String): String {
        val salt = ByteArray(16).also { random.nextBytes(it) }
        val digest = pbkdf2(password, salt, ITERATIONS)
        return "$ALGO$$ITERATIONS$${salt.toHex()}$${digest.toHex()}"
    }

    fun verify(password: String, stored: String): Boolean {
        val parts = stored.split("$")
        if (parts.size != 4 || parts[0] != ALGO) return false
        return try {
            val iterations = parts[1].toInt()
            val salt = parts[2].hexToBytes()
            val expected = parts[3]
            val digest = pbkdf2(password, salt, iterations)
            constantTimeEquals(digest.toHex(), expected)
        } catch (_: Exception) {
            false
        }
    }

    /** Parol siyosatini tekshiradi; muammo bo'lsa xato matnini qaytaradi. */
    fun checkPolicy(password: String, minLength: Int = 8): String? {
        if (password.length < minLength) {
            return "Parol kamida $minLength ta belgidan iborat bo'lishi kerak."
        }
        if (password.none { it.isDigit() }) return "Parolda kamida bitta raqam bo'lishi kerak."
        if (password.none { it.isLetter() }) return "Parolda kamida bitta harf bo'lishi kerak."
        return null
    }

    /** Siyosatga mos tasodifiy parol generatsiya qiladi (admin bootstrap uchun). */
    fun generatePassword(length: Int = 12): String {
        val alphabet = "abcdefghjkmnpqrstuvwxyzABCDEFGHJKMNPQRSTUVWXYZ23456789"
        while (true) {
            val candidate = (1..length).map { alphabet[Random.nextInt(alphabet.length)] }
                .joinToString("")
            if (checkPolicy(candidate) == null) return candidate
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
