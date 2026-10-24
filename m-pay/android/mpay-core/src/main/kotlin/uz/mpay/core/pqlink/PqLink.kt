package uz.mpay.core.pqlink

import org.bouncycastle.crypto.agreement.X25519Agreement
import org.bouncycastle.crypto.digests.SHA256Digest
import org.bouncycastle.crypto.generators.HKDFBytesGenerator
import org.bouncycastle.crypto.macs.HMac
import org.bouncycastle.crypto.modes.ChaCha20Poly1305
import org.bouncycastle.crypto.params.AEADParameters
import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.params.HKDFParameters
import org.bouncycastle.crypto.params.KeyParameter
import org.bouncycastle.crypto.params.ParametersWithContext
import org.bouncycastle.crypto.params.X25519PrivateKeyParameters
import org.bouncycastle.crypto.params.X25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import org.bouncycastle.crypto.params.MLDSAParameters
import org.bouncycastle.crypto.params.MLDSAPublicKeyParameters
import org.bouncycastle.crypto.signers.MLDSASigner
import org.bouncycastle.crypto.kems.MLKEMExtractor
import org.bouncycastle.crypto.params.MLKEMKeyGenerationParameters
import org.bouncycastle.crypto.generators.MLKEMKeyPairGenerator
import org.bouncycastle.crypto.params.MLKEMParameters
import org.bouncycastle.crypto.params.MLKEMPrivateKeyParameters
import org.bouncycastle.crypto.params.MLKEMPublicKeyParameters
import java.nio.ByteBuffer
import java.security.MessageDigest
import java.security.SecureRandom

/**
 * PQ Link v1 qurilma (client) tomoni — `docs/specs/pqlink.md`, Rust `mpay-pqlink::client` bilan
 * bayt-bayt mos. Interop: `InteropTest` haqiqiy `mpay-server` bilan.
 */
class PqLinkException(message: String) : Exception(message)

/** Pinlangan server identifikatori. */
class ServerIdentity(val ed25519: ByteArray, val mldsa65: ByteArray) {
    init {
        require(ed25519.size == 32 && mldsa65.size == PqLink.MLDSA65_PK_LEN) { "server identifikatori uzunligi" }
    }

    fun fingerprint(): ByteArray = sha256(ed25519, mldsa65)

    /** Gibrid imzo: Ed25519 **va** ML-DSA-65 (kontekst `mpay-pqlink-v1`) ikkalasi ham to'g'ri bo'lishi shart. */
    internal fun verifyHybrid(msg: ByteArray, sigEd: ByteArray, sigMl: ByteArray): Boolean {
        if (sigEd.size != 64 || sigMl.size != PqLink.MLDSA65_SIG_LEN) return false
        val ed = Ed25519Signer().apply { init(false, Ed25519PublicKeyParameters(ed25519, 0)); update(msg, 0, msg.size) }
        if (!ed.verifySignature(sigEd)) return false
        val ml = MLDSASigner().apply {
            init(false, ParametersWithContext(MLDSAPublicKeyParameters(MLDSAParameters.ml_dsa_65, mldsa65), PqLink.MLDSA_CTX))
            update(msg, 0, msg.size)
        }
        return ml.verifySignature(sigMl)
    }

    /** Kalit almashtirish (P1.6): shu identifikator `nextFingerprint` ni tasdiqlaganmi. */
    fun verifyEndorsement(nextFingerprint: ByteArray, sigEd: ByteArray, sigMl: ByteArray): Boolean =
        nextFingerprint.size == 32 && verifyHybrid(PqLink.ROTATION + nextFingerprint, sigEd, sigMl)
}

/** Qurilma kaliti: StrongBox P-256 (Android) yoki test kaliti. */
interface DeviceKey {
    /** Attestatsiya zanjiri (DER, leaf birinchi). */
    fun certChain(): List<ByteArray>

    /** ECDSA P-256 / SHA-256, DER. */
    fun sign(message: ByteArray): ByteArray
}

