package uz.sectorverify.data.security

import android.content.Context
import android.content.pm.PackageManager
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.StrongBoxUnavailableException
import java.io.File
import java.security.KeyPairGenerator
import java.security.KeyStore
import java.security.PrivateKey
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.UUID
import uz.sectorverify.format.ReportSigner

/** Har o'rnatish uchun tasodifiy id; kalit attestation challenge'i sifatida ishlatiladi (§8.3). Zaxiralanmaydi. */
class InstallId(private val file: File) {
    @Synchronized
    fun get(): String {
        if (file.exists()) return file.readText().trim()
        val id = UUID.randomUUID().toString()
        file.parentFile?.mkdirs()
        file.writeText(id)
        return id
    }

    companion object {
        const val FILE_NAME = "install.id"

        fun of(context: Context) = InstallId(File(context.noBackupFilesDir, FILE_NAME))
    }
}

/**
 * §8.3: har o'rnatishga bitta EC P-256 Keystore kaliti (StrongBox bo'lsa, unda), attestation
 * challenge = o'rnatish UUID bilan yaratiladi. SHA256withECDSA bilan imzolaydi; sertifikat zanjiri report.json ga yoziladi.
 */
class KeystoreReportSigner(private val context: Context, private val alias: String = ALIAS) : ReportSigner {
    private val ks: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun key(): PrivateKey {
        (ks.getKey(alias, null) as? PrivateKey)?.let { return it }
        val challenge = InstallId.of(context).get().toByteArray()
        val strongBox = context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        try {
            generate(challenge, strongBox)
        } catch (expected: StrongBoxUnavailableException) {
            // E'lon qilingan StrongBox baribir EC kalitni rad etishi mumkin: TEE'ga qaytamiz.
            generate(challenge, false)
        }
        return ks.getKey(alias, null) as PrivateKey
    }

    private fun generate(challenge: ByteArray, strongBox: Boolean) {
        val spec = KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_SIGN or KeyProperties.PURPOSE_VERIFY)
            .setAlgorithmParameterSpec(ECGenParameterSpec(CURVE))
            .setDigests(KeyProperties.DIGEST_SHA256)
            .setAttestationChallenge(challenge)
            .setIsStrongBoxBacked(strongBox)
            .build()
        KeyPairGenerator.getInstance(KeyProperties.KEY_ALGORITHM_EC, ANDROID_KEYSTORE).run {
            initialize(spec)
            generateKeyPair()
        }
    }

    override fun sign(data: ByteArray): ByteArray = Signature.getInstance(ALGORITHM).run {
        initSign(key())
        update(data)
        sign()
    }

    override fun certificateChain(): List<ByteArray> {
        key()
        return ks.getCertificateChain(alias).orEmpty().map { it.encoded }
    }

    companion object {
        const val ALIAS = "sv_report_key"
        private const val ANDROID_KEYSTORE = "AndroidKeyStore"
        private const val CURVE = "secp256r1"
        private const val ALGORITHM = "SHA256withECDSA"
    }
}
