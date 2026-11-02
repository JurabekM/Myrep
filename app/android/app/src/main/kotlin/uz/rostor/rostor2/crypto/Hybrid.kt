package uz.rostor.rostor2.crypto

import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.digests.SHA3Digest
import org.bouncycastle.crypto.params.Ed25519PrivateKeyParameters
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.bouncycastle.pqc.crypto.mldsa.MLDSAParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSAPrivateKeyParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSAPublicKeyParameters
import org.bouncycastle.pqc.crypto.mldsa.MLDSASigner

/**
 * ROSTOR-1 gibrid imzosining tekshiruvi (spec §5.3): Ed25519 || ML-DSA-65, xom konkatenatsiya.
 * Ikkala imzo ham haqiqiy bo'lgandagina true. Ikkala tekshiruv har doim bajariladi.
 * Python referensi: scutum_q1/scutum/crypto/primitives.py::hybrid_verify.
 */
object Hybrid {
    const val ED25519_PK = 32
    const val ED25519_SIG = 64
    const val MLDSA65_PK = 1952
    const val MLDSA65_SIG = 3309
    const val SIG_LEN = ED25519_SIG + MLDSA65_SIG

    fun verify(edPk: ByteArray, mldsaPk: ByteArray, sig: ByteArray, msg: ByteArray): Boolean {
        if (edPk.size != ED25519_PK || mldsaPk.size != MLDSA65_PK || sig.size != SIG_LEN) return false
        val okEd = verifyEd25519(edPk, sig.copyOfRange(0, ED25519_SIG), msg)
        val okPq = verifyMlDsa65(mldsaPk, sig.copyOfRange(ED25519_SIG, SIG_LEN), msg)
        return okEd and okPq
    }

    /** Qurilma kaliti (F3): 32 baytli urug'lardan ochiq kalitlar. ML-DSA urug'i FIPS 204 ξ (Python from_seed_bytes bilan bir xil). */
    fun publicKeys(edSeed: ByteArray, mldsaSeed: ByteArray): Pair<ByteArray, ByteArray> {
        val ed = Ed25519PrivateKeyParameters(edSeed, 0).generatePublicKey().encoded
        val ml = MLDSAPrivateKeyParameters(MLDSAParameters.ml_dsa_65, mldsaSeed).publicKeyParameters.encoded
        return ed to ml
    }

    /** Ed25519 || ML-DSA-65 gibrid imzo (ROSTOR-1 §5.3 formati). */
    fun sign(edSeed: ByteArray, mldsaSeed: ByteArray, msg: ByteArray): ByteArray {
        val e = Ed25519Signer()
        e.init(true, Ed25519PrivateKeyParameters(edSeed, 0))
        e.update(msg, 0, msg.size)
        val m = MLDSASigner()
        m.init(true, MLDSAPrivateKeyParameters(MLDSAParameters.ml_dsa_65, mldsaSeed))
        m.update(msg, 0, msg.size)
        return e.generateSignature() + m.generateSignature()
    }

    fun verifyEd25519(pk: ByteArray, sig: ByteArray, msg: ByteArray): Boolean = try {
        val s = Ed25519Signer()
        s.init(false, Ed25519PublicKeyParameters(pk, 0))
        s.update(msg, 0, msg.size)
        s.verifySignature(sig)
    } catch (e: Exception) {
        false
    }

    fun verifyMlDsa65(pk: ByteArray, sig: ByteArray, msg: ByteArray): Boolean = try {
        val s = MLDSASigner()
        s.init(false, MLDSAPublicKeyParameters(MLDSAParameters.ml_dsa_65, pk))
        s.update(msg, 0, msg.size)
        s.verifySignature(sig)
    } catch (e: Exception) {
        false
    }

    fun sha3_256(vararg parts: ByteArray): ByteArray {
        val d = SHA3Digest(256)
        for (p in parts) d.update(p, 0, p.size)
        return ByteArray(32).also { d.doFinal(it, 0) }
    }

    fun sha256(data: ByteArray): ByteArray {
        val d = SHA256Digest()
        d.update(data, 0, data.size)
        return ByteArray(32).also { d.doFinal(it, 0) }
    }
}

fun ByteArray.toHex(): String = joinToString("") { "%02x".format(it) }

fun String.hexToBytes(): ByteArray {
    require(length % 2 == 0) { "hex uzunligi toq" }
    return ByteArray(length / 2) { i -> substring(2 * i, 2 * i + 2).toInt(16).toByte() }
}