internal fun sha256(vararg parts: ByteArray): ByteArray {
    val d = MessageDigest.getInstance("SHA-256")
    parts.forEach { d.update(it) }
    return d.digest()
}

object PqLink {
    val MAGIC = "MPQL".toByteArray(Charsets.US_ASCII)
    const val VERSION = 0x01
    const val SUITE_V1 = 0x01
    const val T_CLIENT_HELLO = 0x01
    const val T_SERVER_HELLO = 0x02
    const val T_CLIENT_FINISHED = 0x03
    const val T_SERVER_ACCEPT = 0x04
    const val T_RECORD = 0x10
    const val MLKEM768_EK_LEN = 1184
    const val MLKEM768_CT_LEN = 1088
    const val MLDSA65_SIG_LEN = 3309
    const val MLDSA65_PK_LEN = 1952
    const val SERVER_HELLO_UNSIGNED_LEN = 6 + 32 + 16 + 1 + 32 + MLKEM768_CT_LEN + 32
    const val SERVER_HELLO_LEN = SERVER_HELLO_UNSIGNED_LEN + 64 + MLDSA65_SIG_LEN + 32
    const val DIR_C2S = 0x01
    const val DIR_S2C = 0x02
    const val CONTENT_TYPE = "application/x-mpay-pqlink"

    internal val TH1 = "MPAY-PQLINK-V1 TH1".toByteArray(Charsets.US_ASCII)
    internal val TH2 = "MPAY-PQLINK-V1 TH2".toByteArray(Charsets.US_ASCII)
    internal val SERVER_SIG = "MPAY-PQLINK-V1 server-sig".toByteArray(Charsets.US_ASCII)
    internal val DEVICE_SIG = "MPAY-PQLINK-V1 device-sig".toByteArray(Charsets.US_ASCII)
    internal val MLDSA_CTX = "mpay-pqlink-v1".toByteArray(Charsets.US_ASCII)
    internal val ROTATION = "MPAY-PQLINK-V1 identity-rotation".toByteArray(Charsets.US_ASCII)

    fun header(type: Int): ByteArray = MAGIC + byteArrayOf(VERSION.toByte(), type.toByte())

    internal fun hkdf(prk: ByteArray, salt: ByteArray, info: String): ByteArray {
        val g = HKDFBytesGenerator(SHA256Digest())
        g.init(HKDFParameters(prk, salt, info.toByteArray(Charsets.US_ASCII)))
        return ByteArray(32).also { g.generateBytes(it, 0, 32) }
    }

    internal fun hmac(key: ByteArray, data: ByteArray): ByteArray {
        val m = HMac(SHA256Digest())
        m.init(KeyParameter(key))
        m.update(data, 0, data.size)
        return ByteArray(32).also { m.doFinal(it, 0) }
    }

    internal fun aad(type: Int, sid: ByteArray, seq: Long, dir: Int): ByteArray =
        header(type) + sid + ByteBuffer.allocate(8).putLong(seq).array() + byteArrayOf(dir.toByte())

    internal fun nonce(seq: Long): ByteArray = ByteArray(4) + ByteBuffer.allocate(8).putLong(seq).array()

    internal fun seal(key: ByteArray, type: Int, sid: ByteArray, seq: Long, dir: Int, pt: ByteArray): ByteArray {
        val c = ChaCha20Poly1305()
        c.init(true, AEADParameters(KeyParameter(key), 128, nonce(seq), aad(type, sid, seq, dir)))
        val out = ByteArray(c.getOutputSize(pt.size))
        val n = c.processBytes(pt, 0, pt.size, out, 0)
        c.doFinal(out, n)
        return header(type) + sid + ByteBuffer.allocate(8).putLong(seq).array() + out
    }

