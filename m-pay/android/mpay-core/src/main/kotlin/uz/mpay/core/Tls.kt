package uz.mpay.core

import org.json.JSONObject
import java.security.KeyFactory
import java.security.KeyStore
import java.security.MessageDigest
import java.security.PrivateKey
import java.security.cert.CertificateException
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.spec.PKCS8EncodedKeySpec
import java.util.Base64
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.KeyManagerFactory
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509KeyManager
import javax.net.ssl.X509TrustManager

/**
 * HTTPS sozlamasi (1-faza, P1.4): server sertifikati SHA-256 bo'yicha **pinlanadi** (tizim CA'lariga
 * ishonilmaydi) va ixtiyoriy mTLS mijoz kaliti ko'rsatiladi (ADR-0011).
 *
 * Pin aniq sertifikatga bog'langani uchun xost nomi tekshiruvi ham pin bilan almashtiriladi:
 * sandbox sertifikati `localhost` uchun chiqarilgan, terminal esa LAN IP orqali ulanadi.
 */
class TlsConfig(serverCertSha256: ByteArray, private val keyManager: X509KeyManager? = null) {
    private val pin = serverCertSha256.copyOf()

    init {
        require(pin.size == 32) { "server sertifikati pini SHA-256 (32 bayt) bo'lishi kerak" }
    }

    private fun matches(cert: java.security.cert.Certificate?): Boolean =
        cert != null && MessageDigest.isEqual(Pem.sha256(cert.encoded), pin)

    private val trustManager = object : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) =
            throw CertificateException("mijoz sertifikatlari qabul qilinmaydi")

        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            if (!matches(chain?.firstOrNull())) throw CertificateException("server sertifikati pinga mos emas")
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }

    val socketFactory: SSLSocketFactory by lazy {
        SSLContext.getInstance("TLS").apply {
            init(keyManager?.let { arrayOf(it) }, arrayOf(trustManager), null)
        }.socketFactory
    }

    val hostnameVerifier = HostnameVerifier { _, session ->
        runCatching { matches(session.peerCertificates.firstOrNull()) }.getOrDefault(false)
    }
}

/** PEM yordamchilari (JVM va Android). */
object Pem {
    fun sha256(der: ByteArray): ByteArray = MessageDigest.getInstance("SHA-256").digest(der)

    private fun blocks(pem: String, label: String): List<ByteArray> =
        Regex("-----BEGIN $label-----([A-Za-z0-9+/=\\s]+)-----END $label-----")
            .findAll(pem)
            .map { Base64.getMimeDecoder().decode(it.groupValues[1]) }
            .toList()

    fun certificates(pem: String): List<X509Certificate> {
        val cf = CertificateFactory.getInstance("X.509")
        return blocks(pem, "CERTIFICATE").map { cf.generateCertificate(it.inputStream()) as X509Certificate }
    }

    /** PKCS#8 `PRIVATE KEY` (EC yoki RSA). */
    fun privateKey(pem: String): PrivateKey {
        val der = blocks(pem, "PRIVATE KEY").singleOrNull() ?: throw IllegalArgumentException("PKCS#8 kalit topilmadi")
        val spec = PKCS8EncodedKeySpec(der)
        return runCatching { KeyFactory.getInstance("EC").generatePrivate(spec) }
            .getOrElse { KeyFactory.getInstance("RSA").generatePrivate(spec) }
    }

    /** PEM sertifikat + kalitdan mTLS key manager (JVM; Android'da kalit Keystore'da saqlanadi). */
    fun keyManager(certPem: String, keyPem: String): X509KeyManager {
        val password = CharArray(0)
        val ks = KeyStore.getInstance("PKCS12").apply {
            load(null, null)
            setKeyEntry("client", privateKey(keyPem), password, certificates(certPem).toTypedArray())
        }
        val kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm()).apply { init(ks, password) }
        return kmf.keyManagers.filterIsInstance<X509KeyManager>().first()
    }
}

/**
 * `mpay-server terminal-bundle` paketi (`mpay-terminal-bundle/1`). Ichida sirlar bor: import qilingach
 * mijoz kaliti va terminal kaliti xavfsiz saqlanadi, fayl o'chiriladi.
 */
class TerminalBundle(
    val serverUrl: String,
    val serverCertSha256: ByteArray,
    val keyId: String,
    val clientCertPem: String,
    val clientKeyPem: String,
    val terminalKey: String,
) {
    companion object {
        const val FORMAT = "mpay-terminal-bundle/1"

        fun parse(json: String): TerminalBundle {
            val j = JSONObject(json)
            require(j.optString("format") == FORMAT) { "noma'lum paket formati" }
            val url = j.getString("server_url")
            require(url.startsWith("https://")) { "paket faqat https:// uchun" }
            val pin = Hex.decode(j.getString("server_cert_sha256"))
            // Pin paketdagi sertifikatga mos kelishi shart (buzilgan paketni rad etish).
            val cert = Pem.certificates(j.getString("server_cert_pem")).firstOrNull()
                ?: throw IllegalArgumentException("server sertifikati yo'q")
            require(MessageDigest.isEqual(Pem.sha256(cert.encoded), pin)) { "server pini sertifikatga mos emas" }
            return TerminalBundle(
                serverUrl = url,
                serverCertSha256 = pin,
                keyId = j.getString("key_id"),
                clientCertPem = j.getString("client_cert_pem"),
                clientKeyPem = j.getString("client_key_pem"),
                terminalKey = j.getString("terminal_key"),
            )
        }
    }
}
