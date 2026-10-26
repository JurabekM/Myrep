package uz.mpay.core

import org.bouncycastle.asn1.ASN1ObjectIdentifier
import org.bouncycastle.asn1.x500.X500Name
import org.bouncycastle.asn1.x509.SubjectPublicKeyInfo
import org.bouncycastle.cert.X509v3CertificateBuilder
import org.bouncycastle.cert.jcajce.JcaX509CertificateHolder
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import uz.mpay.core.pqlink.DeviceKey
import java.io.File
import java.math.BigInteger
import java.security.KeyFactory
import java.security.KeyPairGenerator
import java.security.PrivateKey
import java.security.Signature
import java.security.cert.CertificateFactory
import java.security.cert.X509Certificate
import java.security.spec.ECGenParameterSpec
import java.security.spec.PKCS8EncodedKeySpec
import java.util.Base64
import java.util.Date

/**
 * Kotlin ↔ Rust interop: Kotlin PQ Link client, HCE applet va terminal yadrosi haqiqiy
 * `mpay-server` (Rust) bilan. `scripts/android-interop.sh` ishga tushiradi; muhit
 * o'zgaruvchilarisiz o'tkazib yuboriladi.
 */
class InteropTest {
    private val url = System.getenv("MPAY_INTEROP_URL")
    private val sandbox = System.getenv("MPAY_SANDBOX_DIR")?.let(::File)

    /** Sandbox attestatsiya CA bilan imzolangan test qurilma (Android Keystore o'rnida). */
    private class SoftDevice(dir: File, level: Int = 2, challenge: ByteArray = "kotlin-interop".toByteArray()) : DeviceKey {
        private val kp = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        private val chain: List<ByteArray>

        init {
            val pem = File(dir, "sandbox-attestation-ca.key.pem").readText()
            val der = Base64.getMimeDecoder().decode(pem.lines().filter { !it.startsWith("-----") }.joinToString(""))
            val caKey: PrivateKey = KeyFactory.getInstance("EC").generatePrivate(PKCS8EncodedKeySpec(der))
            val caDer = File(dir, "sandbox-attestation-root.der").readBytes()
            val ca = CertificateFactory.getInstance("X.509").generateCertificate(caDer.inputStream()) as X509Certificate
            val kd = Tlv.constructed(
                0x30,
                Tlv.primitive(0x02, byteArrayOf(0x01, 0x2C)), Tlv.primitive(0x0A, byteArrayOf(level.toByte())),
                Tlv.primitive(0x02, byteArrayOf(0x01, 0x2C)), Tlv.primitive(0x0A, byteArrayOf(level.toByte())),
                Tlv.primitive(0x04, challenge), Tlv.primitive(0x04, ByteArray(0)),
                Tlv.constructed(0x30),
                // hardwareEnforced.rootOfTrust [704]: Verified, deviceLocked = true (server buni talab qiladi).
                Tlv.constructed(
                    0x30,
                    Tlv.constructed(
                        0xBF8540,
                        Tlv.constructed(
                            0x30,
                            Tlv.primitive(0x04, ByteArray(32)), Tlv.primitive(0x01, byteArrayOf(0xFF.toByte())),
                            Tlv.primitive(0x0A, byteArrayOf(0)), Tlv.primitive(0x04, ByteArray(32)),
                        ),
                    ),
                ),
            ).encode()
            val now = System.currentTimeMillis()
            val b = X509v3CertificateBuilder(
                JcaX509CertificateHolder(ca).subject, BigInteger.valueOf(now), Date(now - 86_400_000), Date(now + 86_400_000L * 365),
                X500Name("CN=Android Keystore Key"), SubjectPublicKeyInfo.getInstance(kp.public.encoded),
            ).addExtension(ASN1ObjectIdentifier("1.3.6.1.4.1.11129.2.1.17"), false, kd)
            val leaf = b.build(JcaContentSignerBuilder("SHA256withECDSA").build(caKey)).encoded
            chain = listOf(leaf, caDer)
        }

        override fun certChain() = chain
        override fun sign(message: ByteArray): ByteArray =
            Signature.getInstance("SHA256withECDSA").run { initSign(kp.private); update(message); sign() }
    }

    private class Gate(var ok: Boolean = false) : CdcvmGate {
        override fun isVerified() = ok
        override fun consume() { ok = false }
    }

    private fun cred(key: String): String =
        File(sandbox, "dev-credentials.env").readLines().first { it.startsWith("$key=") }.substringAfter("=").trim()