    /** `(seq, ochiq matn)`. */
    internal fun open(key: ByteArray, type: Int, expectedSid: ByteArray, record: ByteArray, dir: Int): Pair<Long, ByteArray> {
        if (record.size < 6 + 16 + 8 + 16 || !record.copyOfRange(0, 6).contentEquals(header(type))) {
            throw PqLinkException("yozuv formati")
        }
        val sid = record.copyOfRange(6, 22)
        if (!MessageDigest.isEqual(sid, expectedSid)) throw PqLinkException("sessiya ID mos emas")
        val seq = ByteBuffer.wrap(record, 22, 8).long
        val ct = record.copyOfRange(30, record.size)
        val c = ChaCha20Poly1305()
        c.init(false, AEADParameters(KeyParameter(key), 128, nonce(seq), aad(type, sid, seq, dir)))
        val out = ByteArray(c.getOutputSize(ct.size))
        try {
            val n = c.processBytes(ct, 0, ct.size, out, 0)
            c.doFinal(out, n)
        } catch (e: Exception) {
            throw PqLinkException("yozuvni ochib bo'lmadi")
        }
        return seq to out
    }
}

/** Boshlangan handshake. */
class ClientHandshake private constructor(
    private val pinned: ServerIdentity,
    private val xPriv: X25519PrivateKeyParameters,
    private val kemPriv: MLKEMPrivateKeyParameters,
    val clientHello: ByteArray,
) {
    companion object {
        private val rng = SecureRandom()

        fun start(pinned: ServerIdentity): ClientHandshake {
            val x = X25519PrivateKeyParameters(rng)
            val gen = MLKEMKeyPairGenerator()
            gen.init(MLKEMKeyGenerationParameters(rng, MLKEMParameters.ml_kem_768))
            val kp = gen.generateKeyPair()
            val ek = (kp.public as MLKEMPublicKeyParameters).encoded
            check(ek.size == PqLink.MLKEM768_EK_LEN)
            val cRandom = ByteArray(32).also { rng.nextBytes(it) }
            val ch = PqLink.header(PqLink.T_CLIENT_HELLO) + cRandom + byteArrayOf(1, PqLink.SUITE_V1.toByte()) +
                x.generatePublicKey().encoded + ek
            return ClientHandshake(pinned, x, kp.private as MLKEMPrivateKeyParameters, ch)
        }
    }

    /** ServerHello → ClientFinished. Ikkala server imzosi va `s_finished` tekshiriladi. */
    fun onServerHello(sh: ByteArray, device: DeviceKey): Pair<PendingClient, ByteArray> {
        if (sh.size != PqLink.SERVER_HELLO_LEN || !sh.copyOfRange(0, 6).contentEquals(PqLink.header(PqLink.T_SERVER_HELLO))) {
            throw PqLinkException("ServerHello formati")
        }
        var p = 6 + 32
        val sid = sh.copyOfRange(p, p + 16); p += 16
        val suite = sh[p].toInt(); p += 1
        if (suite != PqLink.SUITE_V1) throw PqLinkException("kripto to'plami")
        val xs = sh.copyOfRange(p, p + 32); p += 32
        val ct = sh.copyOfRange(p, p + PqLink.MLKEM768_CT_LEN); p += PqLink.MLKEM768_CT_LEN
        val fp = sh.copyOfRange(p, p + 32); p += 32
        check(p == PqLink.SERVER_HELLO_UNSIGNED_LEN)
        val sigEd = sh.copyOfRange(p, p + 64); p += 64
        val sigMl = sh.copyOfRange(p, p + PqLink.MLDSA65_SIG_LEN); p += PqLink.MLDSA65_SIG_LEN
        val sFin = sh.copyOfRange(p, p + 32)
        if (!MessageDigest.isEqual(fp, pinned.fingerprint())) throw PqLinkException("server pinlangan identifikatorga mos emas")

        val th1 = sha256(PqLink.TH1, clientHello, sh.copyOfRange(0, PqLink.SERVER_HELLO_UNSIGNED_LEN))
        val msg = PqLink.SERVER_SIG + th1
        // Imzolar — kalit almashuvidan oldin.
        val ed = Ed25519Signer().apply { init(false, Ed25519PublicKeyParameters(pinned.ed25519, 0)); update(msg, 0, msg.size) }
        if (!ed.verifySignature(sigEd)) throw PqLinkException("server imzosi noto'g'ri (Ed25519)")
        val ml = MLDSASigner().apply {
            init(false, ParametersWithContext(MLDSAPublicKeyParameters(MLDSAParameters.ml_dsa_65, pinned.mldsa65), PqLink.MLDSA_CTX))
            update(msg, 0, msg.size)
        }
        if (!ml.verifySignature(sigMl)) throw PqLinkException("server imzosi noto'g'ri (ML-DSA-65)")

        val agree = X25519Agreement().apply { init(xPriv) }
        val ssX = ByteArray(32)
        agree.calculateAgreement(X25519PublicKeyParameters(xs, 0), ssX, 0)
        if (ssX.all { it.toInt() == 0 }) throw PqLinkException("X25519 kichik tartibli nuqta")
        val ssK = MLKEMExtractor(kemPriv).extractSecret(ct)
        val ss = ssX + ssK
        val c2s = PqLink.hkdf(ss, th1, "mpay pqlink v1 c2s")
        val s2c = PqLink.hkdf(ss, th1, "mpay pqlink v1 s2c")
        val finC = PqLink.hkdf(ss, th1, "mpay pqlink v1 c fin")
        val finS = PqLink.hkdf(ss, th1, "mpay pqlink v1 s fin")
        ss.fill(0); ssX.fill(0); ssK.fill(0)
        if (!MessageDigest.isEqual(PqLink.hmac(finS, th1), sFin)) throw PqLinkException("s_finished noto'g'ri")

        val th2 = sha256(PqLink.TH2, clientHello, sh)
        val inner = java.io.ByteArrayOutputStream()
        val chain = device.certChain()
        require(chain.isNotEmpty() && chain.size <= 6) { "attestatsiya zanjiri" }
        inner.write(chain.size)
        for (c in chain) { inner.write(c.size ushr 8); inner.write(c.size and 0xFF); inner.write(c) }
        val sig = device.sign(PqLink.DEVICE_SIG + th2)
        inner.write(sig.size ushr 8); inner.write(sig.size and 0xFF); inner.write(sig)
        inner.write(PqLink.hmac(finC, th2))
        val cf = PqLink.seal(c2s, PqLink.T_CLIENT_FINISHED, sid, 0, PqLink.DIR_C2S, inner.toByteArray())
        return PendingClient(sid, c2s, s2c) to cf
    }
}

