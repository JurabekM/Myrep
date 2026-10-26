package uz.sectorverify.feature.report

import android.annotation.SuppressLint
import android.content.Context
import android.content.res.Configuration
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import java.util.Locale
import javax.inject.Inject
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import uz.sectorverify.data.db.ReportEntity
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.ReportRepository
import uz.sectorverify.data.repo.SessionExporter
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.format.ReportIntegrity
import uz.sectorverify.format.ReportJson
import uz.sectorverify.format.ReportSigner
import uz.sectorverify.ui.util.Share

data class GeneratedReport(val pdf: File, val json: File, val zip: File, val sha256: String, val pages: Int)

/** report.json (signed) → PDF in the report language → session ZIP; stored as a `report` row (§5.4, §8.2, §8.3). */
class ReportGenerator @Inject constructor(
    @ApplicationContext private val context: Context,
    private val sessions: SessionRepository,
    private val settings: SettingsRepository,
    private val reports: ReportRepository,
    private val exporter: SessionExporter,
    private val signer: ReportSigner,
    private val clock: Clock,
) {
    @SuppressLint("AppBundleLocaleChanges") // :app disables bundle language splits (all languages ship).
    suspend fun generate(sessionId: String): GeneratedReport = withContext(Dispatchers.Default) {
        val s = settings.current()
        val stored = requireNotNull(sessions.result(sessionId)) { "no session $sessionId" }
        val result = requireNotNull(stored.full) { "session $sessionId has no analysis" }
        val meta = requireNotNull(sessions.meta(sessionId, s.engineerName))
        val plan = requireNotNull(sessions.plan(sessionId)) { "no plan for $sessionId" }
        val sealed = ReportIntegrity.seal(ReportJson.build(plan, meta, result), signer)
        val integrity = sealed.getValue(ReportJson.INTEGRITY).jsonObject
        val sha = integrity.getValue("sha256").jsonPrimitive.content
        val sig = integrity.getValue("signature").jsonPrimitive.content
        val jsonText = ReportJson.toText(sealed)

        val locale = Locale.forLanguageTag(s.reportLanguage)
        val localized = context.createConfigurationContext(Configuration(context.resources.configuration).apply { setLocale(locale) })
        val writer = PdfReportWriter(localized, locale)
        val pdfBytes = writer.write(PdfInput(plan, meta, result, sessions.fixes(sessionId), sha, sig))

        val dir = File(Share.exportsDir(context), sessionId).apply { mkdirs() }
        val json = File(dir, "report.json").apply { writeText(jsonText) }
        val pdf = File(dir, "${meta.siteCode}_report.pdf").apply { writeBytes(pdfBytes) }
        val zip = exporter.export(sessionId, dir, s.engineerName, s.capabilities, jsonText, pdfBytes)
        reports.save(ReportEntity(0, sessionId, pdf.path, json.path, zip.path, sha, sig, clock.nowUtcMs()))
        GeneratedReport(pdf, json, zip, sha, writer.pages)
    }
}
