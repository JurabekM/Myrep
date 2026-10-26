package uz.sectorverify.feature.plan

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.repo.SiteSummary
import uz.sectorverify.format.PlanError

data class ImportOutcome(val imported: Int, val errors: List<PlanError>)

data class ResumeOffer(val sessionId: String, val siteCode: String, val samples: Int)

/** Resumes or abandons a RUNNING session; implemented by :feature:survey, bound in :app. */
interface SessionResumer {
    /** False when the survey cannot start (location permission missing). */
    fun resume(sessionId: String): Boolean

    suspend fun abandon(sessionId: String)
}

@OptIn(ExperimentalCoroutinesApi::class)
@HiltViewModel
class SitesViewModel @Inject constructor(
    private val plans: PlanRepository,
    private val sessions: SessionRepository,
    private val resumer: SessionResumer,
) : ViewModel() {
    private val _query = MutableStateFlow("")
    val query: StateFlow<String> = _query.asStateFlow()
    val sites: StateFlow<List<SiteSummary>> = _query.flatMapLatest { plans.observeSites(it) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(STOP_MS), emptyList())
    private val _import = MutableStateFlow<ImportOutcome?>(null)
    val import: StateFlow<ImportOutcome?> = _import.asStateFlow()
    private val _resume = MutableStateFlow<ResumeOffer?>(null)
    val resume: StateFlow<ResumeOffer?> = _resume.asStateFlow()

    init {
        viewModelScope.launch { checkRunning() }
    }

    /** §7: a session left RUNNING by a killed process is offered for resumption. */
    suspend fun checkRunning() {
        val s = sessions.running().firstOrNull() ?: return
        val code = plans.site(s.siteId)?.plan?.code ?: return
        _resume.value = ResumeOffer(s.id, code, sessions.sampleCount(s.id))
    }

    fun setQuery(q: String) = _query.update { q }

    fun importCsv(text: String) {
        viewModelScope.launch {
            val r = plans.importCsv(text)
            _import.value = ImportOutcome(r.sites.size, r.errors)
        }
    }

    fun dismissImport() = _import.update { null }

    private val _resumeBlocked = MutableStateFlow(false)
    val resumeBlocked: StateFlow<Boolean> = _resumeBlocked.asStateFlow()

    /** Returns the resumed session id, or null when it could not start (the offer stays visible). */
    fun resume(): String? {
        val offer = _resume.value ?: return null
        if (!resumer.resume(offer.sessionId)) {
            _resumeBlocked.value = true
            return null
        }
        _resume.value = null
        _resumeBlocked.value = false
        return offer.sessionId
    }

    fun abandon() {
        val offer = _resume.value ?: return
        viewModelScope.launch {
            resumer.abandon(offer.sessionId)
            _resume.value = null
        }
    }

    private companion object {
        const val STOP_MS = 5_000L
    }
}
