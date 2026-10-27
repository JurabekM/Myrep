package uz.sectorverify.feature.survey.ui

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import javax.inject.Inject
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.survey.PreCheck
import uz.sectorverify.feature.survey.PreCheckInput
import uz.sectorverify.feature.survey.PreCheckResult
import uz.sectorverify.feature.survey.PreCheckSource
import uz.sectorverify.feature.survey.StartResult
import uz.sectorverify.feature.survey.SurveyLauncher
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SitePlan

data class PreCheckUi(val plan: SitePlan? = null, val result: PreCheckResult? = null, val startedSessionId: String? = null)

/** 3-ekran: har safar GNSS fix yoki cell skani kelganda tekshiruvlarni qayta baholaydi. */
@HiltViewModel
class PreCheckViewModel @Inject constructor(
    savedState: SavedStateHandle,
    private val plans: PlanRepository,
    private val settings: SettingsRepository,
    private val source: PreCheckSource,
    private val launcher: SurveyLauncher,
) : ViewModel() {
    val siteId: Long = checkNotNull(savedState.get<Long>(ARG_SITE_ID))
    private val mode: SessionMode = savedState.get<String>(ARG_MODE)?.let { SessionMode.valueOf(it) } ?: SessionMode.FULL
    private val _ui = MutableStateFlow(PreCheckUi())
    val ui: StateFlow<PreCheckUi> = _ui.asStateFlow()
    private var accuracy: Double? = null
    private val visible = HashSet<CellKey>()
    private var servingLte = false
    private var listeners: Job? = null

    init {
        refresh()
    }

    /** Ruxsat dialogi qaytgach yana chaqiring. */
    fun refresh() {
        viewModelScope.launch {
            val plan = plans.site(siteId)?.plan ?: return@launch
            _ui.value = _ui.value.copy(plan = plan)
            evaluate()
            listeners?.cancel()
            listeners = launch {
                launch {
                    source.fixes().collect {
                        accuracy = it.accM
                        evaluate()
                    }
                }
                val sub = _ui.value.result?.subscription?.subscriptionId ?: return@launch
                source.cells(sub).collect { batch ->
                    visible += batch.map { it.key }
                    servingLte = servingLte || batch.any { it.registered }
                    evaluate()
                }
            }
        }
    }

    private suspend fun evaluate() {
        val plan = _ui.value.plan ?: return
        val s = settings.current()
        val input = PreCheckInput(
            plan = plan,
            locationGranted = source.locationGranted(),
            phoneStateGranted = source.phoneStateGranted(),
            notificationsGranted = source.notificationsGranted(),
            sims = source.sims(),
            gpsEnabled = source.gpsEnabled(),
            gpsAccuracyM = accuracy,
            capabilities = s.capabilities,
            visibleCells = visible.toSet(),
            servingRatsLte = servingLte,
            trafficUrl = s.trafficUrl,
            config = s.effectiveConfig,
        )
        _ui.value = _ui.value.copy(result = PreCheck.evaluate(input))
    }

    fun start(appVersion: String) {
        val r = _ui.value.result ?: return
        if (!r.canStart) return
        viewModelScope.launch {
            listeners?.cancel()
            when (val res = launcher.start(siteId, mode, r.subscription, appVersion)) {
                is StartResult.Started -> _ui.value = _ui.value.copy(startedSessionId = res.sessionId)
                else -> evaluate()
            }
        }
    }

    fun consumeStarted() {
        _ui.value = _ui.value.copy(startedSessionId = null)
    }

    companion object {
        const val ARG_SITE_ID = "siteId"
        const val ARG_MODE = "mode"
    }
}
