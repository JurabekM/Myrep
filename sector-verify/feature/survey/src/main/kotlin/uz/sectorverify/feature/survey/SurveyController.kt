package uz.sectorverify.feature.survey

import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Process-wide survey state shared by the foreground service (writer) and the UI (reader). */
@Singleton
class SurveyController @Inject constructor() {
    private val _state = MutableStateFlow(SurveyState())
    val state: StateFlow<SurveyState> = _state.asStateFlow()

    fun publish(s: SurveyState) {
        _state.value = s
    }

    fun finished(sessionId: String) {
        _state.value = _state.value.copy(running = false, finishedSessionId = sessionId)
    }

    fun reset() {
        _state.value = SurveyState()
    }
}
