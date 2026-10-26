package uz.sectorverify.feature.survey.ui

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.feature.survey.SurveyController
import uz.sectorverify.feature.survey.SurveyLauncher
import uz.sectorverify.feature.survey.SurveyState
import uz.sectorverify.model.SitePlan

/** Screen 4: reads the service state; "Tugatish" stops it, and the result screen opens when analysis is stored. */
@HiltViewModel
class LiveViewModel @Inject constructor(
    savedState: SavedStateHandle,
    controller: SurveyController,
    private val launcher: SurveyLauncher,
    private val sessions: SessionRepository,
) : ViewModel() {
    val sessionId: String = checkNotNull(savedState.get<String>(ARG_SESSION_ID))
    val state: StateFlow<SurveyState> = controller.state
    private val _plan = MutableStateFlow<SitePlan?>(null)
    val plan: StateFlow<SitePlan?> = _plan.asStateFlow()
    private val _stopping = MutableStateFlow(false)
    val stopping: StateFlow<Boolean> = _stopping.asStateFlow()

    init {
        viewModelScope.launch {
            _plan.value = sessions.plan(sessionId)
        }
    }

    fun finish() {
        _stopping.value = true
        launcher.stop()
    }

    companion object {
        const val ARG_SESSION_ID = "sessionId"
    }
}
