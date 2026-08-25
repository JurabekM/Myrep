package uz.distribos.crypto

import org.bouncycastle.pqc.crypto.mldsa.MLDSAKeyGenerationParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSAKeyPairGenerator
import org.bouncycastle.pqc.crypto.mldsa.MLDSAParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSAPrivateKeyParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSAPublicKeyParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSASigner
import java.security.SecureRandom

/**
 * ML-DSA-65 (FIPS 204) — post-kvant raqamli imzo.
 *
 * Har bir DES-1 envelope shu kalit bilan imzolanadi. Bu guruh kalitidan
 * kuchliroq himoya: epoch kalitini bilgan a'zo ham BOSHQA qurilma
 * nomidan hodisa yasay olmaydi. Audit va «bekor qilingan qurilma rad
 * etiladi» talabi aynan shunga tayanadi.
 *
 * O'lchamlar (AETHER-Q spec §2): PK = 1952 B, Sig = 3309 B.
 *
 * Python tomonida bu OpenSSL orqali (`cryptography` kutubxonasi), bu
 * yerda BouncyCastle orqali. Ikkalasi ham FIPS 204, ya'ni bir tomon
 * yaratgan imzoni ikkinchisi TEKSHIRA OLADI. Buni `MlDsaInteropTest`
 * Python yozgan haqiqiy imzolar ustida tasdiqlaydi.
 *
 * DIQQAT: imzo baytlari har safar FARQ QILADI (ML-DSA hedged, ya'ni
 * tasodifiylik qo'shadi). Shuning uchun imzolarni baytma-bayt
 * solishtirish MUMKIN EMAS — faqat tekshirish.
 */
object MlDsa65 {

    const val PUBLIC_KEY_SIZE = 1952
    const val SIGNATURE_SIZE = 3309

    private val parameters = MLDSAParameters.ml_dsa_65

    data class KeyPair(val publicKey: ByteArray, val privateKey: ByteArray) {
        override fun equals(other: Any?): Boolean =
            this === other || (other is KeyPair && publicKey.contentEquals(other.publicKey))

        override fun hashCode(): Int = publicKey.contentHashCode()

        override fun toString(): String = "MlDsa65.KeyPair(<secrets hidden>)"
    }

    fun generate(random: SecureRandom = SecureRandom()): KeyPair {
        val generator = MLDSAKeyPairGenerator()
        generator.init(MLDSAKeyGenerationParameters(random, parameters))
        val pair = generator.generateKeyPair()
        val public = (pair.public as MLDSAPublicKeyParameters).encoded
        val private = (pair.private as MLDSAPrivateKeyParameters).encoded
        require(public.size == PUBLIC_KEY_SIZE) {
            "ML-DSA-65 ochiq kaliti $PUBLIC_KEY_SIZE bayt bo'lishi kerak, ${public.size} chiqdi"
        }
        return KeyPair(public, private)
    }

    fun sign(privateKey: ByteArray, message: ByteArray): ByteArray {
        val signer = MLDSASigner()
        signer.init(true, MLDSAPrivateKeyParameters(parameters, privateKey))
        signer.update(message, 0, message.size)
        val signature = signer.generateSignature()
        require(signature.size == SIGNATURE_SIZE) {
            "kutilmagan imzo uzunligi: ${signature.size}"
        }
        return signature
    }

    /** Imzoni tekshiradi. Istisno ko'tarmaydi — `false` qaytaradi. */
    fun verify(publicKey: ByteArray, signature: ByteArray, message: ByteArray): Boolean =
        try {
            if (publicKey.size != PUBLIC_KEY_SIZE || signature.size != SIGNATURE_SIZE) {
                false
            } else {
                val signer = MLDSASigner()
                signer.init(false, MLDSAPublicKeyParameters(parameters, publicKey))
                signer.update(message, 0, message.size)
                signer.verifySignature(signature)
            }
        } catch (_: Exception) {
            // Buzilgan kalit yoki imzo — tekshirish muvaffaqiyatsiz,
            // lekin ilova yiqilmasligi kerak.
            false
        }
}
