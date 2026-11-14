package uz.mpay.core

/** Kartadagi LUK. `key` — 16 bayt (xotirada; saqlash shifrlangan — `wallet-sdk`). */
class CardLuk(val seq: Long, val key: ByteArray, val expiresAt: Long, var usesLeft: Int) {
    override fun toString() = "CardLuk(seq=$seq, usesLeft=$usesLeft)"
}

/** Token profili (kartada). */
class CardProfile(
    val tokenId: String,
    val dpan: String,
    val expiryYymm: String,
    val psn: Int,
    val luks: MutableList<CardLuk>,
    var atc: Int,
) {
    override fun toString() = "CardProfile($tokenId, ${maskPan(dpan)}, luks=${luks.size}, atc=$atc)"
}

/** CDCVM (biometriya) holati va siyosati. */
interface CdcvmGate {
    /** Biometrik tasdiq amal qilish oynasi ichidami. */
    fun isVerified(): Boolean
    /** Muvaffaqiyatli GPO'dan keyin — bir martalik. */
    fun consume()
}

/**
 * M-Pay Test Scheme HCE applet'i (`emv-profile.md` §2) — Rust `mpay-terminal-sim::card::SoftCard`
 * bilan bir xil xatti-harakat. Platformadan mustaqil: Android'da `HostApduService` chaqiradi.
 *
 * @param now unix sekund
 * @param onChanged ATC/LUK o'zgargach (saqlash uchun)
 */
