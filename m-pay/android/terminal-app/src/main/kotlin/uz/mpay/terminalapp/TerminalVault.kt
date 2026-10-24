package uz.mpay.terminalapp

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.security.keystore.KeyProtection
import android.util.Base64
import uz.mpay.core.Hex
import uz.mpay.core.Pem
import uz.mpay.core.TerminalBundle
import uz.mpay.core.TlsConfig
import java.net.Socket
import java.security.KeyStore
import java.security.Principal
import java.security.PrivateKey
import java.security.cert.X509Certificate
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import javax.net.ssl.SSLEngine
import javax.net.ssl.X509ExtendedKeyManager

/**
 * Terminal sirlari (1-faza, P1.4):
 * * mTLS mijoz kaliti — Android Keystore'ga import qilinadi (ilovaga qaytib chiqmaydi, imzo Keystore'da);
 * * terminal API kaliti, server manzili va pin — Keystore AES-256-GCM kaliti bilan shifrlangan.
 * Paket fayli import qilingach o'chiriladi.
 */
class TerminalVault(context: Context) {
    private val prefs = context.applicationContext.getSharedPreferences("terminal-vault", Context.MODE_PRIVATE)
    private val ks = KeyStore.getInstance(ANDROID_KEYSTORE).apply { load(null) }

    /** Import qilingan sozlama (shifrlangan qiymatlar ochilgan). */
    class Profile(val serverUrl: String, val keyId: String, val terminalKey: String, val tls: TlsConfig)

    val imported: Boolean get() = prefs.contains(P_SECRET) && ks.containsAlias(MTLS_ALIAS)

    fun import(json: String): Profile {
        val b = TerminalBundle.parse(json)
        val chain = Pem.certificates(b.clientCertPem)
        require(chain.isNotEmpty()) { "mijoz sertifikati yo'q" }
        val key = Pem.privateKey(b.clientKeyPem)
        ks.setEntry(
            MTLS_ALIAS,
            KeyStore.PrivateKeyEntry(key, chain.toTypedArray()),
            KeyProtection.Builder(KeyProperties.PURPOSE_SIGN)
                .setDigests(
                    KeyProperties.DIGEST_NONE, KeyProperties.DIGEST_SHA256,
                    KeyProperties.DIGEST_SHA384, KeyProperties.DIGEST_SHA512,
                )
                .build(),
        )
        val secret = "${b.serverUrl}\n${b.keyId}\n${Hex.encode(b.serverCertSha256)}\n${b.terminalKey}"
        prefs.edit().putString(P_SECRET, encrypt(secret.toByteArray(Charsets.UTF_8))).apply()
        return load()!!
    }

    fun load(): Profile? {
        if (!imported) return null
        val parts = String(decrypt(prefs.getString(P_SECRET, null)!!), Charsets.UTF_8).split('\n')
        if (parts.size != 4) return null
        return Profile(parts[0], parts[1], parts[3], TlsConfig(Hex.decode(parts[2]), KeystoreKeyManager()))
    }

    fun clear() {
        prefs.edit().clear().apply()
        runCatching { ks.deleteEntry(MTLS_ALIAS) }
        runCatching { ks.deleteEntry(AES_ALIAS) }
    }

    private fun aesKey(): SecretKey {
        (ks.getKey(AES_ALIAS, null) as? SecretKey)?.let { return it }
        val g = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, ANDROID_KEYSTORE)
        g.init(
            KeyGenParameterSpec.Builder(AES_ALIAS, KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build(),
        )
        return g.generateKey()
    }

    private fun encrypt(plain: ByteArray): String {
        val c = Cipher.getInstance(AES_GCM).apply { init(Cipher.ENCRYPT_MODE, aesKey()) }
        return Base64.encodeToString(c.iv + c.doFinal(plain), Base64.NO_WRAP)
    }

    private fun decrypt(b64: String): ByteArray {
        val raw = Base64.decode(b64, Base64.NO_WRAP)
        val c = Cipher.getInstance(AES_GCM).apply { init(Cipher.DECRYPT_MODE, aesKey(), GCMParameterSpec(128, raw, 0, 12)) }
        return c.doFinal(raw, 12, raw.size - 12)
    }

    /** mTLS: shaxsiy kalit Keystore'da qoladi, TLS imzosi Keystore orqali. */
    private inner class KeystoreKeyManager : X509ExtendedKeyManager() {
        override fun chooseClientAlias(keyType: Array<out String>?, issuers: Array<out Principal>?, socket: Socket?) = MTLS_ALIAS
        override fun chooseEngineClientAlias(keyType: Array<out String>?, issuers: Array<out Principal>?, engine: SSLEngine?) = MTLS_ALIAS
        override fun getClientAliases(keyType: String?, issuers: Array<out Principal>?) = arrayOf(MTLS_ALIAS)
        override fun getCertificateChain(alias: String?): Array<X509Certificate>? =
            ks.getCertificateChain(MTLS_ALIAS)?.map { it as X509Certificate }?.toTypedArray()
        override fun getPrivateKey(alias: String?): PrivateKey? = ks.getKey(MTLS_ALIAS, null) as? PrivateKey
        override fun getServerAliases(keyType: String?, issuers: Array<out Principal>?): Array<String>? = null
        override fun chooseServerAlias(keyType: String?, issuers: Array<out Principal>?, socket: Socket?): String? = null
    }

    private companion object {
        const val ANDROID_KEYSTORE = "AndroidKeyStore"
        const val MTLS_ALIAS = "mpay-terminal-mtls"
        const val AES_ALIAS = "mpay-terminal-vault"
        const val AES_GCM = "AES/GCM/NoPadding"
        const val P_SECRET = "secret"
    }
}