    /** Virtual SMS shlyuzidagi xabarlar matni (`GET /messages?to=`). */
    private fun smsInbox(gw: String, to: String): List<String> {
        val c = java.net.URL("$gw/messages?to=" + java.net.URLEncoder.encode(to, "UTF-8")).openConnection() as java.net.HttpURLConnection
        c.setRequestProperty("Authorization", "Bearer " + System.getenv("MPAY_SMS_TOKEN"))
        val arr = org.json.JSONArray(c.inputStream.bufferedReader().readText())
        return (0 until arr.length()).map { arr.getJSONObject(it).getString("text") }
    }

    private fun demoPan(i: Int): String =
        File(sandbox, "mpay.toml").readLines().filter { it.startsWith("pan = ") }[i].substringAfter("\"").substringBefore("\"")

    @Test
    fun kotlinClientAgainstRustServer() {
        assumeTrue("MPAY_INTEROP_URL o'rnatilmagan — o'tkazib yuborildi", url != null && sandbox != null)
        val dir = sandbox!!
        val api = MpayClient(url!!)
        val (identity, fp) = api.identity()
        println("server fp $fp")

        // 1) PQ Link handshake (Kotlin) → Rust server; provisioning.
        // P1.7: ro'yxatdan o'tmagan qurilma (nonce'siz challenge) — rad.
        try {
            MpayClient(url).connect(identity, SoftDevice(dir))
            throw AssertionError("PQLINK_ENROLLMENT kutilgan")
        } catch (e: ApiException) {
            assertEquals("PQLINK_ENROLLMENT", e.code)
        }
        val s = api.connect(identity, SoftDevice(dir, challenge = api.enrollNonce()))
        println("PQ Link sessiyasi: $s")
        val pan = demoPan(0)
        // 2-faza P2.6: yaxlitlik tokeni majburiy; requestHash Kotlin'da hisoblanadi (Rust bilan bir xil),
        // token — server mock'idan (real ilovada Play Integrity API).
        val op = cred("MPAY_OPERATOR_KEY")
        try {
            api.provision(pan, "3112")
            throw AssertionError("INTEGRITY_REQUIRED kutilgan")
        } catch (e: ApiException) {
            assertEquals("INTEGRITY_REQUIRED", e.code)
        }
        val staleHash = api.integrityRequestHash()
        val r = api.provision(pan, "3112", api.sandboxIntegrityToken(staleHash, op))
        assertTrue("ACTIVE kutilgan: $r", r is ProvisionResult.Active)
        val profile = (r as ProvisionResult.Active).profile
        assertEquals(5, profile.luks.size)
        println("token ${profile.tokenId} ${maskPan(profile.dpan)} idv=${r.idv}")

        // 2) Kotlin applet + Kotlin terminal → Rust emitent: ARQC tekshiriladi, ARPC kartada tasdiqlanadi.
        val gate = Gate()
        val applet = CardApplet({ profile }, gate)
        val date = java.time.LocalDate.now()
        val d = TerminalData.dateBcd(date.year, date.monthValue, date.dayOfMonth)
        val term = cred("MPAY_TERMINAL_KEY")
        val tap1 = TerminalKernel.tap({ applet.process(it) }, 1_250_000, d)
        val a1 = api.authorize(term, "TERMKT01", "SHOP0000000001", 1, tap1.iccHex())
        println("avtorizatsiya: $a1")
        assertEquals("00", a1.responseCode)
        assertTrue("ARPC Kotlin applet'da tasdiqlanishi kerak", applet.verifyIssuerAuth(Hex.decode(a1.issuerAuthData!!)))

        // 3) CDCVM: yuqori summa biometriyasiz — 6986; tasdiqdan keyin — 00.
        try {
            TerminalKernel.tap({ applet.process(it) }, 200_000_000, d)
            throw AssertionError("6986 kutilgan")
        } catch (e: TerminalException) {
            assertTrue(e.seePhone)
        }
        gate.ok = true
        val tap2 = TerminalKernel.tap({ applet.process(it) }, 200_000_000, d)
        assertEquals("00", api.authorize(term, "TERMKT01", "SHOP0000000001", 2, tap2.iccHex()).responseCode)

        // 4) Takroriy kriptogramma — Q1 (Rust emitent ATC replay'ni ushlaydi).
        val replay = api.authorize(term, "TERMKT01", "SHOP0000000001", 3, tap2.iccHex())
        assertEquals("Q1", replay.responseCode)
        assertEquals("ATC_REPLAY", replay.reason)

        // 5) LUK to'ldirish.
        assertEquals(5, api.replenish(profile.tokenId).size)

        // 5a) ADR-0015: qurilma kalitini almashtirish (Kotlin imzosi → Rust tekshiradi), token ko'chadi.
        val newKey = SoftDevice(dir, challenge = api.enrollNonce())
        val newId = api.rekey(newKey)
        println("kalit almashtirildi: yangi qurilma ${newId.take(16)}")
        api.connect(identity, newKey)
        // Token yangi qurilmaga bog'langan: qurilma tekshiruvidan o'tadi (eskisida — DEVICE_MISMATCH),
        // keyin faol LUK limiti (2 × partiya) to'lgani uchun TOO_MANY_LUKS.
        try {
            api.replenish(profile.tokenId)
            throw AssertionError("TOO_MANY_LUKS kutilgan")
        } catch (e: ApiException) {
            assertEquals("TOO_MANY_LUKS", e.code)
        }

        // 5b) ADR-0022: muddatni yangilash — oyna hali ochilmagan (36 oy), profil o'zgarmaydi (Kotlin ↔ Rust).
        val rn = api.renew(profile.tokenId)
        assertFalse(rn.renewed)
        assertEquals(profile.expiryYymm, rn.expiryYymm)
        assertEquals(profile.renewAfter, rn.renewAfter)
        assertNotNull("karta 3112, token undan oldin tugaydi — renew_after bor", rn.renewAfter)

        // 6) O'sha kartani ikkinchi qurilmaga — YELLOW → OTP (Shield dvigateli).
        val api2 = MpayClient(url)
        api2.connect(identity, SoftDevice(dir, challenge = api2.enrollNonce()))
        // Boshqa sessiya uchun olingan token — rad (sessiyaga bog'lanish).
        try {
            api2.provision(pan, "3112", api.sandboxIntegrityToken(staleHash, op))
            throw AssertionError("INTEGRITY_INVALID kutilgan")
        } catch (e: ApiException) {
            assertEquals("INTEGRITY_INVALID", e.code)
        }
        val y = api2.provision(pan, "3112", api2.sandboxIntegrityToken(api2.integrityRequestHash(), op))
        assertTrue("PENDING_IDV kutilgan: $y", y is ProvisionResult.PendingIdv)
        y as ProvisionResult.PendingIdv
        val gw = System.getenv("MPAY_SMSGW")
        val otp = if (gw != null) {
            // 2-faza P2.1: kod emitentdagi (fiktiv) telefonga virtual SMS shlyuzi orqali keldi.
            assertEquals("+998*******01", y.otpSentTo)
            assertEquals("+998*******01", api2.resendOtp(y.tokenId, y.challengeId))
            // Provisioning SMS'i fonda yuboriladi (ADR-0016) — qutida 2 ta xabarni kutamiz.
            var inbox = smsInbox(gw, "+998000000001")
            for (i in 0 until 30) {
                if (inbox.size >= 2) break
                Thread.sleep(100)
                inbox = smsInbox(gw, "+998000000001")
            }
            assertEquals(2, inbox.size)
            val codes = inbox.map { Regex("""\b(\d{6})\b""").find(it)!!.groupValues[1] }.toSet()
            assertEquals(1, codes.size)
            println("SMS keldi: ${y.otpSentTo} (2 ta, bir xil kod)")
            codes.first()
        } else {
            api2.sandboxOtp(y.challengeId, cred("MPAY_OPERATOR_KEY"))
        }
        val p2 = api2.verifyOtp(y.tokenId, y.challengeId, otp)
        assertEquals(5, p2.luks.size)

        // 7) Past attestatsiya darajasi (TEE) siyosat bo'yicha rad etiladi.
        try {
            MpayClient(url).connect(identity, SoftDevice(dir, level = 1))
            throw AssertionError("PQLINK_ATTESTATION kutilgan")
        } catch (e: ApiException) {
            assertEquals("PQLINK_ATTESTATION", e.code)
        }
    }

