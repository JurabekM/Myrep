package uz.mpay.core

import org.bouncycastle.crypto.engines.AESEngine
import org.bouncycastle.crypto.macs.CMac
import org.bouncycastle.crypto.params.KeyParameter
import java.security.MessageDigest

/**
 * `MPAY-AES128-CMAC-V1` (ADR-0004, `emv-profile.md` §5–§7) — qurilma tomoni: LUK → SK → ARQC,
 * ARPC tekshiruvi. IMK va MK_tok qurilmada **yo'q**. KAT: `testvectors/emv-kat.json`.
 */
object MpayScheme {
    const val SCHEME_ID = 0x01
    private val LABEL_LUK = "MPAY-LUK".toByteArray(Charsets.US_ASCII)
    private val LABEL_SK = "MPAY-SK-AC".toByteArray(Charsets.US_ASCII)
    private val LABEL_MK = "MPAY-TOKEN-MK".toByteArray(Charsets.US_ASCII)

    fun cmac(key: ByteArray, data: ByteArray): ByteArray {
        require(key.size == 16)
        val m = CMac(AESEngine.newInstance())
        m.init(KeyParameter(key))
        m.update(data, 0, data.size)
        return ByteArray(16).also { m.doFinal(it, 0) }
    }

    /** SP 800-108 counter: `CMAC(K, 0x01 ‖ Label ‖ 0x00 ‖ Context ‖ 0x0080)`. */
    fun kdf(key: ByteArray, label: ByteArray, context: ByteArray): ByteArray {
        val input = java.io.ByteArrayOutputStream()
        input.write(1); input.write(label); input.write(0); input.write(context); input.write(0x00); input.write(0x80)
        return cmac(key, input.toByteArray())
    }

    /** Faqat KAT testi uchun (qurilma IMK'ni bilmaydi). */
    internal fun tokenMasterKey(imk: ByteArray, dpan: String, psn: Int): ByteArray {
        val d = dpan.toByteArray(Charsets.US_ASCII)
        return kdf(imk, LABEL_MK, byteArrayOf(d.size.toByte()) + d + byteArrayOf(psn.toByte()))
    }

    internal fun luk(mk: ByteArray, seq: Long): ByteArray =
        kdf(mk, LABEL_LUK, byteArrayOf((seq ushr 24).toByte(), (seq ushr 16).toByte(), (seq ushr 8).toByte(), seq.toByte()))

    fun sessionKey(luk: ByteArray, atc: Int): ByteArray =
        kdf(luk, LABEL_SK, byteArrayOf((atc ushr 8).toByte(), atc.toByte()))

    fun arqc(sk: ByteArray, cdol: ByteArray): ByteArray = cmac(sk, cdol).copyOf(8)

    fun arpc(sk: ByteArray, arqc: ByteArray, arc: ByteArray): ByteArray = cmac(sk, arqc + arc).copyOf(4)

    /** `91` = ARPC(4) ‖ ARC(2) ni constant-time tekshiradi. */
    fun verifyIssuerAuth(sk: ByteArray, arqc: ByteArray, iad91: ByteArray): Boolean {
        if (iad91.size != 6) return false
        val want = arpc(sk, arqc, iad91.copyOfRange(4, 6))
        return MessageDigest.isEqual(want, iad91.copyOfRange(0, 4))
    }
}
