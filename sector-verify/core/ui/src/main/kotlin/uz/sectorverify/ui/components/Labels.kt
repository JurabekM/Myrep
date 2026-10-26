package uz.sectorverify.ui.components

import androidx.annotation.StringRes
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.Verdict
import uz.sectorverify.ui.R
import uz.sectorverify.ui.theme.SvPalette

@StringRes
fun Verdict.labelRes(): Int = when (this) {
    Verdict.PASS -> R.string.verdict_pass
    Verdict.WARN -> R.string.verdict_warn
    Verdict.FAIL -> R.string.verdict_fail
    Verdict.INCONCLUSIVE -> R.string.verdict_inconclusive
}

@StringRes
fun CauseCode.labelRes(): Int = when (this) {
    CauseCode.NONE -> R.string.cause_none
    CauseCode.BAND_PORT_SWAP -> R.string.cause_band_port_swap
    CauseCode.CELL_CONFIG_SWAP -> R.string.cause_cell_config_swap
    CauseCode.ANTENNA_ROTATED -> R.string.cause_antenna_rotated
    CauseCode.PCI_MISSING -> R.string.cause_pci_missing
    CauseCode.PCI_UNEXPECTED -> R.string.cause_pci_unexpected
    CauseCode.LOW_COVERAGE -> R.string.cause_low_coverage
}

fun SvPalette.verdictColor(v: Verdict?): Color = when (v) {
    Verdict.PASS -> ok
    Verdict.WARN -> warn
    Verdict.FAIL -> danger
    Verdict.INCONCLUSIVE, null -> inkMuted
}

/** Stable colour per serving PCI for the track (chart palette, then hue rotation). */
fun SvPalette.pciColor(pci: Int): Color {
    val fixed = listOf(chart1, chart2, ok, warn, accentText, danger)
    return fixed[Math.floorMod(pci, fixed.size)]
}

@Composable
fun verdictText(v: Verdict): String = androidx.compose.ui.res.stringResource(v.labelRes())