    /**
     * 1-faza P1.4: TLS (server pinlangan) + mTLS (`terminal-bundle`) — Rust server `init --tls`.
     * `MPAY_INTEROP_TLS_URL`, `MPAY_TLS_SANDBOX_DIR`, `MPAY_TERMINAL_BUNDLE`.
     */
    @Test
    fun pinnedTlsAndMtlsAgainstRustServer() {
        val tlsUrl = System.getenv("MPAY_INTEROP_TLS_URL")
        val dir = System.getenv("MPAY_TLS_SANDBOX_DIR")?.let(::File)
        val bundlePath = System.getenv("MPAY_TERMINAL_BUNDLE")
        assumeTrue("MPAY_INTEROP_TLS_URL o'rnatilmagan — o'tkazib yuborildi", tlsUrl != null && dir != null && bundlePath != null)
        val bundle = TerminalBundle.parse(File(bundlePath!!).readText())
        assertEquals("terminal-1", bundle.keyId)
        val pinOnly = TlsConfig(bundle.serverCertSha256)
        val mtls = TlsConfig(bundle.serverCertSha256, Pem.keyManager(bundle.clientCertPem, bundle.clientKeyPem))

        // Noto'g'ri pin — TLS ulanishning o'zi rad etiladi.
        val wrong = bundle.serverCertSha256.copyOf().also { it[0] = (it[0].toInt() xor 1).toByte() }
        try {
            MpayClient(tlsUrl!!, tls = TlsConfig(wrong)).terminalPing(bundle.terminalKey)
            throw AssertionError("pin xatosi kutilgan")
        } catch (e: javax.net.ssl.SSLException) {
            println("noto'g'ri pin rad etildi: ${e.javaClass.simpleName}")
        }

        // Sertifikatsiz — 403 MTLS_REQUIRED; sertifikat bilan — ping o'tadi.
        try {
            MpayClient(tlsUrl, tls = pinOnly).terminalPing(bundle.terminalKey)
            throw AssertionError("MTLS_REQUIRED kutilgan")
        } catch (e: ApiException) {
            assertEquals("MTLS_REQUIRED", e.code)
        }
        val term = MpayClient(tlsUrl, tls = mtls)
        assertEquals("terminal-1" to true, term.terminalPing(bundle.terminalKey))

        // P1.6: Rust `identity-next` e'lon qilgan keyingi identifikator — tasdiq Kotlin'da tekshiriladi.
        val info = MpayClient(tlsUrl, tls = pinOnly).identityInfo()
        println("keyingi identifikator: ${info.next?.let { Hex.encode(it.fingerprint()).take(16) }} tasdiq=${info.nextEndorsed}")
        assertTrue("next e'lon qilingan va tasdiqlangan bo'lishi kerak", info.next != null && info.nextEndorsed)

        // ADR-0014: Rust `revoke` imzolagan ro'yxat Kotlin'da ildiz bo'yicha tekshiriladi.
        val rootFp = System.getenv("MPAY_ROOT_FP")
        if (rootFp != null) {
            val rev = Revocations.verify(MpayClient(tlsUrl, tls = pinOnly).revocationsJson()!!, rootFp)
            println("bekor qilish ro'yxati: versiya ${rev.version}, ${rev.revoked.size} ta")
            assertEquals(3L, rev.version)
            assertTrue("cd".repeat(32) in rev.revoked)
        }

        // To'liq oqim TLS ustida: hamyon (sertifikatsiz, pinlangan) → token; terminal (mTLS) → 00.
        val wallet = MpayClient(tlsUrl, tls = pinOnly)
        val (identity, _) = wallet.identity()
        wallet.connect(identity, SoftDevice(dir!!, challenge = wallet.enrollNonce()))
        val pan = File(dir, "mpay.toml").readLines().filter { it.startsWith("pan = ") }[0].substringAfter("\"").substringBefore("\"")
        // P2.6: mock yaxlitlik tokeni hamyonning o'z PQ Link sessiyasi orqali — demo ilova kabi
        // operator kaliti va mTLS sertifikatisiz (TLS sandbox'ida operator yo'li 403 MTLS_REQUIRED).
        val token = wallet.sandboxDeviceIntegrityToken()
        assertTrue("mock token kutilgan", token != null)
        val r = wallet.provision(pan, "3112", token)
        assertTrue("ACTIVE kutilgan: $r", r is ProvisionResult.Active)
        val profile = (r as ProvisionResult.Active).profile
        val applet = CardApplet({ profile }, Gate())
        val date = java.time.LocalDate.now()
        val tap = TerminalKernel.tap({ applet.process(it) }, 1_250_000, TerminalData.dateBcd(date.year, date.monthValue, date.dayOfMonth))
        val a = term.authorize(bundle.terminalKey, "TERMKT01", "SHOP0000000001", 1, tap.iccHex())
        println("TLS+mTLS avtorizatsiya: ${a.responseCode} ${a.reason}")
        assertEquals("00", a.responseCode)
        assertTrue(applet.verifyIssuerAuth(Hex.decode(a.issuerAuthData!!)))

        // Takroriy yuborish (P1.2) — aynan o'sha javob.
        assertEquals(a, term.authorize(bundle.terminalKey, "TERMKT01", "SHOP0000000001", 1, tap.iccHex()))
    }
}
