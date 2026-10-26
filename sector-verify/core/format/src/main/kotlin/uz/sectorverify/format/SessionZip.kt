package uz.sectorverify.format

import java.io.ByteArrayOutputStream
import java.io.InputStream
import java.io.OutputStream
import java.util.zip.ZipEntry
import java.util.zip.ZipInputStream
import java.util.zip.ZipOutputStream
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.SitePlan

/** Contents of a session export ZIP (§5.4); the same ZIP is the input of :tools:replay. */
data class SessionExport(
    val plan: SitePlan,
    val samples: List<CellSample>,
    val fixes: List<GnssFix>,
    val meta: SessionMeta,
    val reportJson: String? = null,
    val reportPdf: ByteArray? = null,
    val capabilities: DeviceCapabilities? = null,
) {
    override fun equals(other: Any?): Boolean = other is SessionExport &&
        plan == other.plan &&
        samples == other.samples &&
        fixes == other.fixes &&
        meta == other.meta &&
        reportJson == other.reportJson &&
        capabilities == other.capabilities &&
        (reportPdf?.contentEquals(other.reportPdf ?: ByteArray(0)) ?: (other.reportPdf == null))

    override fun hashCode(): Int = plan.hashCode() * 31 + meta.hashCode()
}

object SessionZip {
    const val PLAN = "plan.csv"
    const val SAMPLES = "cell_samples.csv"
    const val FIXES = "gnss_fixes.csv"
    const val SESSION = "session.json"
    const val REPORT_JSON = "report.json"
    const val REPORT_PDF = "report.pdf"
    const val CAPABILITIES = "capabilities.json"

    fun write(export: SessionExport, out: OutputStream) {
        ZipOutputStream(out).use { zip ->
            fun text(name: String, body: String) = bytes(zip, name, body.toByteArray(Charsets.UTF_8))
            text(PLAN, PlanCsv.write(listOf(export.plan)))
            text(SAMPLES, buildString { SessionCsv.writeSamples(export.samples, this) })
            text(FIXES, buildString { SessionCsv.writeFixes(export.fixes, this) })
            text(SESSION, SvJson.pretty.encodeToString(SessionMeta.serializer(), export.meta))
            export.reportJson?.let { text(REPORT_JSON, it) }
            export.reportPdf?.let { bytes(zip, REPORT_PDF, it) }
            export.capabilities?.let { text(CAPABILITIES, SvJson.pretty.encodeToString(DeviceCapabilities.serializer(), it)) }
        }
    }

    fun toBytes(export: SessionExport): ByteArray = ByteArrayOutputStream().also { write(export, it) }.toByteArray()

    fun read(input: InputStream): SessionExport {
        val entries = HashMap<String, ByteArray>()
        ZipInputStream(input).use { zip ->
            var e = zip.nextEntry
            while (e != null) {
                if (!e.isDirectory) entries[e.name.substringAfterLast('/')] = zip.readBytes()
                e = zip.nextEntry
            }
        }
        fun text(name: String) = entries[name]?.toString(Charsets.UTF_8)
        fun need(name: String) = requireNotNull(text(name)) { "ZIP ichida $name yo'q" }
        val plans = PlanCsv.parse(need(PLAN))
        require(plans.ok && plans.sites.size == 1) { "plan.csv xato: ${plans.errors.joinToString { it.messageUz() }}" }
        return SessionExport(
            plan = plans.sites.single(),
            samples = SessionCsv.readSamples(need(SAMPLES)),
            fixes = SessionCsv.readFixes(need(FIXES)),
            meta = SvJson.compact.decodeFromString(SessionMeta.serializer(), need(SESSION)),
            reportJson = text(REPORT_JSON),
            reportPdf = entries[REPORT_PDF],
            capabilities = text(CAPABILITIES)?.let { SvJson.compact.decodeFromString(DeviceCapabilities.serializer(), it) },
        )
    }

    private fun bytes(zip: ZipOutputStream, name: String, body: ByteArray) {
        zip.putNextEntry(ZipEntry(name))
        zip.write(body)
        zip.closeEntry()
    }
}