class PendingClient internal constructor(private val sid: ByteArray, private val c2s: ByteArray, private val s2c: ByteArray) {
    fun onAccept(sa: ByteArray): ClientSession {
        val (seq, pt) = PqLink.open(s2c, PqLink.T_SERVER_ACCEPT, sid, sa, PqLink.DIR_S2C)
        if (seq != 0L || pt.size != 40) throw PqLinkException("ServerAccept")
        return ClientSession(sid, c2s, s2c, pt.copyOfRange(0, 32), ByteBuffer.wrap(pt, 32, 8).long)
    }
}

/** O'rnatilgan sessiya: so'rovlar ketma-ket (seq qat'iy monoton). */
class ClientSession internal constructor(
    val sessionId: ByteArray,
    private val c2s: ByteArray,
    private val s2c: ByteArray,
    val deviceId: ByteArray,
    val expiresAt: Long,
) {
    private var sendSeq = 1L
    private var recvSeq = 1L

    @Synchronized
    fun seal(plaintext: ByteArray): ByteArray = PqLink.seal(c2s, PqLink.T_RECORD, sessionId, sendSeq++, PqLink.DIR_C2S, plaintext)

    @Synchronized
    fun open(record: ByteArray): ByteArray {
        val (seq, pt) = PqLink.open(s2c, PqLink.T_RECORD, sessionId, record, PqLink.DIR_S2C)
        if (seq != recvSeq) throw PqLinkException("takroriy yoki tartibsiz yozuv")
        recvSeq++
        return pt
    }

    override fun toString() = "ClientSession(${deviceId.take(8).joinToString("") { "%02x".format(it) }})"
}
