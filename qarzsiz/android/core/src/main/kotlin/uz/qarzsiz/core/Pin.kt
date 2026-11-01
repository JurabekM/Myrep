package uz.qarzsiz.core

import kotlinx.serialization.Serializable
import java.security.MessageDigest
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/**
 * PIN-kod qulfi. PIN o'zi saqlanmaydi — faqat PBKDF2-HMAC-SHA256 xeshi (tasodifiy tuz bilan).
 * Qulf — ilovaga kirish darvozasi; ma'lumotning o'zi Android Keystore kaliti bilan shifrlangan.
 */
@Serializable
data class PinLock(
    /** Tuz, Base64. */
    val salt: String,
    /** PBKDF2 natijasi (32 bayt), Base64. */
    val hash: String,
    val iterations: Int = Pin.DEFAULT_ITERATIONS,
    /** PIN uzunligi — terish tugagach avtomatik tekshirish uchun. */
    val length: Int,
    /** Ketma-ket noto'g'ri urinishlar. */
    val failures: Int = 0,
    /** Shu vaqtgacha (epoch ms) urinish mumkin emas. */
    val lockedUntil: Long = 0,
    /** Ilova fonda shuncha soniya tursa, qaytganda PIN so'raladi (0 — darhol). */
    val graceSeconds: Int = Pin.DEFAULT_GRACE_SECONDS,
)

object Pin {
    const val DEFAULT_ITERATIONS = 120_000
    const val DEFAULT_GRACE_SECONDS = 30
    const val MIN_LENGTH = 4
    const val MAX_LENGTH = 6
    /** Shuncha xatodan keyin kutish boshlanadi. */
    const val FREE_ATTEMPTS = 4
    /** Eng uzun kutish — soat orqaga surilsa ham bundan oshmaydi. */
    const val MAX_LOCKOUT_MS = 15 * 60_000L

    fun isValidFormat(pin: String): Boolean = pin.length in MIN_LENGTH..MAX_LENGTH && pin.all { it in '0'..'9' }

    /** Oson topiladigan PIN: hammasi bir xil raqam yoki ketma-ket (1234, 9876). */
    fun isWeak(pin: String): Boolean {
        if (pin.toSet().size == 1) return true
        val steps = pin.zipWithNext { a, b -> b - a }.toSet()
        return steps == setOf(1) || steps == setOf(-1)
    }

    fun pbkdf2(pin: String, salt: ByteArray, iterations: Int): ByteArray {
        val spec = PBEKeySpec(pin.toCharArray(), salt, iterations, 256)
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }

    fun create(
        pin: String,
        graceSeconds: Int = DEFAULT_GRACE_SECONDS,
        iterations: Int = DEFAULT_ITERATIONS,
        random: SecureRandom = SecureRandom(),
    ): PinLock {
        require(isValidFormat(pin)) { "PIN 4–6 raqam bo'lishi kerak" }
        val salt = ByteArray(16).also(random::nextBytes)
        val b64 = Base64.getEncoder()
        return PinLock(
            salt = b64.encodeToString(salt),
            hash = b64.encodeToString(pbkdf2(pin, salt, iterations)),
            iterations = iterations,
            length = pin.length,
            graceSeconds = graceSeconds,
        )
    }

    /** Doimiy vaqtda solishtirish. */
    fun matches(lock: PinLock, pin: String): Boolean {
        if (!isValidFormat(pin)) return false
        val dec = Base64.getDecoder()
        val expected = dec.decode(lock.hash)
        return MessageDigest.isEqual(expected, pbkdf2(pin, dec.decode(lock.salt), lock.iterations))
    }

    /** `failures` ta xatodan keyingi kutish: 4 tagacha — yo'q, keyin 30 s, 1, 5, 15 daqiqa. */
    fun lockoutMs(failures: Int): Long = when {
        failures <= FREE_ATTEMPTS -> 0
        failures == FREE_ATTEMPTS + 1 -> 30_000
        failures == FREE_ATTEMPTS + 2 -> 60_000
        failures == FREE_ATTEMPTS + 3 -> 5 * 60_000L
        else -> MAX_LOCKOUT_MS
    }

    /** Hozir kutish kerakmi: qolgan ms (0 — urinish mumkin). Soat orqaga surilsa ham ko'pi bilan 15 daqiqa. */
    fun remainingLockMs(lock: PinLock, nowMs: Long): Long =
        (lock.lockedUntil - nowMs).coerceIn(0, MAX_LOCKOUT_MS)

    fun afterFailure(lock: PinLock, nowMs: Long): PinLock {
        val f = lock.failures + 1
        val wait = lockoutMs(f)
        return lock.copy(failures = f, lockedUntil = if (wait > 0) nowMs + wait else 0)
    }

    fun afterSuccess(lock: PinLock): PinLock = lock.copy(failures = 0, lockedUntil = 0)
}
