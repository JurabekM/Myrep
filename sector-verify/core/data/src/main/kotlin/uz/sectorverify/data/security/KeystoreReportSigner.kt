package uz.sectorverify.data.security

import android.content.Context
import android.content.pm.PackageManager
import android.os.Build
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

/** Random per-installation id; used as the key attestation challenge (§8.3). Not backed up. */
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
 * §8.3: one EC P-256 Keystore key per installation (StrongBox when present), created with attestation
 * challenge = install UUID. Signs with SHA256withECDSA; the certificate chain goes into report.json.
 */
class KeystoreReportSigner(private val context: Context, private val alias: String = ALIAS) : ReportSigner {
    private val ks: KeyStore = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    private fun key(): PrivateKey {
        (ks.getKey(alias, null) as? PrivateKey)?.let { return it }
        val challenge = InstallId.of(context).get().toByteArray()
        val strongBox = Build.VERSION.SDK_INT >= Build.VERSION_CODES.P &&
            context.packageManager.hasSystemFeature(PackageManager.FEATURE_STRONGBOX_KEYSTORE)
        try {
            generate(challenge, strongBox)
        } catch (expected: StrongBoxUnavailableException) {
            // Advertised StrongBox may still refuse EC keys: fall back to the TEE.
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
