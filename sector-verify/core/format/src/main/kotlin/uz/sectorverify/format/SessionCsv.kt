package uz.sectorverify.format

import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat

/** Sessiya ZIP'idagi cell_samples.csv va gnss_fixes.csv (§5.4): xom qatorlar, hech narsa hisoblanmagan. */
object SessionCsv {
    val SAMPLE_HEADER = listOf("t_nanos", "rx_nanos", "rat", "arfcn", "pci", "registered", "rsrp", "rsrq", "sinr", "ta", "ci", "tac")
    val FIX_HEADER = listOf("t_nanos", "utc_ms", "lat", "lon", "acc_m", "speed_mps", "bearing_deg")

    fun writeSamples(samples: List<CellSample>, out: Appendable) {
        out.appendLine(Csv.row(SAMPLE_HEADER))
        for (s in samples) {
            val reg = if (s.registered) 1 else 0
            out.appendLine(Csv.row(listOf(s.tNanos, s.rxNanos, s.rat, s.arfcn, s.pci, reg, s.rsrp, s.rsrq, s.sinr, s.ta, s.ci, s.tac)))
        }
    }

    fun writeFixes(fixes: List<GnssFix>, out: Appendable) {
        out.appendLine(Csv.row(FIX_HEADER))
        for (f in fixes) out.appendLine(Csv.row(listOf(f.tNanos, f.utcMs, f.lat, f.lon, f.accM, f.speedMps, f.bearingDeg)))
    }

    fun readSamples(text: String): List<CellSample> = rows(text, SAMPLE_HEADER).map { r ->
        CellSample(
            tNanos = r.long("t_nanos")!!,
            rxNanos = r.long("rx_nanos"),
            rat = Rat.valueOf(r.str("rat")!!),
            arfcn = r.int("arfcn")!!,
            pci = r.int("pci")!!,
            registered = r.str("registered") == "1",
            rsrp = r.double("rsrp"),
            rsrq = r.double("rsrq"),
            sinr = r.double("sinr"),
            ta = r.int("ta"),
            ci = r.long("ci"),
            tac = r.int("tac"),
        )
    }

    fun readFixes(text: String): List<GnssFix> = rows(text, FIX_HEADER).map { r ->
        GnssFix(
            tNanos = r.long("t_nanos")!!,
            utcMs = r.long("utc_ms")!!,
            lat = r.double("lat")!!,
            lon = r.double("lon")!!,
            accM = r.double("acc_m")!!,
            speedMps = r.double("speed_mps"),
            bearingDeg = r.double("bearing_deg"),
        )
    }

    private class Record(private val values: Map<String, String>) {
        fun str(c: String): String? = values[c]?.takeIf { it.isNotEmpty() }
        fun long(c: String) = str(c)?.toLong()
        fun int(c: String) = str(c)?.toInt()
        fun double(c: String) = str(c)?.toDouble()
    }

    private fun rows(text: String, expected: List<String>): List<Record> {
        val lines = Csv.lines(text).filter { it.isNotBlank() }
        if (lines.isEmpty()) return emptyList()
        val header = Csv.parseLine(lines.first(), ',')
        require(header.containsAll(expected)) { "CSV header mismatch: $header" }
        return lines.drop(1).map { Record(header.zip(Csv.parseLine(it, ',')).toMap()) }
    }
}
