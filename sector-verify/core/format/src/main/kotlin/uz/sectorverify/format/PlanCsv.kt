package uz.sectorverify.format

import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SitePlan

enum class PlanErrorCode {
    EMPTY_FILE,
    MISSING_COLUMN,
    WRONG_COLUMN_COUNT,
    EMPTY_VALUE,
    NOT_A_NUMBER,
    LAT_RANGE,
    LON_RANGE,
    BAD_RAT,
    PCI_RANGE,
    AZIMUTH_RANGE,
    HPBW_RANGE,
    ARFCN_RANGE,
    DUPLICATE_CELL,
    SITE_COORDS_MISMATCH,
}

/** [line] is 1-based (the header is line 1). [column] is the CSV column name. */
data class PlanError(val line: Int, val code: PlanErrorCode, val column: String? = null, val value: String? = null) {
    /** Default Uzbek message (UI uses string resources keyed by [code]; CLI prints this). */
    fun messageUz(): String {
        val v = value?.let { " (\"$it\")" }.orEmpty()
        val c = column ?: ""
        val text = when (code) {
            PlanErrorCode.EMPTY_FILE -> "fayl bo'sh"
            PlanErrorCode.MISSING_COLUMN -> "sarlavhada \"$c\" ustuni yo'q"
            PlanErrorCode.WRONG_COLUMN_COUNT -> "ustunlar soni sarlavhaga mos emas"
            PlanErrorCode.EMPTY_VALUE -> "\"$c\" bo'sh"
            PlanErrorCode.NOT_A_NUMBER -> "\"$c\" son emas$v"
            PlanErrorCode.LAT_RANGE -> "kenglik −90..90 oralig'ida bo'lishi kerak$v"
            PlanErrorCode.LON_RANGE -> "uzunlik −180..180 oralig'ida bo'lishi kerak$v"
            PlanErrorCode.BAD_RAT -> "rat LTE yoki NR bo'lishi kerak$v"
            PlanErrorCode.PCI_RANGE -> "PCI chegaradan tashqarida (LTE 0..503, NR 0..1007)$v"
            PlanErrorCode.AZIMUTH_RANGE -> "azimut 0..359.9 oralig'ida bo'lishi kerak$v"
            PlanErrorCode.HPBW_RANGE -> "HPBW 20..120 oralig'ida bo'lishi kerak$v"
            PlanErrorCode.ARFCN_RANGE -> "ARFCN manfiy bo'lmasligi kerak$v"
            PlanErrorCode.DUPLICATE_CELL -> "saytda (rat, arfcn, pci) takrorlanmoqda$v"
            PlanErrorCode.SITE_COORDS_MISMATCH -> "saytning koordinatasi boshqa qatorlardagidan farq qiladi$v"
        }
        return "$line-qator: $text"
    }
}

data class PlanImport(val sites: List<SitePlan>, val errors: List<PlanError>) {
    val ok: Boolean get() = errors.isEmpty()
}

/** RF plan CSV (§5.3): parse with full validation, and write back (plan.csv in the session ZIP). */
object PlanCsv {
    val HEADER = listOf(
        "site_code", "site_name", "lat", "lon", "mcc_mnc", "sector", "rat", "band", "arfcn", "pci",
        "azimuth_deg", "hpbw_deg", "mech_tilt_deg", "elec_tilt_deg", "height_m",
    )
    private val OPTIONAL = setOf("hpbw_deg", "mech_tilt_deg", "elec_tilt_deg", "height_m")
    private const val HPBW_MIN = 20.0
    private const val HPBW_MAX = 120.0
    private const val AZ_MAX = 359.9
    private const val LAT_MAX = 90.0
    private const val LON_MAX = 180.0

    private class Row(
        val line: Int,
        val code: String,
        val name: String,
        val lat: Double,
        val lon: Double,
        val mccMnc: String,
        val sector: Sector,
    )

    fun parse(text: String): PlanImport {
        val lines = Csv.lines(text)
        val firstIdx = lines.indexOfFirst { it.isNotBlank() }
        if (firstIdx < 0) return PlanImport(emptyList(), listOf(PlanError(1, PlanErrorCode.EMPTY_FILE)))
        val sep = Csv.detectSeparator(lines[firstIdx])
        val header = Csv.parseLine(lines[firstIdx], sep).map { it.lowercase() }
        val missing = HEADER.filter { it !in OPTIONAL && it !in header }
        if (missing.isNotEmpty()) {
            return PlanImport(emptyList(), missing.map { PlanError(firstIdx + 1, PlanErrorCode.MISSING_COLUMN, it) })
        }
        val errors = ArrayList<PlanError>()
        val rows = ArrayList<Row>()
        for (i in firstIdx + 1 until lines.size) {
            if (lines[i].isBlank()) continue
            val cells = Csv.parseLine(lines[i], sep)
            if (cells.size == header.size) {
                parseRow(i + 1, header.zip(cells).toMap(), errors)?.let { rows += it }
            } else {
                errors += PlanError(i + 1, PlanErrorCode.WRONG_COLUMN_COUNT)
            }
        }
        errors += crossRowErrors(rows)
        val sites = if (errors.isEmpty()) {
            rows.groupBy { it.code }.map { (code, r) ->
                SitePlan(code, r.first().name, r.first().lat, r.first().lon, r.first().mccMnc, r.map { it.sector })
            }
        } else {
            emptyList()
        }
        return PlanImport(sites, errors.sortedBy { it.line })
    }

