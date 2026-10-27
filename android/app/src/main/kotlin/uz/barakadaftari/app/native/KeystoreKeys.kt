package uz.barakadaftari.app.native

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import java.security.KeyStore
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey

/**
 * Android Keystore'dagi wrap kaliti (AES-256-GCM). Kalit hech qachon
 * ilova xotirasiga chiqmaydi — barcha shifrlash Keystore ichida bajariladi.
 */
class KeystoreKeys(private val context: Context) {

    @Volatile
    private var cached: SecretKey? = null

    /** StrongBox'da yaratilganmi (diagnostika uchun; maxfiy emas). */
    @Volatile
    var isStrongBoxBacked: Boolean = false
        private set

    @Synchronized
    fun getOrCreateWrappingKey(): SecretKey {
        cached?.let { return it }
        val keyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        val existing = keyStore.getKey(ALIAS, null) as SecretKey?
        val key = existing ?: generate()
        cached = key
        return key
    }

    private fun generate(): SecretKey {
        val wantStrongBox = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P &&
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        if (wantStrongBox) {
            try {
                return generate(strongBox = true).also { isStrongBoxBacked = true }
            } catch (_: StrongBoxUnavailableException) {
                // StrongBox e'lon qilingan, lekin ishlamayapti — oddiy TEE'ga qaytamiz.
            }
        }
        return generate(strongBox = false)
    }

    private fun generate(strongBox: Boolean): SecretKey {
        val spec = KeyGenParameterSpec.Builder(
            ALIAS,
            KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
        )
            .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
            .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
            .setKeySize(256)
            .setRandomizedEncryptionRequired(true)
            .apply { if (strongBox && Build.VERSION.SDK_INT >= Build.VERSION_CODES.P) setIsStrongBoxBacked(true) }
            .build()
        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(spec)
        return generator.generateKey()
    }

    companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val ALIAS = "baraka_wrap_key_v1"
    }
}
