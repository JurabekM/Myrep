package uz.sectorverify.feature.report

import android.content.res.Resources
import kotlin.math.abs
import kotlin.math.roundToInt
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.Finding
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.Verdict
import uz.sectorverify.ui.R as UiR

/** Recommended action per sector in the chosen language (§8.1 screen 5, §8.2). */
object Recommendations {
    private const val BIN_DEG = 10

    fun forSector(res: Resources, s: SectorResult, findings: List<Finding>): String {
        val err = s.errorDeg?.let { abs(it).roundToInt().toString() } ?: "—"
        return when (s.cause) {
            CauseCode.CELL_CONFIG_SWAP, CauseCode.BAND_PORT_SWAP -> {
                val target = swapTarget(s, findings) ?: "?"
                val id = if (s.cause == CauseCode.CELL_CONFIG_SWAP) UiR.string.action_cell_config_swap else UiR.string.action_band_port_swap
                res.getString(id, s.key.pci.toString(), target)
            }
            CauseCode.ANTENNA_ROTATED -> res.getString(
                UiR.string.action_antenna_rotated,
                err,
                s.planAzimuthDeg?.roundToInt()?.toString() ?: "—",
            )
            CauseCode.PCI_MISSING -> res.getString(UiR.string.action_pci_missing)
            CauseCode.PCI_UNEXPECTED -> res.getString(UiR.string.action_pci_unexpected)
            CauseCode.LOW_COVERAGE -> res.getString(UiR.string.action_low_coverage)
            CauseCode.NONE -> when {
                s.verdict == Verdict.PASS -> res.getString(UiR.string.action_ok)
                s.estimate?.unreliable == true || s.verdict == Verdict.INCONCLUSIVE -> res.getString(UiR.string.action_unreliable)
                else -> res.getString(UiR.string.action_large_error, err)
            }
        }
    }

    fun swapTarget(s: SectorResult, findings: List<Finding>): String? = findings
        .firstOrNull { it.type == FindingType.SWAP && it.detail["arfcn"] == s.key.arfcn.toString() && it.detail["rat"] == s.key.rat.name }
        ?.detail?.get("pci.${s.key.pci}")

    /** Missing bin indices → compact direction ranges, e.g. "20°–60°, 300°–320°". */
    fun directions(bins: List<Int>): String {
        if (bins.isEmpty()) return "—"
        val sorted = bins.sorted()
        val ranges = ArrayList<IntRange>()
        var start = sorted.first()
        var prev = start
        for (b in sorted.drop(1)) {
            if (b != prev + 1) {
                ranges += start..prev
                start = b
            }
            prev = b
        }
        ranges += start..prev
        return ranges.joinToString(", ") { "${it.first * BIN_DEG}°–${(it.last + 1) * BIN_DEG}°" }
    }
}
