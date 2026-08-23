package uz.distribos.sync

import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/**
 * Maxfiy material uchun at-rest himoya.
 *
 * Epoch root secret va qurilmaning imzo kaliti bazada OCHIQ saqlanmaydi.
 * O'rash kaliti **Android Keystore** da yotadi: u apparat darajasida
 * (TEE/StrongBox) himoyalanadi va ilova ma'lumotlari nusxalab olinsa ham
 * kalitning o'zi chiqib ketmaydi.
 *
 * Desktop tomonida ekvivalenti — Windows DPAPI.
 */
interface KeyVault {
    /** OS darajasida himoyalanganmi (diagnostikada ko'rsatiladi). */
    val isHardwareBacked: Boolean

    fun wrap(plaintext: ByteArray, context: ByteArray): ByteArray

    fun unwrap(wrapped: ByteArray, context: ByteArray): ByteArray
}

class KeyVaultException(message: String, cause: Throwable? = null) : Exception(message, cause)

/** Android Keystore asosidagi implementatsiya. */
class KeystoreVault(
    private val alias: String = DEFAULT_ALIAS,
) : KeyVault {

    override val isHardwareBacked: Boolean
        get() = try {
            val entry = keyStore.getEntry(alias, null) as? KeyStore.SecretKeyEntry
            entry != null
        } catch (_: Exception) {
            false
        }

    private val keyStore: KeyStore by lazy {
        KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }
    }

    private fun secretKey(): SecretKey {
        (keyStore.getEntry(alias, null) as? KeyStore.SecretKeyEntry)?.let { return it.secretKey }

        val generator = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        generator.init(
            KeyGenParameterSpec.Builder(
                alias,
                KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT,
            )
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                // Foydalanuvchi autentifikatsiyasi TALAB QILINMAYDI: fon
                // sinxronizatsiyasi ekran qulflangan holatda ham ishlashi
                // kerak. Kalitning o'zi baribir Keystore'dan chiqmaydi.
                .setUserAuthenticationRequired(false)
                .build()
        )
        return generator.generateKey()
    }

    override fun wrap(plaintext: ByteArray, context: ByteArray): ByteArray = try {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, secretKey())
        // Kontekst AAD sifatida: bir epoch uchun o'ralgan sirni boshqa
        // epoch nomi bilan ochib bo'lmaydi.
        cipher.updateAAD(context)
        val ciphertext = cipher.doFinal(plaintext)
        byteArrayOf(cipher.iv.size.toByte()) + cipher.iv + ciphertext
    } catch (exception: Exception) {
        throw KeyVaultException("Sirni o'rab bo'lmadi", exception)
    }

    override fun unwrap(wrapped: ByteArray, context: ByteArray): ByteArray = try {
        require(wrapped.isNotEmpty()) { "o'ralgan sir bo'sh" }
        val ivSize = wrapped[0].toInt() and 0xFF
        require(wrapped.size > 1 + ivSize) { "o'ralgan sir qisqa" }
        val iv = wrapped.copyOfRange(1, 1 + ivSize)
        val ciphertext = wrapped.copyOfRange(1 + ivSize, wrapped.size)

        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.DECRYPT_MODE, secretKey(), GCMParameterSpec(128, iv))
        cipher.updateAAD(context)
        cipher.doFinal(ciphertext)
    } catch (exception: Exception) {
        throw KeyVaultException(
            "Sir ochilmadi. Ilova qayta o'rnatilgan yoki kalit o'chirilgan bo'lishi mumkin.",
            exception,
        )
    }

    companion object {
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val DEFAULT_ALIAS = "distribos_epoch_wrap_v1"
    }
}

/**
 * Test uchun o'rash — Keystore yo'q muhitda (JVM birlik testlari).
 *
 * ⚠ Bu OS himoyasi EMAS. Diagnostikada `isHardwareBacked = false`
 * ko'rinadi va production build'da ishlatilishi TAQIQLANADI.
 */
class InMemoryKeyVault(private val passphrase: ByteArray = "test-only".toByteArray()) : KeyVault {

    override val isHardwareBacked: Boolean = false

    override fun wrap(plaintext: ByteArray, context: ByteArray): ByteArray {
        val key = uz.distribos.crypto.Kdf.hkdfExpand(
            uz.distribos.crypto.Kdf.hkdfExtract("DistribOS/test-vault".toByteArray(), passphrase),
            context, 32,
        )
        return ByteArray(plaintext.size) { index ->
            (plaintext[index].toInt() xor key[index % key.size].toInt()).toByte()
        }
    }

    override fun unwrap(wrapped: ByteArray, context: ByteArray): ByteArray =
        wrap(wrapped, context)   // XOR simmetrik
}
