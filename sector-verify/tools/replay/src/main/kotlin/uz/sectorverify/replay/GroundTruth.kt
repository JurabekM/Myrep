package uz.sectorverify.replay

import uz.sectorverify.format.Csv
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.Rat

/**
 * ground_truth.csv (§9, 4-bosqich): `site_code,rat,arfcn,pci,true_azimuth_deg,has_fault,fault_type`.
 * fault_type: NONE, CELL_CONFIG_SWAP, BAND_PORT_SWAP, SWAP (istalgan swap), ANTENNA_ROTATED, PCI_MISSING.
 */
data class TruthRow(val siteCode: String, val key: CellKey, val trueAzimuthDeg: Double?, val hasFault: Boolean, val faultType: String) {
    val isSwap: Boolean get() = faultType in SWAP_TYPES

    companion object {
        val SWAP_TYPES = setOf("SWAP", CauseCode.CELL_CONFIG_SWAP.name, CauseCode.BAND_PORT_SWAP.name)
    }
}

object GroundTruth {
    val HEADER = listOf("site_code", "rat", "arfcn", "pci", "true_azimuth_deg", "has_fault", "fault_type")

    fun parse(text: String): List<TruthRow> {
        val lines = Csv.lines(text).filter { it.isNotBlank() }
        require(lines.isNotEmpty()) { "ground_truth.csv bo'sh" }
        val sep = Csv.detectSeparator(lines.first())
        val header = Csv.parseLine(lines.first(), sep).map { it.lowercase() }
        require(header.containsAll(HEADER)) { "ground_truth.csv sarlavhasi: ${HEADER.joinToString(",")}" }
        return lines.drop(1).mapIndexed { i, line ->
            val f = header.zip(Csv.parseLine(line, sep)).toMap()
            runCatching {
                TruthRow(
                    siteCode = f.getValue("site_code"),
                    key = CellKey(Rat.valueOf(f.getValue("rat").uppercase()), f.getValue("arfcn").toInt(), f.getValue("pci").toInt()),
                    trueAzimuthDeg = f["true_azimuth_deg"]?.takeIf { it.isNotBlank() }?.replace(',', '.')?.toDouble(),
                    hasFault = f.getValue("has_fault").trim().lowercase() in setOf("1", "true", "yes", "ha"),
                    faultType = f["fault_type"].orEmpty().trim().uppercase().ifEmpty { "NONE" },
                )
            }.getOrElse { throw IllegalArgumentException("ground_truth.csv ${i + 2}-qator: ${it.message}", it) }
        }
    }

    fun write(rows: List<TruthRow>): String = buildString {
        appendLine(Csv.row(HEADER))
        for (r in rows) {
            appendLine(
                Csv.row(listOf(r.siteCode, r.key.rat, r.key.arfcn, r.key.pci, r.trueAzimuthDeg, if (r.hasFault) 1 else 0, r.faultType)),
            )
        }
    }
}
