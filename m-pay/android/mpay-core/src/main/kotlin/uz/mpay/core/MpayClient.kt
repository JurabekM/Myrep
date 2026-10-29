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
    /** `otpSentTo` — OTP SMS yuborilgan telefon (maskalangan); sandbox kanalida yoki yuborilmasa `null`. */
    class PendingIdv(val tokenId: String, val challengeId: String, val idv: Idv, val otpSentTo: String? = null) : ProvisionResult()
    class Declined(val idv: Idv) : ProvisionResult()
}

/** `POST /v1/tokens/{id}/luks` javobi. */
class LukBatch(val luks: List<CardLuk>, val cvmLimitMinor: Long?)

/** Token muddatini yangilash natijasi: `renewed = false` — hali erta yoki uzaytirib bo'lmaydi. */
class RenewResult(val renewed: Boolean, val expiryYymm: String, val renewAfter: Long?)

/**
 * Hamyondagi karta (ADR-0030): faqat maskalangan PAN'lar. `state`: `ACTIVE`, `SUSPENDED`, `PENDING_IDV`,
 * `DELETED`; `suspendedBy`: `DEVICE` (foydalanuvchi o'zi) yoki `BANK` (faqat bank qayta yoqadi).
 */
data class WalletToken(
    val tokenId: String,
    val state: String,
    val dpanMasked: String,
    val fpanMasked: String,
    val dpanExpiry: String,
    val createdAt: Long,
    val updatedAt: Long,
    val suspendedBy: String?,
)

/** Karta bo'yicha tranzaksiya (PAN yo'q). `status`: `APPROVED`, `REVERSED`, `DECLINED`. */
data class Txn(
    val id: String,
    val at: Long,
    val amountMinor: Long,
    val currency: Int,
    val merchantId: String,
    val terminalId: String,
    val rrn: String,
    val status: String,
    val responseCode: String,
    val reason: String,
    val cleared: Boolean,
)

