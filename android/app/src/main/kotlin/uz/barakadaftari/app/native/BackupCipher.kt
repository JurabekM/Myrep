package uz.barakadaftari.app.native

import java.nio.ByteBuffer
import java.security.SecureRandom
import javax.crypto.AEADBadTagException
import javax.crypto.Cipher
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.SecretKeySpec

/**
 * Zaxira nusxa shifri (MVP_PLAN Vazifa 15): foydalanuvchi parolidan
 * PBKDF2-HMAC-SHA256 bilan kalit, AES-256-GCM bilan shifrlash.
 *
 * Format: `BRKD` (4) · versiya (1) · iteratsiya (4, big-endian) · tuz (16) ·
 * IV (12) · shifrmatn+teg. Sarlavha GCM'ga AAD sifatida beriladi — uni
 * o'zgartirib bo'lmaydi.
 */
object BackupCipher {
    private val MAGIC = byteArrayOf('B'.code.toByte(), 'R'.code.toByte(), 'K'.code.toByte(), 'D'.code.toByte())
    private const val VERSION: Byte = 1
    const val ITERATIONS = 310_000
    private const val SALT = 16
    private const val IV = 12
    private const val TAG_BITS = 128
    private const val HEADER = 4 + 1 + 4 + SALT + IV

    /** Parol noto'g'ri yoki fayl buzilgan. */
    class BadPasswordException : Exception()

    /** Bu zaxira nusxa fayli emas yoki versiyasi noma'lum. */
    class FormatException : Exception()

    fun encrypt(
        password: CharArray,
        plain: ByteArray,
        iterations: Int = ITERATIONS,
        random: SecureRandom = SecureRandom(),
    ): ByteArray {
        val salt = ByteArray(SALT).also(random::nextBytes)
        val iv = ByteArray(IV).also(random::nextBytes)
        val header = ByteBuffer.allocate(HEADER)
            .put(MAGIC).put(VERSION).putInt(iterations).put(salt).put(iv)
            .array()
        val key = PinKdf.derive(password, salt, iterations)
        try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_BITS, iv))
            cipher.updateAAD(header)
            return header + cipher.doFinal(plain)
        } finally {
            key.fill(0)
        }
    }

    fun decrypt(password: CharArray, data: ByteArray): ByteArray {
        if (data.size <= HEADER) throw FormatException()
        val buf = ByteBuffer.wrap(data)
        val magic = ByteArray(4).also { buf.get(it) }
        if (!magic.contentEquals(MAGIC) || buf.get() != VERSION) throw FormatException()
        val iterations = buf.getInt()
        if (iterations < PinKdf.MIN_ITERATIONS || iterations > 10_000_000) throw FormatException()
        val salt = ByteArray(SALT).also { buf.get(it) }
        val iv = ByteArray(IV).also { buf.get(it) }
        val header = data.copyOfRange(0, HEADER)
        val key = PinKdf.derive(password, salt, iterations)
        try {
            val cipher = Cipher.getInstance("AES/GCM/NoPadding")
            cipher.init(Cipher.DECRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_BITS, iv))
            cipher.updateAAD(header)
            return cipher.doFinal(data, HEADER, data.size - HEADER)
        } catch (e: AEADBadTagException) {
            throw BadPasswordException()
        } finally {
            key.fill(0)
        }
    }
}
