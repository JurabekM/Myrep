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
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.mpay.core.pqlink.ServerIdentity
import java.security.SecureRandom

/** 1-faza P1.6: kalit almashtirish tasdig'i va pin to'plamini oldinga surish. */
class RotationTest {
    private class Keys {
        val ed = Ed25519KeyPairGenerator().apply { init(Ed25519KeyGenerationParameters(SecureRandom())) }.generateKeyPair()
        val ml = MLDSAKeyPairGenerator().apply { init(MLDSAKeyGenerationParameters(SecureRandom(), MLDSAParameters.ml_dsa_65)) }.generateKeyPair()
        val identity = ServerIdentity((ed.public as Ed25519PublicKeyParameters).encoded, (ml.public as MLDSAPublicKeyParameters).encoded)

        fun sign(msg: ByteArray): Pair<ByteArray, ByteArray> {
            val e = Ed25519Signer().apply { init(true, ed.private as Ed25519PrivateKeyParameters); update(msg, 0, msg.size) }.generateSignature()
            val m = MLDSASigner().apply {
                init(true, ParametersWithContext(ml.private as MLDSAPrivateKeyParameters, "mpay-pqlink-v1".toByteArray()))
                update(msg, 0, msg.size)
            }.generateSignature()
            return e to m
        }
    }

    private val rotation = "MPAY-PQLINK-V1 identity-rotation".toByteArray()

    @Test
    fun endorsementVerifiesAndIsDomainSeparated() {
        val cur = Keys()
        val next = Keys()
        val fp = next.identity.fingerprint()
        val (e, m) = cur.sign(rotation + fp)
        assertTrue(cur.identity.verifyEndorsement(fp, e, m))
        assertFalse("boshqa barmoq izi", cur.identity.verifyEndorsement(ByteArray(32), e, m))
        assertFalse("boshqa imzolovchi", next.identity.verifyEndorsement(fp, e, m))
        // Handshake yorlig'i bilan imzo tasdiq sifatida o'tmaydi.
        val (he, hm) = cur.sign("MPAY-PQLINK-V1 server-sig".toByteArray() + fp)
        assertFalse(cur.identity.verifyEndorsement(fp, he, hm))
    }

    @Test
    fun rollForwardOnlyWithEndorsement() {
        val cur = Keys()
        val next = Keys()
        val fp = Hex.encode(next.identity.fingerprint()).lowercase()
        val ok = MpayClient.IdentityInfo(cur.identity, Hex.encode(cur.identity.fingerprint()), next.identity, nextEndorsed = true)
        val bad = MpayClient.IdentityInfo(cur.identity, Hex.encode(cur.identity.fingerprint()), next.identity, nextEndorsed = false)
        val none = MpayClient.IdentityInfo(cur.identity, Hex.encode(cur.identity.fingerprint()), null, nextEndorsed = false)
        assertEquals(setOf(fp), ServerPinPolicy.rollForward(emptySet(), ok))
        assertEquals(emptySet<String>(), ServerPinPolicy.rollForward(emptySet(), bad))
        assertEquals(setOf("x"), ServerPinPolicy.rollForward(setOf("x"), none))
        // O'rganilgan pin bilan keyingi server qabul qilinadi, tasdiqsiz — yo'q.
        val policy = ServerPinPolicy(listOf(Hex.encode(cur.identity.fingerprint())) + ServerPinPolicy.rollForward(emptySet(), ok), false)
        policy.check(fp, null)
    }
}
