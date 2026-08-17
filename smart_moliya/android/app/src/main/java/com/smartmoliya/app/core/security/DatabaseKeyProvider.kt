package com.smartmoliya.app.core.security

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import java.security.SecureRandom
import javax.inject.Inject
import javax.inject.Singleton

/**
 * SQLCipher uchun baza shifrlash kalitini boshqaradi.
 *
 * Birinchi ishga tushishda 32 baytlik tasodifiy kalit yaratiladi va Android
 * Keystore bilan himoyalangan EncryptedSharedPreferences'da saqlanadi -
 * kalit hech qachon kod ichida yozilmaydi va qurilmadan chiqmaydi.
 */
@Singleton
class DatabaseKeyProvider @Inject constructor(@ApplicationContext context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "smart_moliya_db_key",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    /** Mavjud kalitni qaytaradi, bo'lmasa yangi yaratib saqlaydi. */
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