/** Tarix sahifasi; `nextCursor == null` — oxirgi sahifa. */
data class TxnPage(val transactions: List<Txn>, val nextCursor: String?)

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
        cvmLimitMinor = d.optLong("cvm_limit_minor", DEFAULT_CVM_LIMIT_MINOR),
        renewAfter = renewAfter(d),
    )

    private fun renewAfter(d: JSONObject): Long? = if (d.has("renew_after")) d.getLong("renew_after") else null

    /** P2.6: provisioning `requestHash` — joriy PQ Link sessiyasiga bog'langan ([Integrity]). */
    fun integrityRequestHash(): String {
        val s = session ?: throw ApiException(0, "NOT_CONNECTED", "PQ Link sessiyasi yo'q")
        return Integrity.requestHash(Integrity.PURPOSE_PROVISION, s.sessionId)
    }

    /** `integrityToken` — Play Integrity (sandbox: mock) tokeni, [integrityRequestHash] uchun olingan. */
    fun provision(pan: String, expiryYymm: String, integrityToken: String? = null): ProvisionResult {
        val body = JSONObject().put("pan", pan).put("expiry", expiryYymm)
        if (integrityToken != null) body.put("integrity_token", integrityToken)
        val d = sealed("/v1/tokens", body)
        return when (d.getString("status")) {
            "ACTIVE" -> ProvisionResult.Active(profile(d), idv(d.getJSONObject("idv")))
            "PENDING_IDV" -> ProvisionResult.PendingIdv(
                d.getString("token_id"),
                d.getString("challenge_id"),
                idv(d.getJSONObject("idv")),
                if (d.has("otp_sent_to")) d.getString("otp_sent_to") else null,
            )
            else -> ProvisionResult.Declined(idv(d.getJSONObject("idv")))
        }
    }

    fun verifyOtp(tokenId: String, challengeId: String, otp: String): CardProfile =
        profile(sealed("/v1/tokens/$tokenId/idv/verify", JSONObject().put("challenge_id", challengeId).put("otp", otp)))

    /** OTP SMS'ni qayta yuborish (2-faza P2.1); qaytaradi: maskalangan telefon. Chegara — 3 marta (`429 OTP_RESEND_LIMIT`). */
    fun resendOtp(tokenId: String, challengeId: String): String =
        sealed("/v1/tokens/$tokenId/idv/resend", JSONObject().put("challenge_id", challengeId)).getString("otp_sent_to")

    fun replenish(tokenId: String): List<CardLuk> = replenishBatch(tokenId).luks

    /** LUK to'ldirish + joriy CVM chegarasi (bank siyosatni o'zgartirsa qurilma yangilaydi; ADR-0022). */
    fun replenishBatch(tokenId: String): LukBatch {
        val d = sealed("/v1/tokens/$tokenId/luks", JSONObject())
        return LukBatch(luks(d.getJSONArray("luks")), if (d.has("cvm_limit_minor")) d.getLong("cvm_limit_minor") else null)
    }

    /** Token muddatini yangilash (`renew_after` dan keyin; takroriy chaqiruv xavfsiz; ADR-0022). */
    fun renew(tokenId: String): RenewResult {
        val d = sealed("/v1/tokens/$tokenId/renew", JSONObject())
        return RenewResult(d.getBoolean("renewed"), d.getString("dpan_expiry"), renewAfter(d))
    }

    // ------------------------------------------------------------ hamyon (ADR-0030)

    private fun walletToken(d: JSONObject) = WalletToken(
        tokenId = d.getString("token_id"),
        state = d.getString("state"),
        dpanMasked = d.getString("dpan_masked"),
        fpanMasked = d.getString("fpan_masked"),
        dpanExpiry = d.getString("dpan_expiry"),
        createdAt = d.getLong("created_at"),
        updatedAt = d.getLong("updated_at"),
        suspendedBy = if (d.isNull("suspended_by")) null else d.optString("suspended_by", null),
    )

    /** Shu qurilmaning serverdagi kartalari (o'chirilganlarsiz). */
    fun walletTokens(): List<WalletToken> {
        val a = sealed("/v1/wallet/tokens", JSONObject()).getJSONArray("tokens")
        return List(a.length()) { walletToken(a.getJSONObject(it)) }
    }

    /**
     * Kartani o'zi boshqarish: `action` — `suspend`, `resume` yoki `delete`. Bank to'xtatgan kartani
     * yoqish — `SUSPENDED_BY_BANK` (403).
     */
    fun walletSetState(tokenId: String, action: String): WalletToken {
        require(action in setOf("suspend", "resume", "delete")) { "action: $action" }
        return walletToken(sealed("/v1/wallet/tokens/$tokenId/$action", JSONObject()))
    }

    /** Karta tarixi, yangilari birinchi; `cursor` — oldingi sahifaning [TxnPage.nextCursor]. */
    fun transactions(tokenId: String, cursor: String? = null, limit: Int? = null): TxnPage {
        val body = JSONObject()
        if (cursor != null) body.put("cursor", cursor)
        if (limit != null) body.put("limit", limit)
        val d = sealed("/v1/wallet/tokens/$tokenId/transactions", body)
        val a = d.getJSONArray("transactions")
        val txns = List(a.length()) { i ->
            val t = a.getJSONObject(i)
            Txn(
                id = t.getString("id"),
                at = t.getLong("at"),
                amountMinor = t.getLong("amount_minor"),
                currency = t.getInt("currency"),
                merchantId = t.getString("merchant_id"),
                terminalId = t.getString("terminal_id"),
                rrn = t.getString("rrn"),
                status = t.getString("status"),
                responseCode = t.getString("response_code"),
                reason = t.getString("reason"),
                cleared = t.getBoolean("cleared"),
            )
        }
        return TxnPage(txns, if (d.isNull("next_cursor")) null else d.optString("next_cursor", null))
    }

    /**
     * Sandbox: Play Integrity o'rnida mock token (`[integrity] mode = "mock"`, operator kaliti).
     * `preset`: `strong` (standart), `device`, `basic`, `no_integrity`, `unrecognized`,
     * `play_protect_risk`, `remote_control`. Rejim `off` bo'lsa — `null` (404).
     */
    fun sandboxIntegrityToken(requestHash: String, operatorKey: String, preset: String? = null): String? {
        val body = JSONObject().put("request_hash", requestHash)
        if (preset != null) body.put("preset", preset)
        return try {
            json("POST", "/v1/sandbox/integrity-token", body, operatorKey).getString("integrity_token")
        } catch (e: ApiException) {
            if (e.status == 404) null else throw e
        }
    }

    /**
     * Sandbox: mock yaxlitlik tokeni qurilmaning o'z PQ Link sessiyasi orqali — operator kaliti va mTLS
     * kerak emas (TLS sandbox'ida ham ishlaydi). Token shu sessiyaning [integrityRequestHash] i uchun.
     * Rejim `off` bo'lsa — `null` (404).
     */
    fun sandboxDeviceIntegrityToken(preset: String? = null): String? {
        val body = JSONObject().put("request_hash", integrityRequestHash())
        if (preset != null) body.put("preset", preset)
        return try {
            sealed("/v1/sandbox/integrity-token/device", body).getString("integrity_token")
        } catch (e: ApiException) {
            if (e.status == 404 || e.code == "NOT_FOUND") null else throw e
        }
    }

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
