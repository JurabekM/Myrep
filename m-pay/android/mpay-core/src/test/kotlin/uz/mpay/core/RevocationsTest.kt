package uz.mpay.core

import org.bouncycastle.crypto.generators.Ed25519KeyPairGenerator
import org.bouncycastle.crypto.generators.MLDSAKeyPairGenerator
import org.bouncycastle.crypto.params.Ed25519KeyGenerationParameters
import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.params.MLDSAKeyGenerationParameters
import org.bouncycastle.crypto.params.MLDSAParameters
import org.bouncycastle.crypto.params.MLDSAPrivateKeyParameters
import org.bouncycastle.crypto.params.MLDSAPublicKeyParameters
import org.bouncycastle.crypto.params.ParametersWithContext
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.bouncycastle.crypto.signers.MLDSASigner
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Assert.assertThrows
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.mpay.core.pqlink.ServerIdentity
import java.security.SecureRandom

/** ADR-0014: oflayn ildiz imzolagan bekor qilish ro'yxati va pin siyosati. */
class RevocationsTest {
    private val ed = Ed25519KeyPairGenerator().apply { init(Ed25519KeyGenerationParameters(SecureRandom())) }.generateKeyPair()
    private val ml = MLDSAKeyPairGenerator().apply { init(MLDSAKeyGenerationParameters(SecureRandom(), MLDSAParameters.ml_dsa_65)) }.generateKeyPair()
    private val root = ServerIdentity((ed.public as Ed25519PublicKeyParameters).encoded, (ml.public as MLDSAPublicKeyParameters).encoded)
    private val rootFp = Hex.encode(root.fingerprint())

    private fun doc(version: Long, revoked: List<String>, signVersion: Long = version): String {
        val msg = Revocations.message(signVersion, revoked)
        val e = Ed25519Signer().apply { init(true, ed.private as Ed25519PrivateKeyParameters); update(msg, 0, msg.size) }.generateSignature()
        val m = MLDSASigner().apply {
            init(true, ParametersWithContext(ml.private as MLDSAPrivateKeyParameters, "mpay-pqlink-v1".toByteArray()))
            update(msg, 0, msg.size)
        }.generateSignature()
        return JSONObject().put("format", Revocations.FORMAT).put("version", version).put("revoked", JSONArray(revoked))
            .put("root_ed25519", Hex.encode(root.ed25519)).put("root_mldsa65", Hex.encode(root.mldsa65))
            .put("sig_ed25519", Hex.encode(e)).put("sig_mldsa65", Hex.encode(m)).toString()
    }

    private val a = "aa".repeat(32)
    private val b = "BB".repeat(32)

    @Test
    fun verifiesAndRejectsTamperOrForeignRoot() {
        // Tartib va registr ahamiyatsiz (kanonik xabar).
        val r = Revocations.verify(doc(5, listOf(b, a)), rootFp)
        assertEquals(5, r.version)
        assertEquals(setOf(a, b.lowercase()), r.revoked)
        assertThrows(PinException::class.java) { Revocations.verify(doc(5, listOf(a)), "00".repeat(32)) }
        assertThrows(PinException::class.java) { Revocations.verify(doc(6, listOf(a), signVersion = 5), rootFp) }
        val tampered = JSONObject(doc(5, listOf(a))).put("revoked", JSONArray(listOf(b))).toString()
        assertThrows(PinException::class.java) { Revocations.verify(tampered, rootFp) }
    }

    @Test
    fun revokedFingerprintRejectedEvenIfPinned() {
        val p = ServerPinPolicy(listOf(a, b), allowTofu = false, revoked = setOf(a))
        assertThrows(PinException::class.java) { p.check(a, null) }
        p.check(b, null)
        // TOFU ham bekor qilinganni qabul qilmaydi.
        assertThrows(PinException::class.java) { ServerPinPolicy(emptyList(), true, setOf(a)).check(a, null) }
    }

    /** ADR-0029: ilova build'i, mustaqil kanal va server — eng katta haqiqiy versiya yutadi. */
    @Test
    fun highestValidVersionAcrossSourcesWins() {
        val bundled = doc(3, listOf(a))
        // Hujumchi serveri (oshkor kalit bilan) eski, lekin haqiqiy ro'yxatni beradi — yutqazadi.
        val attackerServer = doc(1, emptyList())
        val cdn = doc(4, listOf(a, b))
        val sel = RevocationSources.select(
            rootFp,
            listOf(
                RevocationSources.Candidate("ilova", bundled),
                RevocationSources.Candidate("cdn", cdn),
                RevocationSources.Candidate("server", attackerServer),
            ),
        )
        assertEquals(4, sel.best!!.version)
        assertEquals("cdn", sel.bestSource)
        assertEquals(setOf(a, b.lowercase()), sel.best!!.revoked)
        assertTrue(sel.rejected.isEmpty())

        // Kanal soxtalashtirgan (versiyani oshirgan) yoki begona ildizli nusxa — rad, build nusxasi qoladi.
        val forged = JSONObject(cdn).put("version", 99).toString()
        val sel2 = RevocationSources.select(
            rootFp,
            listOf(
                RevocationSources.Candidate("ilova", bundled),
                RevocationSources.Candidate("cdn", forged),
                RevocationSources.Candidate("server", null),
                RevocationSources.Candidate("boshqa", "{not json"),
            ),
        )
        assertEquals(3, sel2.best!!.version)
        assertEquals("ilova", sel2.bestSource)
        assertEquals(2, sel2.rejected.size)
        assertTrue(sel2.rejected[0].startsWith("cdn:"))
        // Hech bir manba yo'q — tanlov bo'sh (qurilmada saqlangani ishlatiladi).
        assertNull(RevocationSources.select(rootFp, emptyList()).best)
    }

    @Test
    fun fetchFromIndependentChannel() {
        val big = "x".repeat(70 * 1024)
        val body = doc(7, listOf(a))
        val srv = com.sun.net.httpserver.HttpServer.create(java.net.InetSocketAddress("127.0.0.1", 0), 0)
        fun route(path: String, code: Int, text: String) = srv.createContext(path) { ex ->
            val bytes = text.toByteArray()
            ex.sendResponseHeaders(code, bytes.size.toLong())
            ex.responseBody.use { it.write(bytes) }
        }
        route("/rev.json", 200, body)
        route("/missing.json", 404, "")
        route("/big.json", 200, big)
        route("/moved.json", 302, "")
        srv.start()
        try {
            val base = "http://127.0.0.1:${srv.address.port}"
            val got = RevocationSources.fetch("$base/rev.json")
            assertEquals(7, Revocations.verify(got!!, rootFp).version)
            assertNull(RevocationSources.fetch("$base/missing.json"))
            assertNull("64 KB dan katta — rad", RevocationSources.fetch("$base/big.json"))
            assertNull("yo'naltirishga ergashilmaydi", RevocationSources.fetch("$base/moved.json"))
            // Loopback bo'lmagan oddiy http — rad (faqat https).
            assertNull(RevocationSources.fetch("http://example.com/rev.json"))
            // Yetib bo'lmaydigan manzil — null, istisno emas.
            assertNull(RevocationSources.fetch("http://127.0.0.1:1/rev.json", timeoutMs = 500))
        } finally {
            srv.stop(0)
        }
    }
}
