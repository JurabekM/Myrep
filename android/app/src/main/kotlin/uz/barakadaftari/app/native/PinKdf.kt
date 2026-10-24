package uz.barakadaftari.app.native

import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

/** PIN hosilasi: PBKDF2-HMAC-SHA256 (SPEC 4.5). PIN o'zi hech qayerda saqlanmaydi. */
object PinKdf {
    const val MIN_ITERATIONS = 310_000
    const val KEY_LENGTH_BYTES = 32

    fun derive(
        password: CharArray,
        salt: ByteArray,
        iterations: Int,
        keyLengthBytes: Int = KEY_LENGTH_BYTES,
    ): ByteArray {
        val spec = PBEKeySpec(password, salt, iterations, keyLengthBytes * 8)
        try {
            return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
        } finally {
            spec.clearPassword()
        }
    }
}
