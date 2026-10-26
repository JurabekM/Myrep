package uz.mpay.core

import org.json.JSONArray
import org.json.JSONObject
import uz.mpay.core.pqlink.ClientHandshake
import uz.mpay.core.pqlink.ClientSession
import uz.mpay.core.pqlink.DeviceKey
import uz.mpay.core.pqlink.PqLink
import uz.mpay.core.pqlink.ServerIdentity
import java.net.HttpURLConnection
import java.net.URL
import javax.net.ssl.HttpsURLConnection

/** Server xatosi (`{"error": {...}}` yoki muhrlangan konvert). */
class ApiException(val status: Int, val code: String, message: String) : Exception("$status $code: $message")

/** ID&V natijasi. */
data class Idv(val decision: String, val score: Int, val reasons: List<String>)

sealed class ProvisionResult {
    class Active(val profile: CardProfile, val idv: Idv) : ProvisionResult()
    class PendingIdv(val tokenId: String, val challengeId: String, val idv: Idv) : ProvisionResult()
    class Declined(val idv: Idv) : ProvisionResult()
}

/** Terminal avtorizatsiyasi natijasi. */
data class AuthResult(
    val approved: Boolean,
    val responseCode: String,
    val reason: String,
    val rrn: String,
    val dpanMasked: String,
    val amountMinor: Long,
    val issuerAuthData: String?,
    val riskScore: Int?,
)

/**
 * `mpay-server` HTTP client (`docs/specs/api.md`). Platformadan mustaqil: Android'da ham, JVM
 * testlarida ham ishlaydi. Qurilma endpointlari PQ Link bilan muhrlanadi.
 */
