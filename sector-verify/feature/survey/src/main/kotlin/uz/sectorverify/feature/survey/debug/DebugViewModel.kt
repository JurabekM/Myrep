package uz.sectorverify.feature.survey.debug

import android.content.Context
import androidx.annotation.StringRes
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import java.io.File
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.SessionExporter
import uz.sectorverify.data.repo.SiteSummary
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.survey.R
import uz.sectorverify.feature.survey.StartResult
import uz.sectorverify.feature.survey.SurveyController
import uz.sectorverify.feature.survey.SurveyLauncher
import uz.sectorverify.feature.survey.SurveyState
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.SessionMode
import uz.sectorverify.telephony.DeviceCapabilityProbe
import uz.sectorverify.telephony.SubscriptionSelector
import uz.sectorverify.ui.util.Share

data class DebugUi(
    val probing: Boolean = false,
    val capabilities: DeviceCapabilities? = null,
    val lastZip: File? = null,
    @StringRes val messageRes: Int? = null,
    val messageArg: String = "",
    val lastSessionId: String? = null,
)

/** 2-bosqich vaqtinchalik debug ekrani (faqat debug build'larda). */
@HiltViewModel
class DebugViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val starter: SurveyLauncher,
    private val exporter: SessionExporter,
    private val settings: SettingsRepository,
    private val planRepo: PlanRepository,
    controller: SurveyController,
) : ViewModel() {
    val survey: StateFlow<SurveyState> = controller.state
    val sites: StateFlow<List<SiteSummary>> = planRepo.observeSites().stateIn(viewModelScope, SharingStarted.Eagerly, emptyList())
    private val _ui = MutableStateFlow(DebugUi())
    val ui: StateFlow<DebugUi> = _ui.asStateFlow()

    fun probe() {
        viewModelScope.launch {
            _ui.value = _ui.value.copy(probing = true)
            val sim = SubscriptionSelector.activeSims(context).firstOrNull()
            if (sim == null) {
                _ui.value = _ui.value.copy(probing = false, messageRes = R.string.debug_no_sim)
                return@launch
            }
            val caps = DeviceCapabilityProbe(context, sim.subscriptionId).run()
            settings.update { it.copy(capabilities = caps) }
            _ui.value = _ui.value.copy(probing = false, capabilities = caps)
        }
    }

    fun start(site: SiteSummary) {
        viewModelScope.launch {
            val plan = planRepo.site(site.id)?.plan ?: return@launch
            val sim = SubscriptionSelector.select(SubscriptionSelector.activeSims(context), plan.mccMnc)
            when (val r = starter.start(site.id, SessionMode.FULL, sim, appVersion())) {
                is StartResult.Started -> _ui.value = _ui.value.copy(lastSessionId = r.sessionId, messageRes = null)
                is StartResult.NoMatchingSim ->
                    _ui.value =
                        _ui.value.copy(messageRes = R.string.debug_no_matching_sim, messageArg = r.planMccMnc)
                StartResult.UnknownSite -> Unit
            }
        }
    }

    fun importPlan(uri: android.net.Uri) {
        viewModelScope.launch {
            val text = context.contentResolver.openInputStream(uri)?.use { it.readBytes().toString(Charsets.UTF_8) } ?: return@launch
            val r = planRepo.importCsv(text)
            _ui.value = if (r.ok) {
                _ui.value.copy(messageRes = R.string.debug_imported, messageArg = r.sites.size.toString())
            } else {
                _ui.value.copy(
                    messageRes = R.string.debug_import_errors,
                    messageArg = r.errors.take(MAX_ERRORS).joinToString("\n") {
                        it.messageUz()
                    },
                )
            }
        }
    }

    fun stop() = starter.stop()

    fun exportZip() {
        val id = survey.value.finishedSessionId ?: survey.value.sessionId ?: _ui.value.lastSessionId ?: return
        viewModelScope.launch {
            val s = settings.settings.first()
            val zip = exporter.export(id, Share.exportsDir(context), s.engineerName, s.capabilities)
            _ui.value = _ui.value.copy(lastZip = zip)
            Share.send(context, zip, "application/zip", "ZIP")
        }
    }

    private companion object {
        const val MAX_ERRORS = 5
    }

    private fun appVersion(): String = context.packageManager.getPackageInfo(context.packageName, 0).versionName ?: "?"
}
