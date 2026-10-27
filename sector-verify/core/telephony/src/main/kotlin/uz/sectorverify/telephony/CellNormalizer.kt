package uz.sectorverify.telephony

import uz.sectorverify.model.CellSample
import uz.sectorverify.model.Rat

/** Bitta CellInfo'ning platformaga bog'liq bo'lmagan nusxasi; Int.MAX_VALUE / Long.MAX_VALUE = CellInfo.UNAVAILABLE. */
data class RawCell(
    val rat: Rat,
    val registered: Boolean,
    val timestampNanos: Long,
    val arfcn: Int,
    val pci: Int,
    val rsrp: Int,
    val rsrq: Int,
    val sinr: Int,
    val ta: Int,
    val ci: Long,
    val tac: Int,
)

/** §7 CellNormalizer: UNAVAILABLE → null, diapazondan tashqari qiymatlar → null, noto'g'ri PCI/ARFCN → sample tashlanadi. */
object CellNormalizer {
    const val UNAVAILABLE = Int.MAX_VALUE
    const val UNAVAILABLE_LONG = Long.MAX_VALUE

    private val LTE_RSRP = -140..-44
    private val LTE_RSRQ = -34..3
    private val LTE_SINR = -23..40
    private val LTE_TA = 0..1282
    private val NR_RSRP = -156..-31
    private val NR_RSRQ = -43..20
    private val NR_SINR = -23..40
    private const val LTE_MAX_EARFCN = 262_143
    private const val NR_MAX_ARFCN = 3_279_165

    fun normalize(raw: RawCell, rxNanos: Long): CellSample? {
        val maxArfcn = if (raw.rat == Rat.LTE) LTE_MAX_EARFCN else NR_MAX_ARFCN
        if (raw.pci !in 0..raw.rat.maxPci || raw.arfcn !in 0..maxArfcn) return null
        val lte = raw.rat == Rat.LTE
        return CellSample(
            tNanos = raw.timestampNanos,
            rat = raw.rat,
            arfcn = raw.arfcn,
            pci = raw.pci,
            registered = raw.registered,
            rsrp = raw.rsrp.inRange(if (lte) LTE_RSRP else NR_RSRP),
            rsrq = raw.rsrq.inRange(if (lte) LTE_RSRQ else NR_RSRQ),
            sinr = raw.sinr.inRange(if (lte) LTE_SINR else NR_SINR),
            ta = if (lte) raw.ta.takeIf { it in LTE_TA } else null,
            ci = raw.ci.takeIf { it != UNAVAILABLE_LONG && it >= 0 },
            tac = raw.tac.takeIf { it != UNAVAILABLE && it >= 0 },
            rxNanos = rxNanos,
        )
    }

    private fun Int.inRange(r: IntRange): Double? = if (this != UNAVAILABLE && this in r) toDouble() else null
}
