package uz.baraka.oilasi

import android.content.Context
import android.content.pm.PackageManager
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import java.io.File
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Platforma siri (BARAKA_OILASI 7.2): 32 bayt tasodifiy qiymat, Android Keystore'dagi AES-256-GCM
 * kalit bilan o'ralib, ilovaning private storage'ida saqlanadi. Keystore kaliti qurilmadan
 * chiqmaydi (StrongBox bo'lsa — StrongBox'da). Sir faqat Rust yadroga uzatiladi va u yerda
 * PIN bilan birga KEK hosil qiladi — faqat shu sir bilan ham, faqat PIN bilan ham baza ochilmaydi.
 */
class PlatformSecretStore(private val context: Context) : PlatformSecretApi {
    private val file = File(context.noBackupFilesDir, "platform_secret.v1")

    override fun getOrCreatePlatformSecret(): ByteArray {
        if (file.exists()) return loadPlatformSecret()
        val secret = ByteArray(SECRET_LEN).also { SecureRandom().nextBytes(it) }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, key(create = true))
        val sealed = cipher.iv + cipher.doFinal(secret)
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeBytes(sealed)
        if (!tmp.renameTo(file)) throw FlutterError("KEYFILE_CORRUPT", "platform secret not stored", null)
        return secret
    }

    override fun loadPlatformSecret(): ByteArray {
        if (!file.exists()) throw FlutterError("PLATFORM_SECRET_MISSING", "platform secret missing", null)
        val sealed = file.readBytes()
        if (sealed.size <= IV_LEN) throw FlutterError("KEYFILE_CORRUPT", "platform secret corrupt", null)
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, key(create = false), GCMParameterSpec(TAG_BITS, sealed, 0, IV_LEN))
        return try {
            cipher.doFinal(sealed, IV_LEN, sealed.size - IV_LEN)
        } catch (e: Exception) {
            throw FlutterError("KEYFILE_CORRUPT", "platform secret corrupt", null)
        }
    }

    private fun key(create: Boolean): SecretKey {
        val ks = KeyStore.getInstance(KEYSTORE).apply { load(null) }
        (ks.getKey(ALIAS, null) as? SecretKey)?.let { return it }
        if (!create) throw FlutterError("PLATFORM_SECRET_MISSING", "keystore key missing", null)
        val strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        return try {
            generate(strongBox)
        } catch (e: StrongBoxUnavailableException) {
            generate(false)
        }
    }

    private fun generate(strongBox: Boolean): SecretKey {
        val spec = KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .apply { if (strongBox) setIsStrongBoxBacked(true) }
            .build()
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, KEYSTORE).run {
            init(spec)
            generateKey()
        }
    }

    private companion object {
        const val KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "baraka.platform_secret.v1"
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val SECRET_LEN = 32
        const val IV_LEN = 12
        const val TAG_BITS = 128
    }
}
