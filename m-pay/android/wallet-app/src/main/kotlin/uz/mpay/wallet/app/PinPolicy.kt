package uz.mpay.wallet.app

import java.security.MessageDigest

/**
 * Ilova qulfi PIN'i (6 raqam) — platformadan mustaqil siyosat:
 * * tekshirgich = `mac(salt ‖ pin)`; `mac` — Android'da Keystore'dagi chiqarib bo'lmaydigan HMAC kaliti,
 *   ya'ni fayl o'g'irlansa ham PIN'ni qurilmasiz terib topib bo'lmaydi;
 * * oddiy PIN'lar (`111111`, `123456`, `654321`) rad;
 * * ketma-ket xatolar: 5-dan keyin kutish 30 s, so'ng 1, 5, 15 daqiqa (eng ko'pi).
 */
class PinPolicy(private val mac: (ByteArray) -> ByteArray) {
    /** Saqlanadigan holat (sirsiz: salt va tekshirgich). */
    data class State(val salt: ByteArray, val verifier: ByteArray, val failures: Int = 0, val lockedUntil: Long = 0)

    sealed class Check {
        data object Ok : Check()
        data class Wrong(val failures: Int, val lockedUntil: Long) : Check()
        data class Locked(val until: Long) : Check()
    }

    fun valid(pin: String): Boolean {
        if (pin.length != LENGTH || !pin.all(Char::isDigit)) return false
        if (pin.toSet().size == 1) return false
        val d = pin.map { it - '0' }
        val steps = d.zipWithNext { a, b -> b - a }.toSet()
        return steps != setOf(1) && steps != setOf(-1)
    }

    fun create(pin: String, salt: ByteArray): State {
        require(valid(pin)) { "PIN talabga javob bermaydi" }
        return State(salt, verifier(pin, salt))
    }

    private fun verifier(pin: String, salt: ByteArray) = mac(salt + pin.toByteArray(Charsets.US_ASCII))

    /** Tekshiradi va yangi holatni qaytaradi (chaqiruvchi saqlaydi). */
    fun check(s: State, pin: String, nowMs: Long): Pair<Check, State> {
        if (nowMs < s.lockedUntil) return Check.Locked(s.lockedUntil) to s
        if (MessageDigest.isEqual(verifier(pin, s.salt), s.verifier)) return Check.Ok to s.copy(failures = 0, lockedUntil = 0)
        val f = s.failures + 1
        val until = lockout(f)?.let { nowMs + it } ?: 0
        return Check.Wrong(f, until) to s.copy(failures = f, lockedUntil = until)
    }

    companion object {
        const val LENGTH = 6

        /** `failures` ta xatodan keyingi kutish (ms); `null` — kutish yo'q. */
        fun lockout(failures: Int): Long? = when {
            failures < 5 -> null
            failures == 5 -> 30_000L
            failures == 6 -> 60_000L
            failures == 7 -> 5 * 60_000L
            else -> 15 * 60_000L
        }
    }
}
