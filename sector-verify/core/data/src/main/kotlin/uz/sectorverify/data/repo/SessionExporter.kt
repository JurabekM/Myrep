package uz.sectorverify.data.repo

import java.io.File
import javax.inject.Inject
import uz.sectorverify.format.SessionExport
import uz.sectorverify.format.SessionZip
import uz.sectorverify.model.DeviceCapabilities

/** Builds the session ZIP (§5.4) from stored data; [reportJson] and [reportPdf] are added once a report exists. */
class SessionExporter @Inject constructor(private val sessions: SessionRepository, private val plans: PlanRepository) {
    suspend fun export(
        sessionId: String,
        dir: File,
        engineer: String?,
        capabilities: DeviceCapabilities?,
        reportJson: String? = null,
        reportPdf: ByteArray? = null,
    ): File {
        val meta = requireNotNull(sessions.meta(sessionId, engineer)) { "unknown session $sessionId" }
        val site = requireNotNull(plans.siteByCode(meta.siteCode)) { "unknown site ${meta.siteCode}" }
        val export =
            SessionExport(site.plan, sessions.samples(sessionId), sessions.fixes(sessionId), meta, reportJson, reportPdf, capabilities)
        dir.mkdirs()
        val file = File(dir, "${meta.siteCode}_${sessionId.take(SHORT_ID)}.zip")
        file.outputStream().buffered().use { SessionZip.write(export, it) }
        return file
    }

    private companion object {
        const val SHORT_ID = 8
    }
}
