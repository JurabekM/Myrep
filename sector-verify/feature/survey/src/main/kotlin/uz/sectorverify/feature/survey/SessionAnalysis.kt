package uz.sectorverify.feature.survey

import javax.inject.Inject
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import uz.sectorverify.analysis.SessionAnalyzer
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.SessionResult

/** Final analysis (§6, full bootstrap) on Dispatchers.Default; the result and the config used are stored. */
class SessionAnalysis(
    private val sessions: SessionRepository,
    private val plans: PlanRepository,
    private val dispatcher: CoroutineDispatcher,
) {
    @Inject constructor(sessions: SessionRepository, plans: PlanRepository) : this(sessions, plans, Dispatchers.Default)

    suspend fun analyze(sessionId: String, override: AnalysisConfig? = null): SessionResult {
        val session = requireNotNull(sessions.session(sessionId)) { "unknown session $sessionId" }
        val plan = requireNotNull(plans.site(session.siteId)) { "unknown site ${session.siteId}" }.plan
        val config = override ?: SvJson.parseConfig(session.configJson)
        val samples = sessions.samples(sessionId)
        val fixes = sessions.fixes(sessionId)
        val result = withContext(dispatcher) { SessionAnalyzer(config).analyze(plan, samples, fixes) }
        sessions.saveResult(sessionId, result, config)
        return result
    }
}
