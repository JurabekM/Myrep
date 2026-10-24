package uz.mpay.core

import org.bouncycastle.asn1.ASN1ObjectIdentifier
import org.bouncycastle.asn1.x500.X500Name
import org.bouncycastle.asn1.x509.SubjectPublicKeyInfo
import org.bouncycastle.cert.X509v3CertificateBuilder
import org.bouncycastle.cert.jcajce.JcaX509CertificateHolder
import org.bouncycastle.operator.jcajce.JcaContentSignerBuilder
import org.junit.Assert.assertEquals
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
    private class SoftDevice(dir: File, level: Int = 2) : DeviceKey {
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
                Tlv.primitive(0x04, "kotlin-interop".toByteArray()), Tlv.primitive(0x04, ByteArray(0)),
                Tlv.constructed(0x30), Tlv.constructed(0x30),
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
        val s = api.connect(identity, SoftDevice(dir))
        println("PQ Link sessiyasi: $s")
        val pan = demoPan(0)
        val r = api.provision(pan, "3112")
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

        // 6) O'sha kartani ikkinchi qurilmaga — YELLOW → OTP (Shield dvigateli).
        val api2 = MpayClient(url)
        api2.connect(identity, SoftDevice(dir))
        val y = api2.provision(pan, "3112")
        assertTrue("PENDING_IDV kutilgan: $y", y is ProvisionResult.PendingIdv)
        y as ProvisionResult.PendingIdv
        val otp = api2.sandboxOtp(y.challengeId, cred("MPAY_OPERATOR_KEY"))
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
}
