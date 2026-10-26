package uz.sectorverify.feature.report

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.sectorverify.data.repo.ReportRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.repo.StoredResult
import uz.sectorverify.model.SitePlan

data class ResultUi(val loading: Boolean = true, val stored: StoredResult? = null, val plan: SitePlan? = null, val siteId: Long? = null)

/** Screen 5 — result of the final analysis. */
@HiltViewModel
class ResultViewModel @Inject constructor(
    savedState: SavedStateHandle,
    private val sessions: SessionRepository,
) : ViewModel() {
    val sessionId: String = checkNotNull(savedState.get<String>(ARG_SESSION_ID))
    private val _ui = MutableStateFlow(ResultUi())
    val ui: StateFlow<ResultUi> = _ui.asStateFlow()

    init {
        viewModelScope.launch {
            val stored = sessions.result(sessionId)
            _ui.value = ResultUi(false, stored, sessions.plan(sessionId), stored?.session?.siteId)
        }
    }

    companion object {
        const val ARG_SESSION_ID = "sessionId"
    }
}

sealed interface ReportState {
    data object Idle : ReportState

    data object Working : ReportState

    data class Ready(val pdf: File, val zip: File, val sha256: String) : ReportState

    data class Failed(val reason: String) : ReportState
}

/** Screen 6 — report: generate, view, share PDF, export ZIP. */
@HiltViewModel
class ReportViewModel @Inject constructor(
    savedState: SavedStateHandle,
    private val generator: ReportGenerator,
    private val reports: ReportRepository,
) : ViewModel() {
    val sessionId: String = checkNotNull(savedState.get<String>(ResultViewModel.ARG_SESSION_ID))
    private val _state = MutableStateFlow<ReportState>(ReportState.Idle)
    val state: StateFlow<ReportState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            reports.latest(sessionId)?.let { r ->
                val pdf = File(r.pdfPath)
                val zip = File(r.zipPath)
                if (pdf.exists() && zip.exists()) _state.value = ReportState.Ready(pdf, zip, r.sha256)
            }
        }
    }

    fun generate() {
        _state.value = ReportState.Working
        viewModelScope.launch {
            _state.value = runCatching { generator.generate(sessionId) }
                .fold({ ReportState.Ready(it.pdf, it.zip, it.sha256) }, { ReportState.Failed(it.message ?: it.javaClass.simpleName) })
        }
    }
}
