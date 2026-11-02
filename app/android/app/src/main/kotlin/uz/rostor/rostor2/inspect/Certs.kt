package uz.rostor.rostor2.inspect

import android.content.pm.PackageInfo
import android.content.pm.PackageManager
import android.os.Build
import uz.rostor.rostor2.crypto.Hybrid
import uz.rostor.rostor2.crypto.toHex
import java.io.ByteArrayInputStream
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate

/** Imzo sertifikatlari bilan ishlash: SHA-256 izi (Android tooling bilan mos — ROSTOR-1 §16). */
object Certs {
    fun sha256Hex(encoded: ByteArray): String = Hybrid.sha256(encoded).toHex()

    fun describe(cert: X509Certificate): Map<String, Any?> {
        val subject = cert.subjectX500Principal.name
        return mapOf(
            "sha256" to sha256Hex(cert.encoded),
            "subject" to subject,
            "issuer" to cert.issuerX500Principal.name,
            "notBefore" to cert.notBefore.time,
            "notAfter" to cert.notAfter.time,
            "debug" to subject.contains("CN=Android Debug"),
        )
    }

    fun parse(encoded: ByteArray): X509Certificate? = try {
        CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(encoded)) as X509Certificate
    } catch (e: Exception) {
        null
    }

    fun signatureFlag(): Int =
        if (Build.VERSION.SDK_INT >= 28) PackageManager.GET_SIGNING_CERTIFICATES
        else @Suppress("DEPRECATION") PackageManager.GET_SIGNATURES

    /** O'rnatilgan paketning joriy imzolovchilari va (v3 rotatsiyasida) avvalgi sertifikatlar tarixi. */
    fun ofInstalled(pi: PackageInfo): Pair<List<ByteArray>, List<ByteArray>> {
        if (Build.VERSION.SDK_INT >= 28) {
            val si = pi.signingInfo ?: return emptyList<ByteArray>() to emptyList()
            return if (si.hasMultipleSigners()) {
                si.apkContentsSigners.map { it.toByteArray() } to emptyList()
            } else {
                val history = si.signingCertificateHistory?.map { it.toByteArray() } ?: emptyList()
                // Tarixning oxirgisi — joriy sertifikat.
                listOfNotNull(history.lastOrNull()) to history
            }
        }
        @Suppress("DEPRECATION")
        val sigs = pi.signatures?.map { it.toByteArray() } ?: emptyList()
        return sigs to emptyList()
    }
}
