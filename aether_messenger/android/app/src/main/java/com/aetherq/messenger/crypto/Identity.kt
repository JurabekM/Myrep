package com.aetherq.messenger.crypto

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.security.MessageDigest

/**
 * Qurilmaning o'z uzoq-muddatli identity kalitlar to'plami: Ed25519 (imzo), X25519
 * (statik DH), ML-KEM-768 (post-kvant KEM) — AUTH-AKEM handshake'ida ishlatiladi.
 * `zRecip` — Implicit Rejection uchun `sk_x25519` bilan birga saqlanadigan alohida
 * maxfiy qiymat (spec 4.1-bo'lim, band 4).
 */
data class Identity(
    val userId: String,
    val edPk: ByteArray,
    val edSk: ByteArray,
    val xPk: ByteArray,
    val xSk: ByteArray,
    val mlkemPk: ByteArray,
    val mlkemSk: ByteArray,
    val zRecip: ByteArray,
)

/** Identity — Android Keystore bilan himoyalangan `EncryptedSharedPreferences`da saqlanadi. */
class IdentityStore(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            context,
            "aetherq_identity",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    /** Mavjud identity'ni qaytaradi, bo'lmasa yangisini generatsiya qilib saqlaydi. */
    fun getOrCreate(): Identity {
        prefs.getString(KEY_USER_ID, null)?.let { userId ->
            return Identity(
                userId = userId,
                edPk = hexToBytes(prefs.getString(KEY_ED_PK, "")!!),
                edSk = hexToBytes(prefs.getString(KEY_ED_SK, "")!!),
                xPk = hexToBytes(prefs.getString(KEY_X_PK, "")!!),
                xSk = hexToBytes(prefs.getString(KEY_X_SK, "")!!),
                mlkemPk = hexToBytes(prefs.getString(KEY_MLKEM_PK, "")!!),
                mlkemSk = hexToBytes(prefs.getString(KEY_MLKEM_SK, "")!!),
                zRecip = hexToBytes(prefs.getString(KEY_Z_RECIP, "")!!),
            )
        }

        val edKp = AetherCrypto.generateEd25519Identity()
        val xKp = AetherCrypto.generateX25519Identity()
        val mlkemKp = AetherCrypto.generateMlKem768Identity()
        val zRecip = AetherCrypto.randomBytes(32)
        val userId = MessageDigest.getInstance("SHA-256").digest(edKp.publicKey).take(8).toByteArray().toHex()

        prefs.edit()
            .putString(KEY_USER_ID, userId)
            .putString(KEY_ED_PK, edKp.publicKey.toHex())
            .putString(KEY_ED_SK, edKp.secretKey.toHex())
            .putString(KEY_X_PK, xKp.publicKey.toHex())
            .putString(KEY_X_SK, xKp.secretKey.toHex())
            .putString(KEY_MLKEM_PK, mlkemKp.publicKey.toHex())
            .putString(KEY_MLKEM_SK, mlkemKp.secretKey.toHex())
            .putString(KEY_Z_RECIP, zRecip.toHex())
            .apply()

        return Identity(userId, edKp.publicKey, edKp.secretKey, xKp.publicKey, xKp.secretKey, mlkemKp.publicKey, mlkemKp.secretKey, zRecip)
    }

    companion object {
        private const val KEY_USER_ID = "user_id"
        private const val KEY_ED_PK = "ed_pk"
        private const val KEY_ED_SK = "ed_sk"
        private const val KEY_X_PK = "x_pk"
        private const val KEY_X_SK = "x_sk"
        private const val KEY_MLKEM_PK = "mlkem_pk"
        private const val KEY_MLKEM_SK = "mlkem_sk"
        private const val KEY_Z_RECIP = "z_recip"
    }
}
