package uz.sectorverify.feature.settings

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import javax.inject.Inject
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import uz.sectorverify.data.settings.AppTheme
import uz.sectorverify.data.settings.Settings
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.AnalysisPreset
import uz.sectorverify.telephony.DeviceCapabilityProbe
import uz.sectorverify.telephony.SubscriptionSelector
import uz.sectorverify.telephony.TrafficGenerator
import uz.sectorverify.ui.util.LocaleStore

/** Editable subset of [AnalysisConfig] shown as text fields. */
data class Thresholds(
    val rMaxM: String,
    val pathLossExponent: String,
    val minOverallCoverage: String,
    val minSectorCoverage: String,
    val passMaxErrDeg: String,
    val warnMaxErrDeg: String,
) {
    /** Applies the fields to [base]; returns the invalid field name on error. */
    fun applyTo(base: AnalysisConfig): Result<AnalysisConfig> {
        fun d(name: String, v: String) = v.replace(',', '.').toDoubleOrNull() ?: throw IllegalArgumentException(name)
        return runCatching {
            val c = base.copy(
                rMaxM = d("rMax", rMaxM),
                pathLossExponent = d("n", pathLossExponent),
                minOverallCoverage = d("coverage", minOverallCoverage),
                minSectorCoverage = d("sectorCoverage", minSectorCoverage),
                passMaxErrDeg = d("pass", passMaxErrDeg),
                warnMaxErrDeg = d("warn", warnMaxErrDeg),
            )
            val problems = c.validate() + listOfNotNull("pass < warn".takeIf { c.passMaxErrDeg >= c.warnMaxErrDeg })
            require(problems.isEmpty()) { problems.joinToString() }
            c
        }
    }

    companion object {
        fun of(c: AnalysisConfig) = Thresholds(
            c.rMaxM.toString(),
            c.pathLossExponent.toString(),
            c.minOverallCoverage.toString(),
            c.minSectorCoverage.toString(),
            c.passMaxErrDeg.toString(),
            c.warnMaxErrDeg.toString(),
        )
    }
}

sealed interface SettingsEvent {
    data object Saved : SettingsEvent

    data object ConfigImported : SettingsEvent

    data class Error(val detail: String) : SettingsEvent

    data object ProbeNoSim : SettingsEvent
}

@HiltViewModel
class SettingsViewModel @Inject constructor(
    @ApplicationContext private val context: Context,
    private val repo: SettingsRepository,
) : ViewModel() {
    private val localeStore = LocaleStore(context)
    val settings: StateFlow<Settings> = repo.settings.stateIn(viewModelScope, SharingStarted.Eagerly, Settings())
    private val _event = MutableStateFlow<SettingsEvent?>(null)
    val event: StateFlow<SettingsEvent?> = _event.asStateFlow()
    private val _probing = MutableStateFlow(false)
    val probing: StateFlow<Boolean> = _probing.asStateFlow()

    private fun update(f: (Settings) -> Settings) = viewModelScope.launch { repo.update(f) }

    fun setPreset(p: AnalysisPreset) = update { it.copy(preset = p, configOverride = null) }

    fun applyThresholds(t: Thresholds) {
        t.applyTo(settings.value.effectiveConfig)
            .onSuccess { c -> update { it.copy(configOverride = c) }.also { _event.value = SettingsEvent.Saved } }
            .onFailure { _event.value = SettingsEvent.Error(it.message.orEmpty()) }
    }

    fun resetToPreset() = update { it.copy(configOverride = null) }

    /** Calibration output of `sv-replay calibrate` (recommended-config.json). */
    fun importConfig(text: String) {
        runCatching { SvJson.parseConfig(text).also { c -> require(c.validate().isEmpty()) { c.validate().joinToString() } } }
            .onSuccess { c -> update { it.copy(configOverride = c) }.also { _event.value = SettingsEvent.ConfigImported } }
            .onFailure { _event.value = SettingsEvent.Error(it.message ?: it.javaClass.simpleName) }
    }

    /** Returns false (and keeps the old value) for a non-empty URL that is not plain https. */
    fun setTrafficUrl(url: String): Boolean {
        val ok = url.isBlank() || TrafficGenerator.isValidUrl(url.trim())
        if (ok) update { it.copy(trafficUrl = url.trim()) }
        return ok
    }

    fun setEngineer(name: String) = update { it.copy(engineerName = name.trim()) }

    fun setAppLanguage(tag: String) {
        localeStore.set(tag)
        update { it.copy(appLanguage = tag) }
    }

    fun setReportLanguage(tag: String) = update { it.copy(reportLanguage = tag) }

    fun setTheme(t: AppTheme) = update { it.copy(theme = t) }

    fun probe() {
        viewModelScope.launch {
            val sim = runCatching { SubscriptionSelector.activeSims(context).firstOrNull() }.getOrNull()
            if (sim == null) {
                _event.value = SettingsEvent.ProbeNoSim
                return@launch
            }
            _probing.value = true
            val caps = DeviceCapabilityProbe(context, sim.subscriptionId).run()
            repo.update { it.copy(capabilities = caps) }
            _probing.value = false
        }
    }

    fun consumeEvent() {
        _event.value = null
    }
}
