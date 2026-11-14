package uz.mpay.core

/** M-Pay Test Scheme profili — `docs/specs/emv-profile.md`, `crates/mpay-common/src/emv.rs`. */
object Emv {
    val PPSE_NAME: ByteArray = "2PAY.SYS.DDF01".toByteArray(Charsets.US_ASCII)
    val AID: ByteArray = byteArrayOf(0xF0.toByte(), 0x4D, 0x50, 0x41, 0x59, 0x01)
    val APP_LABEL: ByteArray = "M-PAY TEST".toByteArray(Charsets.US_ASCII)
    val AIP: ByteArray = byteArrayOf(0x00, 0x80.toByte())
    const val CID_ARQC = 0x80
    const val UZ_NUMERIC = 860
    const val PDOL_DATA_LEN = 29
    const val CDOL_LEN = 41
    const val IAD_LEN = 8

    object Tag {
        const val FCI = 0x6F; const val DF_NAME = 0x84; const val FCI_PROP = 0xA5; const val FCI_ISSUER = 0xBF0C
        const val APP_TEMPLATE = 0x61; const val AID = 0x4F; const val LABEL = 0x50; const val PRIORITY = 0x87
        const val PDOL = 0x9F38; const val CMD_TEMPLATE = 0x83; const val RESP_TEMPLATE_2 = 0x77
        const val AIP = 0x82; const val TRACK2 = 0x57; const val PSN = 0x5F34; const val APP_EXPIRY = 0x5F24
        const val ATC = 0x9F36; const val ARQC = 0x9F26; const val CID = 0x9F27; const val IAD = 0x9F10
        const val AMOUNT = 0x9F02; const val AMOUNT_OTHER = 0x9F03; const val COUNTRY = 0x9F1A; const val TVR = 0x95
        const val CURRENCY = 0x5F2A; const val DATE = 0x9A; const val TXN_TYPE = 0x9C; const val UN = 0x9F37
    }

    /** PDOL tartibi (29 bayt). */
    val PDOL: List<Pair<Int, Int>> = listOf(
        Tag.AMOUNT to 6, Tag.AMOUNT_OTHER to 6, Tag.COUNTRY to 2, Tag.TVR to 5,
        Tag.CURRENCY to 2, Tag.DATE to 3, Tag.TXN_TYPE to 1, Tag.UN to 4,
    )

    /** CVR bitlari (IAD bayt 6). */
    const val CVR_CDCVM_PERFORMED = 0x80
    const val CVR_CDCVM_REQUIRED = 0x40

    fun toBcd(value: Long, nBytes: Int): ByteArray {
        var v = value
        require(v >= 0)
        val out = ByteArray(nBytes)
        for (i in nBytes - 1 downTo 0) {
            val lo = (v % 10).toInt(); v /= 10
            val hi = (v % 10).toInt(); v /= 10
            out[i] = ((hi shl 4) or lo).toByte()
        }
        require(v == 0L) { "qiymat BCD sig'imidan katta" }
        return out
    }

    fun fromBcd(b: ByteArray): Long {
        var v = 0L
        for (x in b) {
            val hi = (x.toInt() ushr 4) and 0xF; val lo = x.toInt() and 0xF
            require(hi <= 9 && lo <= 9) { "noto'g'ri BCD" }
            v = v * 100 + hi * 10 + lo
        }
        return v
    }
}