class CardApplet(
    private val profileProvider: () -> CardProfile?,
    private val cdcvm: CdcvmGate,
    private val cdcvmLimitMinor: Long = 100_000_000,
    private val now: () -> Long = { System.currentTimeMillis() / 1000 },
    private val onChanged: (CardProfile) -> Unit = {},
) {
    private var selected = false
    private var last: Pair<ByteArray, ByteArray>? = null // (SK, ARQC)

    companion object {
        const val SW_OK = 0x9000
        const val SW_WRONG_LENGTH = 0x6700
        const val SW_WRONG_DATA = 0x6A80
        const val SW_FILE_NOT_FOUND = 0x6A82
        const val SW_CONDITIONS = 0x6985
        const val SW_SEE_PHONE = 0x6986
        const val SW_INS_NOT_SUPPORTED = 0x6D00
        const val SW_CLA_NOT_SUPPORTED = 0x6E00

        fun sw(code: Int) = byteArrayOf((code ushr 8).toByte(), code.toByte())

        val PPSE_FCI: ByteArray = Tlv.constructed(
            Emv.Tag.FCI,
            Tlv.primitive(Emv.Tag.DF_NAME, Emv.PPSE_NAME),
            Tlv.constructed(
                Emv.Tag.FCI_PROP,
                Tlv.constructed(
                    Emv.Tag.FCI_ISSUER,
                    Tlv.constructed(
                        Emv.Tag.APP_TEMPLATE,
                        Tlv.primitive(Emv.Tag.AID, Emv.AID),
                        Tlv.primitive(Emv.Tag.LABEL, Emv.APP_LABEL),
                        Tlv.primitive(Emv.Tag.PRIORITY, byteArrayOf(1)),
                    ),
                ),
            ),
        ).encode()

        val AID_FCI: ByteArray = Tlv.constructed(
            Emv.Tag.FCI,
            Tlv.primitive(Emv.Tag.DF_NAME, Emv.AID),
            Tlv.constructed(
                Emv.Tag.FCI_PROP,
                Tlv.primitive(Emv.Tag.LABEL, Emv.APP_LABEL),
                Tlv.primitive(Emv.Tag.PDOL, Tlv.encodeDol(Emv.PDOL)),
            ),
        ).encode()
    }

    /** Karta deaktivatsiya qilinganda (maydon yo'qoldi). */
    fun reset() {
        selected = false
    }

    /** Oxirgi tranzaksiya uchun emitent javobidagi `91` ni tekshiradi. */
    fun verifyIssuerAuth(iad91: ByteArray): Boolean {
        val (sk, arqc) = last ?: return false
        return MpayScheme.verifyIssuerAuth(sk, arqc, iad91)
    }

    fun process(apdu: ByteArray): ByteArray {
        if (apdu.size < 4) return sw(SW_WRONG_LENGTH)
        val cla = apdu[0].toInt() and 0xFF
        val ins = apdu[1].toInt() and 0xFF
        val data: ByteArray = when {
            apdu.size <= 5 -> ByteArray(0)
            else -> {
                val lc = apdu[4].toInt() and 0xFF
                if (lc == 0 || (apdu.size != 5 + lc && apdu.size != 6 + lc)) return sw(SW_WRONG_LENGTH)
                apdu.copyOfRange(5, 5 + lc)
            }
        }
        return when {
            cla == 0x00 && ins == 0xA4 && (apdu[2].toInt() and 0xFF) == 0x04 -> when {
                data.contentEquals(Emv.PPSE_NAME) -> { selected = false; PPSE_FCI + sw(SW_OK) }
                data.contentEquals(Emv.AID) -> {
                    if (profileProvider() == null) { selected = false; sw(SW_FILE_NOT_FOUND) } else { selected = true; AID_FCI + sw(SW_OK) }
                }
                else -> { selected = false; sw(SW_FILE_NOT_FOUND) }
            }
            cla == 0x80 && ins == 0xA8 -> gpo(data)
            cla == 0x00 || cla == 0x80 -> sw(SW_INS_NOT_SUPPORTED)
            else -> sw(SW_CLA_NOT_SUPPORTED)
        }
    }

    private fun gpo(data: ByteArray): ByteArray {
        val profile = profileProvider()
        if (!selected || profile == null) return sw(SW_CONDITIONS)
        val pdol = try {
            val l = Tlv.parseAll(data)
            if (l.size != 1 || l[0].tag != Emv.Tag.CMD_TEMPLATE) return sw(SW_WRONG_DATA)
            l[0].bytes() ?: return sw(SW_WRONG_DATA)
        } catch (e: TlvException) {
            return sw(SW_WRONG_DATA)
        }
        if (pdol.size != Emv.PDOL_DATA_LEN) return sw(SW_WRONG_DATA)
        val td = try { TerminalData.fromPdolData(pdol) } catch (e: IllegalArgumentException) { return sw(SW_WRONG_DATA) }
        val cdcvmRequired = td.amountMinor > cdcvmLimitMinor
        val cdcvmOk = cdcvm.isVerified()
        if (cdcvmRequired && !cdcvmOk) return sw(SW_SEE_PHONE)
        val t = now()
        val luk = profile.luks.firstOrNull { it.usesLeft > 0 && it.expiresAt > t } ?: return sw(SW_CONDITIONS)
        if (profile.atc >= 0xFFFF) return sw(SW_CONDITIONS)
        profile.atc += 1
        luk.usesLeft -= 1
        var cvr = 0
        if (cdcvmOk) cvr = cvr or Emv.CVR_CDCVM_PERFORMED
        if (cdcvmRequired) cvr = cvr or Emv.CVR_CDCVM_REQUIRED
        val iad = Iad(MpayScheme.SCHEME_ID, luk.seq, cvr)
        val sk = MpayScheme.sessionKey(luk.key, profile.atc)
        val arqc = MpayScheme.arqc(sk, Cdol.data(pdol, Emv.AIP, profile.atc, iad))
        last = sk to arqc
        if (cdcvmOk) cdcvm.consume()
        onChanged(profile)
        val y = 2000 + profile.expiryYymm.substring(0, 2).toInt()
        val m = profile.expiryYymm.substring(2, 4).toInt()
        val lastDay = java.time.YearMonth.of(y, m).lengthOfMonth()
        val body = Tlv.constructed(
            Emv.Tag.RESP_TEMPLATE_2,
            Tlv.primitive(Emv.Tag.AIP, Emv.AIP),
            Tlv.primitive(Emv.Tag.TRACK2, Track2.encode(profile.dpan, profile.expiryYymm)),
            Tlv.primitive(Emv.Tag.PSN, byteArrayOf(profile.psn.toByte())),
            Tlv.primitive(Emv.Tag.APP_EXPIRY, TerminalData.dateBcd(y, m, lastDay)),
            Tlv.primitive(Emv.Tag.ATC, byteArrayOf((profile.atc ushr 8).toByte(), profile.atc.toByte())),
            Tlv.primitive(Emv.Tag.ARQC, arqc),
            Tlv.primitive(Emv.Tag.CID, byteArrayOf(Emv.CID_ARQC.toByte())),
            Tlv.primitive(Emv.Tag.IAD, iad.toBytes()),
        )
        return body.encode() + sw(SW_OK)
    }
}