class MpayClient(
    baseUrl: String,
    private val timeoutMs: Int = 20_000,
    /** HTTPS: server pini va ixtiyoriy mTLS ([TlsConfig]); `null` — oddiy HTTP (faqat sandbox). */
    private val tls: TlsConfig? = null,
) {
    private val base = baseUrl.trimEnd('/')
    private var session: ClientSession? = null

    private class Resp(val status: Int, val contentType: String?, val body: ByteArray)

    private fun request(method: String, path: String, body: ByteArray?, contentType: String?, bearer: String? = null): Resp {
        val c = URL(base + path).openConnection() as HttpURLConnection
        if (c is HttpsURLConnection && tls != null) {
            c.sslSocketFactory = tls.socketFactory
            c.hostnameVerifier = tls.hostnameVerifier
        }
        try {
            c.requestMethod = method
            c.connectTimeout = timeoutMs
            c.readTimeout = timeoutMs
            bearer?.let { c.setRequestProperty("Authorization", "Bearer $it") }
            if (body != null) {
                c.doOutput = true
                c.setRequestProperty("Content-Type", contentType)
                c.outputStream.use { it.write(body) }
            }
            val status = c.responseCode
            val stream = if (status >= 400) c.errorStream else c.inputStream
            val bytes = stream?.use { it.readBytes() } ?: ByteArray(0)
            return Resp(status, c.contentType, bytes)
        } finally {
            c.disconnect()
        }
    }

    private fun plainError(r: Resp): ApiException = try {
        val e = JSONObject(String(r.body, Charsets.UTF_8)).getJSONObject("error")
        ApiException(r.status, e.getString("code"), e.getString("message"))
    } catch (x: Exception) {
        ApiException(r.status, "HTTP", String(r.body, Charsets.UTF_8))
    }

    private fun json(method: String, path: String, body: JSONObject?, bearer: String?): JSONObject {
        val r = request(method, path, body?.toString()?.toByteArray(Charsets.UTF_8), "application/json", bearer)
        if (r.status !in 200..299) throw plainError(r)
        return JSONObject(String(r.body, Charsets.UTF_8))
    }

    /**
     * Identifikator + e'lon qilingan keyingisi (P1.6). `nextEndorsed` — joriy identifikator tasdiqlagan
     * (bunga faqat joriysi pin bo'yicha qabul qilingandan keyin tayaniladi).
     */
    class IdentityInfo(
        val identity: ServerIdentity,
        val fingerprint: String,
        val next: ServerIdentity?,
        val nextEndorsed: Boolean,
    )

    fun identityInfo(): IdentityInfo {
        val j = json("GET", "/v1/pqlink/identity", null, null)
        val id = ServerIdentity(Hex.decode(j.getString("ed25519")), Hex.decode(j.getString("mldsa65")))
        val fp = j.getString("fingerprint")
        if (!Hex.encode(id.fingerprint()).equals(fp, ignoreCase = true)) throw ApiException(0, "FINGERPRINT", "barmoq izi mos emas")
        val n = j.optJSONObject("next") ?: return IdentityInfo(id, fp, null, false)
        val next = ServerIdentity(Hex.decode(n.getString("ed25519")), Hex.decode(n.getString("mldsa65")))
        val endorsed = Hex.encode(next.fingerprint()).equals(n.getString("fingerprint"), ignoreCase = true) &&
            id.verifyEndorsement(next.fingerprint(), Hex.decode(n.getString("endorsement_ed25519")), Hex.decode(n.getString("endorsement_mldsa65")))
        return IdentityInfo(id, fp, next, endorsed)
    }

    /** Server identifikatori va barmoq izi (hex). Sandbox'da TOFU; production'da pinlanadi. */
    fun identity(): Pair<ServerIdentity, String> {
        val j = json("GET", "/v1/pqlink/identity", null, null)
        val id = ServerIdentity(Hex.decode(j.getString("ed25519")), Hex.decode(j.getString("mldsa65")))
        val fp = j.getString("fingerprint")
        if (!Hex.encode(id.fingerprint()).equals(fp, ignoreCase = true)) throw ApiException(0, "FINGERPRINT", "barmoq izi mos emas")
        return id to fp
    }

    private fun pq(path: String, body: ByteArray): ByteArray {
        val r = request("POST", path, body, PqLink.CONTENT_TYPE)
        if (r.status != 200 || r.contentType?.startsWith(PqLink.CONTENT_TYPE) != true) throw plainError(r)
        return r.body
    }

    /** Bekor qilish ro'yxati JSON (ADR-0014); server sozlamagan bo'lsa `null`. Tekshiruv — [Revocations.verify]. */
    fun revocationsJson(): String? {
        val r = request("GET", "/v1/pqlink/revocations", null, null)
        if (r.status == 404) return null
        if (r.status !in 200..299) throw plainError(r)
        return String(r.body, Charsets.UTF_8)
    }

    /**
     * Qurilma kalitini almashtirish (ADR-0015): `newKey` — [enrollNonce] bilan yaratilgan kalit. U
     * `"MPAY-PQLINK-V1 device-rekey" ‖ session_id ‖ eski device_id` ni imzolaydi. Muvaffaqiyatda sessiya
     * yopiladi — yangi kalit bilan qayta [connect] qiling. Qaytaradi: yangi device_id (hex).
     */
    fun rekey(newKey: DeviceKey): String {
        val s = session ?: throw ApiException(0, "NOT_CONNECTED", "PQ Link sessiyasi yo'q")
        val msg = "MPAY-PQLINK-V1 device-rekey".toByteArray(Charsets.US_ASCII) + s.sessionId + s.deviceId
        val req = JSONObject()
            .put("cert_chain", JSONArray(newKey.certChain().map(Hex::encode)))
            .put("signature", Hex.encode(newKey.sign(msg)))
        val d = sealed("/v1/devices/rekey", req)
        session = null
        return d.getString("device_id")
    }

    /** Yangi qurilma uchun bir martalik nonce (P1.7): qurilma kaliti `attestationChallenge = nonce` bilan. */
    fun enrollNonce(): ByteArray = Hex.decode(json("POST", "/v1/pqlink/enroll", JSONObject(), null).getString("nonce"))

    /** PQ Link handshake. */
    fun connect(pinned: ServerIdentity, device: DeviceKey): ClientSession {
        val hs = ClientHandshake.start(pinned)
        val sh = pq("/v1/pqlink/hello", hs.clientHello)
        val (pending, cf) = hs.onServerHello(sh, device)
        val s = pending.onAccept(pq("/v1/pqlink/finish", cf))
        session = s
        return s
    }

    val connected: Boolean get() = session != null

    private fun sealed(path: String, payload: JSONObject): JSONObject {
        val s = session ?: throw ApiException(0, "NOT_CONNECTED", "PQ Link sessiyasi yo'q")
        val r = request("POST", path, s.seal(payload.toString().toByteArray(Charsets.UTF_8)), PqLink.CONTENT_TYPE)
        if (r.contentType?.startsWith(PqLink.CONTENT_TYPE) != true) {
            val e = plainError(r)
            if (e.code == "PQLINK_SESSION") session = null
            throw e
        }
        val env = JSONObject(String(s.open(r.body), Charsets.UTF_8))
        if (env.optBoolean("ok")) return env.getJSONObject("data")
        val e = env.getJSONObject("error")
        throw ApiException(r.status, e.getString("code"), e.getString("message"))
    }

    private fun idv(j: JSONObject) = Idv(
        j.getString("decision"),
        j.getInt("score"),
        j.getJSONArray("reasons").let { a -> List(a.length()) { a.getString(it) } },
    )

    private fun luks(a: JSONArray): MutableList<CardLuk> = MutableList(a.length()) { i ->
        val l = a.getJSONObject(i)
        CardLuk(l.getLong("seq"), Hex.decode(l.getString("key")), l.getLong("expires_at"), l.getInt("max_uses"))
    }

    private fun profile(d: JSONObject) = CardProfile(
        tokenId = d.getString("token_id"),
        dpan = d.getString("dpan"),
        expiryYymm = d.getString("dpan_expiry"),
        psn = d.getInt("psn"),
        luks = luks(d.getJSONArray("luks")),
        atc = 0,
    )

    fun provision(pan: String, expiryYymm: String): ProvisionResult {
        val d = sealed("/v1/tokens", JSONObject().put("pan", pan).put("expiry", expiryYymm))
        return when (d.getString("status")) {
            "ACTIVE" -> ProvisionResult.Active(profile(d), idv(d.getJSONObject("idv")))
            "PENDING_IDV" -> ProvisionResult.PendingIdv(d.getString("token_id"), d.getString("challenge_id"), idv(d.getJSONObject("idv")))
            else -> ProvisionResult.Declined(idv(d.getJSONObject("idv")))
        }
    }

    fun verifyOtp(tokenId: String, challengeId: String, otp: String): CardProfile =
        profile(sealed("/v1/tokens/$tokenId/idv/verify", JSONObject().put("challenge_id", challengeId).put("otp", otp)))

    fun replenish(tokenId: String): List<CardLuk> = luks(sealed("/v1/tokens/$tokenId/luks", JSONObject()).getJSONArray("luks"))

    /** Sandbox: OTP'ni operator kaliti bilan oladi (haqiqiy tizimda SMS/push). */
    fun sandboxOtp(challengeId: String, operatorKey: String): String =
        json("GET", "/v1/sandbox/otp/$challengeId", null, operatorKey).getString("otp")

    /** Terminal diagnostikasi: `(key_id, mtls)` — kalit, mTLS va chegaralardan o'tganini tasdiqlaydi. */
    fun terminalPing(terminalKey: String): Pair<String, Boolean> {
        val j = json("GET", "/v1/terminal/ping", null, terminalKey)
        return j.getString("key_id") to j.getBoolean("mtls")
    }

    /** Terminal: tap natijasini avtorizatsiyaga yuboradi. */
    fun authorize(terminalKey: String, terminalId: String, merchantId: String, stan: Int, iccHex: String): AuthResult {
        val j = json(
            "POST", "/v1/authorizations",
            JSONObject().put("terminal_id", terminalId).put("merchant_id", merchantId).put("stan", stan).put("icc_data", iccHex),
            terminalKey,
        )
        return AuthResult(
            approved = j.getBoolean("approved"),
            responseCode = j.getString("response_code"),
            reason = j.getString("reason"),
            rrn = j.getString("rrn"),
            dpanMasked = j.getString("dpan_masked"),
            amountMinor = j.getLong("amount_minor"),
            issuerAuthData = if (j.isNull("issuer_auth_data")) null else j.getString("issuer_auth_data"),
            riskScore = if (j.isNull("risk_score")) null else j.getInt("risk_score"),
        )
    }
}