/** Terminal ma'lumotlari (PDOL). */
data class TerminalData(
    val amountMinor: Long,
    val otherAmountMinor: Long = 0,
    val country: Int = Emv.UZ_NUMERIC,
    val tvr: ByteArray = ByteArray(5),
    val currency: Int = Emv.UZ_NUMERIC,
    /** YYMMDD (BCD, 3 bayt). */
    val date: ByteArray,
    val txnType: Int = 0,
    val un: ByteArray,
) {
    fun toPdolData(): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        out.write(Emv.toBcd(amountMinor, 6)); out.write(Emv.toBcd(otherAmountMinor, 6))
        out.write(Emv.toBcd(country.toLong(), 2)); out.write(tvr)
        out.write(Emv.toBcd(currency.toLong(), 2)); out.write(date)
        out.write(Emv.toBcd(txnType.toLong(), 1)); out.write(un)
        return out.toByteArray().also { check(it.size == Emv.PDOL_DATA_LEN) }
    }

    companion object {
        fun fromPdolData(d: ByteArray): TerminalData {
            require(d.size == Emv.PDOL_DATA_LEN) { "PDOL uzunligi ${d.size}" }
            return TerminalData(
                amountMinor = Emv.fromBcd(d.copyOfRange(0, 6)),
                otherAmountMinor = Emv.fromBcd(d.copyOfRange(6, 12)),
                country = Emv.fromBcd(d.copyOfRange(12, 14)).toInt(),
                tvr = d.copyOfRange(14, 19),
                currency = Emv.fromBcd(d.copyOfRange(19, 21)).toInt(),
                date = d.copyOfRange(21, 24),
                txnType = Emv.fromBcd(d.copyOfRange(24, 25)).toInt(),
                un = d.copyOfRange(25, 29),
            )
        }

        fun dateBcd(year: Int, month: Int, day: Int): ByteArray =
            Emv.toBcd(((year % 100) * 10_000 + month * 100 + day).toLong(), 3)
    }
}

/** IAD (`9F10`, 8 bayt): versiya, sxema, LUK seq, CVR. */
data class Iad(val schemeId: Int, val lukSeq: Long, val cvr: Int) {
    fun toBytes(): ByteArray = byteArrayOf(
        0x01, schemeId.toByte(),
        (lukSeq ushr 24).toByte(), (lukSeq ushr 16).toByte(), (lukSeq ushr 8).toByte(), lukSeq.toByte(),
        cvr.toByte(), 0x00,
    )

    companion object {
        fun parse(b: ByteArray): Iad {
            require(b.size == Emv.IAD_LEN && b[0].toInt() == 1 && b[7].toInt() == 0) { "IAD formati" }
            val seq = ((b[2].toLong() and 0xFF) shl 24) or ((b[3].toLong() and 0xFF) shl 16) or
                ((b[4].toLong() and 0xFF) shl 8) or (b[5].toLong() and 0xFF)
            return Iad(b[1].toInt() and 0xFF, seq, b[6].toInt() and 0xFF)
        }
    }
}

object Cdol {
    /** ARQC kirishi: PDOL ‖ AIP ‖ ATC ‖ IAD (41 bayt). */
    fun data(pdol: ByteArray, aip: ByteArray, atc: Int, iad: Iad): ByteArray {
        val out = java.io.ByteArrayOutputStream()
        out.write(pdol); out.write(aip); out.write(atc ushr 8); out.write(atc and 0xFF); out.write(iad.toBytes())
        return out.toByteArray().also { check(it.size == Emv.CDOL_LEN) }
    }
}

object Track2 {
    /** EMV `57`: DPAN ‖ D ‖ YYMM ‖ 201 ‖ 0000 (BCD, toq bo'lsa F). */
    fun encode(dpan: String, expiryYymm: String): ByteArray {
        val s = dpan + "D" + expiryYymm + "201" + "0000"
        val nib = s.map { if (it == 'D') 0xD else it - '0' }.toMutableList()
        if (nib.size % 2 == 1) nib.add(0xF)
        return ByteArray(nib.size / 2) { i -> ((nib[2 * i] shl 4) or nib[2 * i + 1]).toByte() }
    }

    /** `57` dan DPAN va YYMM. */
    fun decode(b: ByteArray): Pair<String, String> {
        val sb = StringBuilder()
        for ((i, x) in b.withIndex()) {
            for (n in intArrayOf((x.toInt() ushr 4) and 0xF, x.toInt() and 0xF)) {
                when {
                    n <= 9 -> sb.append('0' + n)
                    n == 0xD -> sb.append('=')
                    n == 0xF && i == b.size - 1 -> {}
                    else -> throw IllegalArgumentException("Track 2")
                }
            }
        }
        val (pan, rest) = sb.toString().split('=', limit = 2).let { it[0] to it.getOrElse(1) { "" } }
        require(rest.length >= 4) { "Track 2" }
        return pan to rest.substring(0, 4)
    }
}

/** PAN maskasi: birinchi 6 + `******` + oxirgi 4. */
fun maskPan(pan: String): String =
    if (pan.length < 10) "****" else pan.take(6) + "*".repeat(pan.length - 10) + pan.takeLast(4)
