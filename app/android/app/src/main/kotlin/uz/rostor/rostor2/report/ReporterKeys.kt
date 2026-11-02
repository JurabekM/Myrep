package uz.rostor.rostor2.report

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import java.security.SecureRandom
import java.util.Base64
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Hisobot imzolash uchun qurilma kaliti. Android Keystore ML-DSA va (API 33 dan pastda) Ed25519 ni
 * qo'llamaydi, shuning uchun 2×32 baytli urug' ilova xotirasida saqlanadi, lekin Keystore'dagi
 * eksport qilib bo'lmaydigan AES-256-GCM kalit bilan shifrlangan. Zaxira nusxasi o'chiq (allowBackup=false).
 * Kalit faqat foydalanuvchi birinchi hisobotni yaratganda paydo bo'ladi.
 */
class ReporterKeys(private val ctx: Context) {
    private val prefs = ctx.getSharedPreferences("rostor2_keys", Context.MODE_PRIVATE)

    companion object {
        private const val ALIAS = "rostor2_report_wrap"
        private const val PREF = "report_seeds"
    }

    fun exists(): Boolean = prefs.contains(PREF)

    /** (edSeed, mldsaSeed). Shifr ochilmasa (masalan Keystore tozalangan) yangi kalit yaratiladi. */
    fun seeds(): Pair<ByteArray, ByteArray> {
        prefs.getString(PREF, null)?.let { stored ->
            try {
                val raw = Base64.getDecoder().decode(stored)
                val c = Cipher.getInstance("AES/GCM/NoPadding")
                c.init(Cipher.DECRYPT_MODE, wrapKey(), GCMParameterSpec(128, raw, 0, 12))
                val s = c.doFinal(raw, 12, raw.size - 12)
                if (s.size == 64) return s.copyOfRange(0, 32) to s.copyOfRange(32, 64)
            } catch (e: Exception) {
                // pastga: yangi kalit
            }
        }
        val s = ByteArray(64).also { SecureRandom().nextBytes(it) }
        val c = Cipher.getInstance("AES/GCM/NoPadding")
        c.init(Cipher.ENCRYPT_MODE, wrapKey())
        val ct = c.doFinal(s)
        prefs.edit().putString(PREF, Base64.getEncoder().encodeToString(c.iv + ct)).apply()
        return s.copyOfRange(0, 32) to s.copyOfRange(32, 64)
    }

    private fun wrapKey(): SecretKey {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        val g = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore")
        g.init(
            KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return g.generateKey()
    }
}
