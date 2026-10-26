package uz.sectorverify.format

import java.io.ByteArrayInputStream
import java.security.Signature
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.util.Base64
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import kotlinx.serialization.json.put

/** Kanonik baytlarni imzolaydi; Android'da Android Keystore EC P-256 kalitiga tayanadi. */
interface ReportSigner {
    fun sign(data: ByteArray): ByteArray

    /** DER-kodlangan sertifikatlar, avval leaf (mavjud bo'lsa attestation zanjiri). */
    fun certificateChain(): List<ByteArray>
}

/**
 * [keyFingerprint]: imzolovchi ochiq kalitning SHA-256'i (hex). Imzo hisobot shu kalit bilan imzolangandan keyin
 * o'zgartirilmaganini isbotlaydi; kalit ma'lum telefonga tegishliligi fingerprint'larni solishtirib tekshiriladi (attestation
 * zanjiri hisobotda saqlanadi, lekin v1.0 da Google root'iga nisbatan tekshirilmaydi).
 */
data class VerifyResult(
    val hashOk: Boolean,
    val signatureOk: Boolean,
    val chainLength: Int,
    val message: String,
    val keyFingerprint: String? = null,
) {
    val ok: Boolean get() = hashOk && signatureOk
}

/** §8.3: `integrity`siz kanonik hisobot ustidan sha256 + SHA256withECDSA. */
object ReportIntegrity {
    private val b64 = Base64.getEncoder()

    fun seal(report: JsonObject, signer: ReportSigner): JsonObject {
        val bytes = CanonicalJson.bytes(ReportJson.withoutIntegrity(report))
        val integrity = buildJsonObject {
            put("sha256", CanonicalJson.sha256Hex(bytes))
            put("signature", b64.encodeToString(signer.sign(bytes)))
            put("keyAlg", ReportJson.KEY_ALG)
            put("attestationChain", JsonArray(signer.certificateChain().map { JsonPrimitive(b64.encodeToString(it)) }))
        }
        return JsonObject(ReportJson.withoutIntegrity(report) + (ReportJson.INTEGRITY to integrity))
    }

    @Suppress("ReturnCount")
    fun verify(reportText: String): VerifyResult {
        val report = runCatching {
            ReportJson.parse(reportText)
        }.getOrElse { return VerifyResult(false, false, 0, "report.json o'qilmadi: ${it.message}") }
        val integrity = report[ReportJson.INTEGRITY]?.jsonObject ?: return VerifyResult(false, false, 0, "integrity bloki yo'q")
        val bytes = CanonicalJson.bytes(ReportJson.withoutIntegrity(report))
        val hashOk = integrity["sha256"]?.jsonPrimitive?.content == CanonicalJson.sha256Hex(bytes)
        val chain = integrity["attestationChain"]?.jsonArray?.map { Base64.getDecoder().decode(it.jsonPrimitive.content) }.orEmpty()
        if (chain.isEmpty()) return VerifyResult(hashOk, false, 0, "sertifikat zanjiri yo'q")
        val cert = runCatching {
            CertificateFactory.getInstance("X.509").generateCertificate(ByteArrayInputStream(chain.first())) as X509Certificate
        }.getOrNull()
        val sigOk = cert != null &&
            runCatching {
                Signature.getInstance("SHA256withECDSA").run {
                    initVerify(cert.publicKey)
                    update(bytes)
                    verify(Base64.getDecoder().decode(integrity["signature"]!!.jsonPrimitive.content))
                }
            }.getOrDefault(false)
        val fingerprint = cert?.let { CanonicalJson.sha256Hex(it.publicKey.encoded) }
        val msg = when {
            hashOk && sigOk -> "imzo va xesh to'g'ri"
            !hashOk -> "xesh mos emas: hisobot o'zgartirilgan"
            else -> "imzo noto'g'ri"
        }
        return VerifyResult(hashOk, sigOk, chain.size, msg, fingerprint)
    }
}
