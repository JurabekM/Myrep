package uz.barakadaftari.app.native

import java.security.GeneralSecurityException
import javax.crypto.Cipher
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec

/** Kichik maxfiy ma'lumotni (DB kaliti, PIN yozuvi) shifrlash/ochish. */
interface KeyWrapper {
    /** [aad] — bog'langan ma'lumot (blob nomi): boshqa blob o'rniga qo'yilsa ochilmaydi. */
    fun wrap(plain: ByteArray, aad: ByteArray): ByteArray

    /** Buzilgan yoki boshqa kalit bilan yozilgan blob uchun [GeneralSecurityException]. */
    fun unwrap(blob: ByteArray, aad: ByteArray): ByteArray
}

/**
 * AES-256-GCM wrap. Blob formati: `[versiya=1][iv: 12 bayt][shifrmatn + 16 bayt tag]`.
 *
 * IV'ni Cipher o'zi yaratadi — Android Keystore tashqaridan berilgan IV'ni
 * standart holatda rad etadi (randomized encryption).
 */
class AesGcmKeyWrapper(private val keyProvider: () -> SecretKey) : KeyWrapper {

    override fun wrap(plain: ByteArray, aad: ByteArray): ByteArray {
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(Cipher.ENCRYPT_MODE, keyProvider())
        cipher.updateAAD(aad)
        val iv = cipher.iv
        check(iv.size == IV_LENGTH) { "Kutilmagan IV uzunligi: ${iv.size}" }
        val body = cipher.doFinal(plain)
        return byteArrayOf(FORMAT_VERSION) + iv + body
    }

    override fun unwrap(blob: ByteArray, aad: ByteArray): ByteArray {
        if (blob.size < 1 + IV_LENGTH + TAG_LENGTH_BYTES || blob[0] != FORMAT_VERSION) {
            throw GeneralSecurityException("Blob formati noto'g'ri")
        }
        val cipher = Cipher.getInstance(TRANSFORMATION)
        cipher.init(
            Cipher.DECRYPT_MODE,
            keyProvider(),
            GCMParameterSpec(TAG_LENGTH_BYTES * 8, blob, 1, IV_LENGTH),
        )
        cipher.updateAAD(aad)
        return cipher.doFinal(blob, 1 + IV_LENGTH, blob.size - 1 - IV_LENGTH)
    }

    companion object {
        const val TRANSFORMATION = "AES/GCM/NoPadding"
        const val FORMAT_VERSION: Byte = 1
        const val IV_LENGTH = 12
        const val TAG_LENGTH_BYTES = 16
    }
}