    /** Reads typed fields of one row and collects their errors. */
    private class Fields(private val line: Int, private val f: Map<String, String>, val errors: MutableList<PlanError>) {
        fun text(c: String): String = f[c].orEmpty().also { if (it.isEmpty()) errors += PlanError(line, PlanErrorCode.EMPTY_VALUE, c) }

        fun num(c: String, required: Boolean = true): Double? {
            val raw = f[c].orEmpty()
            if (raw.isEmpty()) {
                if (required) errors += PlanError(line, PlanErrorCode.EMPTY_VALUE, c)
                return null
            }
            val v = raw.replace(',', '.').toDoubleOrNull()
            if (v == null) errors += PlanError(line, PlanErrorCode.NOT_A_NUMBER, c, raw)
            return v
        }

        fun check(value: Double?, c: String, code: PlanErrorCode, ok: (Double) -> Boolean) {
            if (value != null && !ok(value)) errors += PlanError(line, code, c, f[c])
        }

        fun rat(): Rat? {
            val raw = text("rat")
            val rat = Rat.entries.firstOrNull { it.name.equals(raw, ignoreCase = true) }
            if (raw.isNotEmpty() && rat == null) errors += PlanError(line, PlanErrorCode.BAD_RAT, "rat", raw)
            return rat
        }
    }

    private fun isWhole(x: Double) = x == Math.floor(x)

    private fun parseRow(line: Int, f: Map<String, String>, errors: MutableList<PlanError>): Row? {
        val before = errors.size
        val r = Fields(line, f, errors)
        val code = r.text("site_code")
        val name = r.text("site_name")
        val mccMnc = r.text("mcc_mnc")
        val label = r.text("sector")
        val band = r.text("band")
        val rat = r.rat()
        val lat = r.num("lat")
        val lon = r.num("lon")
        val arfcn = r.num("arfcn")
        val pci = r.num("pci")
        val az = r.num("azimuth_deg")
        val hpbw = r.num("hpbw_deg", required = false)
        val mech = r.num("mech_tilt_deg", required = false)
        val elec = r.num("elec_tilt_deg", required = false)
        val height = r.num("height_m", required = false)
        r.check(lat, "lat", PlanErrorCode.LAT_RANGE) { it in -LAT_MAX..LAT_MAX }
        r.check(lon, "lon", PlanErrorCode.LON_RANGE) { it in -LON_MAX..LON_MAX }
        r.check(az, "azimuth_deg", PlanErrorCode.AZIMUTH_RANGE) { it in 0.0..AZ_MAX }
        r.check(hpbw, "hpbw_deg", PlanErrorCode.HPBW_RANGE) { it in HPBW_MIN..HPBW_MAX }
        r.check(arfcn, "arfcn", PlanErrorCode.ARFCN_RANGE) { it >= 0 && isWhole(it) }
        if (rat != null) r.check(pci, "pci", PlanErrorCode.PCI_RANGE) { isWhole(it) && it >= 0 && it <= rat.maxPci }
        if (errors.size != before) return null
        // No new errors ⇒ every required value is present.
        val sector = Sector(label, rat!!, band, arfcn!!.toInt(), pci!!.toInt(), az!!, hpbw ?: Sector.DEFAULT_HPBW_DEG, mech, elec, height)
        return Row(line, code, name, lat!!, lon!!, mccMnc, sector)
    }

    private fun crossRowErrors(rows: List<Row>): List<PlanError> = buildList {
        for ((_, site) in rows.groupBy { it.code }) {
            val first = site.first()
            val seen = HashSet<Triple<Rat, Int, Int>>()
            for (r in site) {
                if (!seen.add(Triple(r.sector.rat, r.sector.arfcn, r.sector.pci))) {
                    add(PlanError(r.line, PlanErrorCode.DUPLICATE_CELL, "pci", "${r.sector.rat}/${r.sector.arfcn}/${r.sector.pci}"))
                }
                if (r.lat != first.lat || r.lon != first.lon) {
                    add(PlanError(r.line, PlanErrorCode.SITE_COORDS_MISMATCH, "lat", "${r.lat},${r.lon}"))
                }
            }
        }
    }

    fun write(sites: List<SitePlan>): String = buildString {
        appendLine(Csv.row(HEADER))
        for (p in sites) {
            for (s in p.sectors) {
                appendLine(
                    Csv.row(
                        listOf(
                            p.code, p.name, p.lat, p.lon, p.mccMnc, s.label, s.rat, s.band, s.arfcn, s.pci,
                            s.azimuthDeg, s.hpbwDeg, s.mechTiltDeg, s.elecTiltDeg, s.heightM,
                        ),
                    ),
                )
            }
        }
    }
}
