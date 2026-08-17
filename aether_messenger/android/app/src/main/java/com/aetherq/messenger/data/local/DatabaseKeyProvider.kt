package com.aetherq.messenger.data.local

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import java.security.SecureRandom

/**
 * SQLCipher uchun baza shifrlash kalitini boshqaradi (smart_moliya loyihasidagi
 * konventsiyaga mos) — 32 baytlik tasodifiy kalit Android Keystore bilan himoyalangan
 * `EncryptedSharedPreferences`da saqlanadi, kalit hech qachon kod ichida yozilmaydi.
 */
class DatabaseKeyProvider(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context).setKeyScheme(MasterKey.KeyScheme.AES256_GCM).build()
        EncryptedSharedPreferences.create(
            context,
            "aetherq_db_key",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun getOrCreatePassphrase(): ByteArray {
        val existing = prefs.getString(KEY_DB_PASSPHRASE, null)
        if (existing != null) {
            return existing.toByteArray(Charsets.UTF_8)
        }

        val randomBytes = ByteArray(32)
        SecureRandom().nextBytes(randomBytes)
        val passphrase = randomBytes.joinToString("") { "%02x".format(it) }
        prefs.edit().putString(KEY_DB_PASSPHRASE, passphrase).apply()
        return passphrase.toByteArray(Charsets.UTF_8)
    }

    companion object {
        private const val KEY_DB_PASSPHRASE = "db_passphrase"
    }
}
