package uz.sectorverify.data.repo

import java.io.File
import javax.inject.Inject
import uz.sectorverify.format.SessionExport
import uz.sectorverify.format.SessionZip
import uz.sectorverify.model.DeviceCapabilities

/** Saqlangan ma'lumotdan sessiya ZIP'ini (§5.4) yig'adi; [reportJson] va [reportPdf] hisobot paydo bo'lgach qo'shiladi. */
class SessionExporter @Inject constructor(private val sessions: SessionRepository) {
    suspend fun export(
        sessionId: String,
        dir: File,
        engineer: String?,
        capabilities: DeviceCapabilities?,
        reportJson: String? = null,
        reportPdf: ByteArray? = null,
    ): File {
        val meta = requireNotNull(sessions.meta(sessionId, engineer)) { "unknown session $sessionId" }
        val plan = requireNotNull(sessions.plan(sessionId)) { "unknown site ${meta.siteCode}" }
        val export =
            SessionExport(plan, sessions.samples(sessionId), sessions.fixes(sessionId), meta, reportJson, reportPdf, capabilities)
        dir.mkdirs()
        val file = File(dir, "${meta.siteCode}_${sessionId.take(SHORT_ID)}.zip")
        file.outputStream().buffered().use { SessionZip.write(export, it) }
        return file
    }

    private companion object {
        const val SHORT_ID = 8
    }
}
