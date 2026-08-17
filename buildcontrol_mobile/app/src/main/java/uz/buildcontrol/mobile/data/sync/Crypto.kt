package uz.buildcontrol.mobile.data.sync

import android.util.Base64
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import javax.crypto.Cipher
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.GCMParameterSpec
import javax.crypto.spec.PBEKeySpec
import javax.crypto.spec.SecretKeySpec
import java.security.SecureRandom

/**
 * Optional payload encryption, byte-compatible with `app/sync/crypto.py`.
 *
 * A free public MQTT broker is readable by anyone who guesses the topic, so the
 * change envelopes are sealed with AES-256-GCM. The key is derived from the
 * shared passphrase with the workspace key as salt, so every installation of
 * the same workspace ends up with the same key without exchanging anything.
 */
object Crypto {

    const val MARKER = "a256gcm"
    private const val ITERATIONS = 200_000
    private const val KEY_BITS = 256
    private const val NONCE_BYTES = 12
    private const val TAG_BITS = 128

    class DecryptionException(message: String) : Exception(message)

    fun deriveKey(passphrase: String, salt: String): ByteArray {
        val spec = PBEKeySpec(passphrase.toCharArray(), salt.toByteArray(), ITERATIONS, KEY_BITS)
        return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256").generateSecret(spec).encoded
    }

    fun encrypt(body: JsonObject, key: ByteArray): ByteArray {
        val nonce = ByteArray(NONCE_BYTES).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
            init(Cipher.ENCRYPT_MODE, SecretKeySpec(key, "AES"), GCMParameterSpec(TAG_BITS, nonce))
        }
        val plaintext = SyncJson.encodeToString(JsonObject.serializer(), body).toByteArray()
        val ciphertext = cipher.doFinal(plaintext)
        val envelope = buildString {
            append("{\"enc\":\"").append(MARKER)
            append("\",\"n\":\"").append(b64(nonce))
            append("\",\"c\":\"").append(b64(ciphertext)).append("\"}")
        }
        return envelope.toByteArray()
    }

    /** Opens a payload, passing unencrypted ones straight through. */
    fun decrypt(raw: ByteArray, key: ByteArray?): JsonObject {
        val body = SyncJson.parseToJsonElement(raw.decodeToString()).jsonObject
        if (body["enc"]?.jsonPrimitive?.contentOrNull != MARKER) return body
        if (key == null) {
            throw DecryptionException("payload is encrypted but no passphrase is configured")
        }
        return try {
            val nonce = unb64(body.getValue("n").jsonPrimitive.content)
            val ciphertext = unb64(body.getValue("c").jsonPrimitive.content)
            val cipher = Cipher.getInstance("AES/GCM/NoPadding").apply {
                init(
                    Cipher.DECRYPT_MODE,
                    SecretKeySpec(key, "AES"),
                    GCMParameterSpec(TAG_BITS, nonce),
                )
            }
            SyncJson.parseToJsonElement(cipher.doFinal(ciphertext).decodeToString()).jsonObject
        } catch (exc: Exception) {
            throw DecryptionException("wrong passphrase or damaged payload")
        }
    }

    private fun b64(data: ByteArray): String = Base64.encodeToString(data, Base64.NO_WRAP)

    private fun unb64(text: String): ByteArray = Base64.decode(text, Base64.DEFAULT)
}
