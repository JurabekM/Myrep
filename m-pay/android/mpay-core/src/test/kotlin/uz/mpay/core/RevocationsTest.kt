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
import org.junit.Assert.assertThrows
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
}
