package uz.mpay.core

import java.security.SecureRandom

/** APDU almashinuvi: NFC (`IsoDep.transceive`) yoki testlarda loopback applet. */
fun interface ApduTransceiver {
    fun transceive(capdu: ByteArray): ByteArray
}

class TerminalException(val sw: Int?, message: String) : Exception(message) {
    val seePhone: Boolean get() = sw == CardApplet.SW_SEE_PHONE
}

/** Tap natijasi: avtorizatsiya uchun ICC teglari. */
class TapResult(val icc: List<Tlv>, val dpanMasked: String, val atc: Int) {
    fun iccHex(): String = Hex.encode(Tlv.encodeAll(icc))
}

/**
 * Terminal yadrosi: SELECT PPSE → SELECT AID → GET PROCESSING OPTIONS
 * (`crates/mpay-terminal-sim/src/terminal.rs` bilan bir xil).
 */
object TerminalKernel {
    private val rng = SecureRandom()

    private fun select(name: ByteArray): ByteArray =
        byteArrayOf(0x00, 0xA4.toByte(), 0x04, 0x00, name.size.toByte()) + name + byteArrayOf(0x00)

    private fun send(t: ApduTransceiver, c: ByteArray): ByteArray {
        val r = t.transceive(c)
        if (r.size < 2) throw TerminalException(null, "R-APDU juda qisqa")
        val sw = ((r[r.size - 2].toInt() and 0xFF) shl 8) or (r[r.size - 1].toInt() and 0xFF)
        if (sw != CardApplet.SW_OK) throw TerminalException(sw, "karta holat so'zi %04X".format(sw))
        return r.copyOf(r.size - 2)
    }

    fun tap(t: ApduTransceiver, amountMinor: Long, date: ByteArray, currency: Int = Emv.UZ_NUMERIC): TapResult {
        val ppse = Tlv.parseAll(send(t, select(Emv.PPSE_NAME)))
        val disc = Tlv.find(ppse, Emv.Tag.FCI_ISSUER) ?: throw TerminalException(null, "PPSE FCI")
        val hasAid = disc.children().any { it.tag == Emv.Tag.APP_TEMPLATE && it.find(Emv.Tag.AID)?.bytes()?.contentEquals(Emv.AID) == true }
        if (!hasAid) throw TerminalException(null, "M-Pay Test Scheme ilovasi topilmadi")
        val fci = Tlv.parseAll(send(t, select(Emv.AID)))
        val pdol = Tlv.parseDol(Tlv.require(fci, Emv.Tag.PDOL))
        if (pdol != Emv.PDOL) throw TerminalException(null, "kutilmagan PDOL")
        val td = TerminalData(amountMinor = amountMinor, currency = currency, date = date, un = ByteArray(4).also { rng.nextBytes(it) })
        val data = td.toPdolData()
        val gpo = byteArrayOf(0x80.toByte(), 0xA8.toByte(), 0x00, 0x00, (data.size + 2).toByte(), 0x83.toByte(), data.size.toByte()) + data + byteArrayOf(0x00)
        val resp = Tlv.parseAll(send(t, gpo))
        val tmpl = resp.singleOrNull()?.takeIf { it.tag == Emv.Tag.RESP_TEMPLATE_2 } ?: throw TerminalException(null, "GPO formati")
        val card = tmpl.children()
        val (dpan, _) = Track2.decode(Tlv.require(card, Emv.Tag.TRACK2))
        val atcB = Tlv.require(card, Emv.Tag.ATC)
        val icc = card.toMutableList()
        var pos = 0
        for ((tag, len) in pdol) {
            icc.add(Tlv.primitive(tag, data.copyOfRange(pos, pos + len)))
            pos += len
        }
        return TapResult(icc, maskPan(dpan), ((atcB[0].toInt() and 0xFF) shl 8) or (atcB[1].toInt() and 0xFF))
    }
}
