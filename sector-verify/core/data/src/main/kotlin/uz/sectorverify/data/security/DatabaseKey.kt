package uz.sectorverify.data.security

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.io.File
import java.security.KeyStore
import java.security.SecureRandom
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Wraps/unwraps small secrets; Android Keystore in production, a fake in JVM tests. */
interface KeyWrapper {
    fun wrap(plain: ByteArray): ByteArray

    fun unwrap(wrapped: ByteArray): ByteArray
}

/** AES-256-GCM key that never leaves the Android Keystore. Output = 12-byte IV ‖ ciphertext+tag. */
class KeystoreKeyWrapper(private val alias: String = ALIAS) : KeyWrapper {
    private fun key(): SecretKey {
        val ks = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
        (ks.getKey(alias, null) as? SecretKey)?.let { return it }
        val gen = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        gen.init(
            KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(KEY_BITS)
                .build(),
        )
        return gen.generateKey()
    }

    override fun wrap(plain: ByteArray): ByteArray {
        val c = Cipher.getInstance(TRANSFORMATION)
        c.init(Cipher.ENCRYPT_MODE, key())
        return c.iv + c.doFinal(plain)
    }

    override fun unwrap(wrapped: ByteArray): ByteArray {
        val c = Cipher.getInstance(TRANSFORMATION)
        c.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(TAG_BITS, wrapped, 0, IV_BYTES))
        return c.doFinal(wrapped, IV_BYTES, wrapped.size - IV_BYTES)
    }

    companion object {
        const val ALIAS = "sv_db_wrap"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        private const val KEY_BITS = 256
        private const val TAG_BITS = 128
        private const val IV_BYTES = 12
    }
}

/**
 * §5 security: SQLCipher passphrase = 32 random bytes, stored only wrapped by the Keystore key in
 * `noBackupFilesDir` (excluded from backups and device transfer).
 */
class DatabaseKeyStore(private val file: File, private val wrapper: KeyWrapper, private val random: SecureRandom = SecureRandom()) {
    @Synchronized
    fun passphrase(): ByteArray {
        if (file.exists()) return wrapper.unwrap(file.readBytes())
        val key = ByteArray(KEY_BYTES).also(random::nextBytes)
        file.parentFile?.mkdirs()
        val tmp = File(file.parentFile, file.name + ".tmp")
        tmp.writeBytes(wrapper.wrap(key))
        check(tmp.renameTo(file)) { "cannot store database key" }
        return key
    }

    companion object {
        const val KEY_BYTES = 32
        const val FILE_NAME = "db.key.enc"
    }
}
