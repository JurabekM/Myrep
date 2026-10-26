package uz.mpay.wallet.sdk

import android.os.Build
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import android.util.Log
import uz.mpay.core.pqlink.DeviceKey
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec

/**
 * Qurilmaning uzoq muddatli P-256 kaliti — Android Keystore'da (iloji bo'lsa StrongBox), Android
 * Key Attestation zanjiri bilan. Kalit qurilmadan chiqmaydi; server zanjirni Google ildizlarigacha
 * tekshiradi (`mpay-pqlink::attestation`). ML-KEM kalitlari bu yerda emas — ular efemer (PQ Link).
 */
class AndroidDeviceKey private constructor(private val alias: String, val strongBox: Boolean) : DeviceKey {

    companion object {
        private const val TAG = "MpayDeviceKey"
        const val DEFAULT_ALIAS = "mpay-device-p256"

        /** Mavjud kalitni ochadi yoki yangisini yaratadi. `challenge` — attestatsiya challenge'i. */
        fun getOrCreate(challenge: ByteArray, alias: String = DEFAULT_ALIAS): AndroidDeviceKey {
            val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
            if (ks.containsAlias(alias)) {
                val sb = runCatching {
                    val info = java.security.KeyFactory.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore")
                        .getKeySpec(ks.getKey(alias, null) as PrivateKey, android.security.keystore.KeyInfo::class.java)
                    Build.VERSION.SDK_INT >= 31 && info.securityLevel == KeyProperties.SECURITY_LEVEL_STRONGBOX
                }.getOrDefault(false)
                return AndroidDeviceKey(alias, sb)
            }
            return try {
                generate(alias, challenge, strongBox = true)
            } catch (e: StrongBoxUnavailableException) {
                Log.w(TAG, "StrongBox yo'q — TEE kaliti (server siyosati rad etishi mumkin)")
                generate(alias, challenge, strongBox = false)
            }
        }

        private fun generate(alias: String, challenge: ByteArray, strongBox: Boolean): AndroidDeviceKey {
            val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN)
                .setAlgorithmParameterSpec(ECGenParameterSpec("secp256r1"))
                .setDigests(KeyProperties.DIGEST_SHA256)
                .setAttestationChallenge(challenge)
                .apply { if (Build.VERSION.SDK_INT >= 28) setIsStrongBoxBacked(strongBox) }
                .build()
            KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, "AndroidKeyStore").apply { initialize(spec) }.generateKeyPair()
            return AndroidDeviceKey(alias, strongBox)
        }

        fun exists(alias: String = DEFAULT_ALIAS): Boolean =
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.containsAlias(alias)

        fun delete(alias: String = DEFAULT_ALIAS) {
            KeyStore.getInstance("AndroidKeyStore").apply { load(null) }.deleteEntry(alias)
        }
    }

    override fun certChain(): List<ByteArray> {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return ks.getCertificateChain(alias).map { it.encoded }
    }

    override fun sign(message: ByteArray): ByteArray {
        val ks = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        return Signature.getInstance("SHA256withECDSA").run {
            initSign(ks.getKey(alias, null) as PrivateKey)
            update(message)
            sign()
        }
    }

    /** Attestatsiya zanjiri PEM ko'rinishida (sandbox: ildizni server konfiguratsiyasiga qo'shish uchun). */
    fun chainPem(): String = certChain().joinToString("") {
        "-----BEGIN CERTIFICATE-----\n" + android.util.Base64.encodeToString(it, android.util.Base64.DEFAULT) + "-----END CERTIFICATE-----\n"
    }
}
