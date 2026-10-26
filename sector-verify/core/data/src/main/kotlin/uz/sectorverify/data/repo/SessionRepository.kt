package uz.sectorverify.data.repo

import java.util.UUID
import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import uz.sectorverify.data.BatchSink
import uz.sectorverify.data.db.RawDao
import uz.sectorverify.data.db.ResultDao
import uz.sectorverify.data.db.SessionDao
import uz.sectorverify.data.db.SessionEntity
import uz.sectorverify.data.db.SiteDao
import uz.sectorverify.data.toEntity
import uz.sectorverify.data.toModel
import uz.sectorverify.format.SessionMeta
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.Finding
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.SectorResult
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionResult
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.SitePlan

data class NewSession(
    val siteId: Long,
    val mode: SessionMode,
    val deviceModel: String,
    val apiLevel: Int,
    val baseband: String?,
    val appVersion: String,
    val algoVersion: String,
    val config: AnalysisConfig,
    val subscriptionId: Int?,
)

data class StoredResult(val session: SessionEntity, val sectors: List<SectorResult>, val findings: List<Finding>) {
    /** Complete analysis output; null for sessions analysed before result_json existed. */
    val full: SessionResult? get() = session.resultJson?.let { SvJson.compact.decodeFromString(SessionResult.serializer(), it) }
}

interface SessionRepository {
    suspend fun create(s: NewSession): String

    fun sink(sessionId: String): BatchSink

    suspend fun finish(sessionId: String, status: SessionStatus)

    suspend fun setMeasuredRate(sessionId: String, rateHz: Double)

    /** Sessions left RUNNING by a killed process (§7: offer to resume). */
    suspend fun running(): List<SessionEntity>

    suspend fun session(sessionId: String): SessionEntity?

    /** Sessiya yaratilgandagi reja (ADR-016); eski yozuvlar uchun saytning joriy rejasi. */
    suspend fun plan(sessionId: String): SitePlan?

    fun observe(sessionId: String): Flow<SessionEntity?>

    fun observeForSite(siteId: Long): Flow<List<SessionEntity>>

    suspend fun samples(sessionId: String): List<CellSample>

    suspend fun fixes(sessionId: String): List<GnssFix>

    suspend fun sampleCount(sessionId: String): Int

    suspend fun saveResult(sessionId: String, result: SessionResult, config: AnalysisConfig)

    suspend fun result(sessionId: String): StoredResult?

    suspend fun meta(sessionId: String, engineer: String?): SessionMeta?
}

class RoomSessionRepository @Inject constructor(
    private val sessions: SessionDao,
    private val raw: RawDao,
    private val results: ResultDao,
    private val sites: SiteDao,
    private val clock: Clock,
) : SessionRepository {
    override suspend fun create(s: NewSession): String {
        val id = UUID.randomUUID().toString()
        val plan = currentPlan(s.siteId)
        sessions.insert(
            SessionEntity(
                id = id,
                siteId = s.siteId,
                mode = s.mode,
                startedAt = clock.nowUtcMs(),
                endedAt = null,
                deviceModel = s.deviceModel,
                apiLevel = s.apiLevel,
                baseband = s.baseband,
                appVersion = s.appVersion,
                algoVersion = s.algoVersion,
                configJson = SvJson.compact.encodeToString(AnalysisConfig.serializer(), s.config),
                measuredRateHz = null,
                status = SessionStatus.RUNNING,
                subscriptionId = s.subscriptionId,
                planJson = plan?.let { SvJson.compact.encodeToString(SitePlan.serializer(), it) },
            ),
        )
        return id
    }

    override fun sink(sessionId: String) = BatchSink { s, f ->
        raw.insertBatch(s.map { it.toEntity(sessionId) }, f.map { it.toEntity(sessionId) })
    }

    override suspend fun finish(sessionId: String, status: SessionStatus) = sessions.setStatus(sessionId, status, clock.nowUtcMs())

    override suspend fun setMeasuredRate(sessionId: String, rateHz: Double) = sessions.setRate(sessionId, rateHz)

    override suspend fun running(): List<SessionEntity> = sessions.running()

    override suspend fun session(sessionId: String): SessionEntity? = sessions.byId(sessionId)

    override suspend fun plan(sessionId: String): SitePlan? {
        val s = sessions.byId(sessionId) ?: return null
        return s.planJson?.let { SvJson.compact.decodeFromString(SitePlan.serializer(), it) } ?: currentPlan(s.siteId)
    }

    private suspend fun currentPlan(siteId: Long): SitePlan? = sites.byId(siteId)?.toModel(sites.sectors(siteId))

    override fun observe(sessionId: String): Flow<SessionEntity?> = sessions.observe(sessionId)

    override fun observeForSite(siteId: Long): Flow<List<SessionEntity>> = sessions.observeForSite(siteId)

    override suspend fun samples(sessionId: String): List<CellSample> = raw.samples(sessionId).map { it.toModel() }

    override suspend fun fixes(sessionId: String): List<GnssFix> = raw.fixes(sessionId).map { it.toModel() }

    override suspend fun sampleCount(sessionId: String): Int = raw.sampleCount(sessionId)

    override suspend fun saveResult(sessionId: String, result: SessionResult, config: AnalysisConfig) {
        val session = requireNotNull(sessions.byId(sessionId)) { "unknown session $sessionId" }
        val sectorIds = sites.sectors(session.siteId).associate { Triple(it.rat, it.arfcn, it.pci) to it.id }
        val rows = result.sectors.map { it.toEntity(sessionId, sectorIds[Triple(it.key.rat, it.key.arfcn, it.key.pci)]) }
        results.replace(sessionId, rows, result.findings.map { it.toEntity(sessionId) })
        val configJson = SvJson.compact.encodeToString(AnalysisConfig.serializer(), config)
        val resultJson = SvJson.compact.encodeToString(SessionResult.serializer(), result)
        sessions.setResult(sessionId, result.verdict, result.overallCoverage * PERCENT, configJson, resultJson)
    }

    override suspend fun result(sessionId: String): StoredResult? {
        val s = sessions.byId(sessionId) ?: return null
        return StoredResult(s, results.results(sessionId).map { it.toModel() }, results.findings(sessionId).map { it.toModel() })
    }

    override suspend fun meta(sessionId: String, engineer: String?): SessionMeta? {
        val s = sessions.byId(sessionId) ?: return null
        val plan = plan(sessionId) ?: return null
        return SessionMeta(
            id = s.id,
            siteCode = plan.code,
            mode = s.mode,
            startedAtUtcMs = s.startedAt,
            endedAtUtcMs = s.endedAt,
            deviceModel = s.deviceModel,
            apiLevel = s.apiLevel,
            baseband = s.baseband,
            appVersion = s.appVersion,
            algoVersion = s.algoVersion,
            measuredRateHz = s.measuredRateHz,
            status = s.status,
            engineer = engineer,
            config = SvJson.parseConfig(s.configJson),
        )
    }

    private companion object {
        const val PERCENT = 100.0
    }
}
