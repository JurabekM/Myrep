package uz.sectorverify.feature.settings

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.sectorverify.data.settings.AppTheme
import uz.sectorverify.model.AnalysisPreset
import uz.sectorverify.ui.components.MinTouch
import uz.sectorverify.ui.components.PrimaryButton
import uz.sectorverify.ui.components.SecondaryButton
import uz.sectorverify.ui.components.SectionTitle
import uz.sectorverify.ui.theme.LocalSvPalette
import uz.sectorverify.ui.util.LocaleStore

/** Screen 7 — settings (§8.1). [onLanguageChanged] recreates the activity. */
@Composable
fun SettingsRoute(onLanguageChanged: () -> Unit, extra: @Composable () -> Unit = {}, vm: SettingsViewModel = hiltViewModel()) {
    val s by vm.settings.collectAsStateWithLifecycle()
    val event by vm.event.collectAsStateWithLifecycle()
    val probing by vm.probing.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val p = LocalSvPalette.current
    val pickConfig = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { u -> context.contentResolver.openInputStream(u)?.use { vm.importConfig(it.readBytes().toString(Charsets.UTF_8)) } }
    }
    var thresholds by remember(s.effectiveConfig) { mutableStateOf(Thresholds.of(s.effectiveConfig)) }
    var traffic by remember(s.trafficUrl) { mutableStateOf(s.trafficUrl) }
    var trafficOk by remember { mutableStateOf(true) }
    var engineer by remember(s.engineerName) { mutableStateOf(s.engineerName) }
    LaunchedEffect(event) { if (event != null) kotlinx.coroutines.delay(EVENT_MS).also { vm.consumeEvent() } }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Text(stringResource(R.string.settings_title), style = MaterialTheme.typography.headlineMedium)
        event?.let { e ->
            val text = when (e) {
                SettingsEvent.Saved -> stringResource(R.string.settings_saved)
                SettingsEvent.ConfigImported -> stringResource(R.string.settings_config_imported)
                SettingsEvent.ProbeNoSim -> stringResource(R.string.settings_probe_no_sim)
                is SettingsEvent.Error -> stringResource(R.string.settings_config_error, e.detail)
            }
            Text(
                text,
                color = if (e is SettingsEvent.Error ||
                    e is SettingsEvent.ProbeNoSim
                ) {
                    p.danger
                } else {
                    p.ok
                },
                modifier = Modifier.testTag("event"),
            )
        }

        SectionTitle(stringResource(R.string.settings_preset))
        Choice(AnalysisPreset.URBAN, s.preset, R.string.preset_urban, vm::setPreset)
        Choice(AnalysisPreset.SUBURBAN, s.preset, R.string.preset_suburban, vm::setPreset)
        Choice(AnalysisPreset.RURAL, s.preset, R.string.preset_rural, vm::setPreset)

        SectionTitle(stringResource(R.string.settings_thresholds))
        if (s.configOverride != null) Text(stringResource(R.string.settings_override_active), color = p.warn)
        NumberField(R.string.th_rmax, thresholds.rMaxM) { thresholds = thresholds.copy(rMaxM = it) }
        NumberField(R.string.th_n, thresholds.pathLossExponent) { thresholds = thresholds.copy(pathLossExponent = it) }
        NumberField(R.string.th_cov, thresholds.minOverallCoverage) { thresholds = thresholds.copy(minOverallCoverage = it) }
        NumberField(R.string.th_sector_cov, thresholds.minSectorCoverage) { thresholds = thresholds.copy(minSectorCoverage = it) }
        NumberField(R.string.th_pass, thresholds.passMaxErrDeg) { thresholds = thresholds.copy(passMaxErrDeg = it) }
        NumberField(R.string.th_warn, thresholds.warnMaxErrDeg) { thresholds = thresholds.copy(warnMaxErrDeg = it) }
        PrimaryButton(stringResource(R.string.th_apply), { vm.applyThresholds(thresholds) }, Modifier.testTag("apply"))
        SecondaryButton(stringResource(R.string.settings_reset), vm::resetToPreset)
        SecondaryButton(stringResource(R.string.settings_import_config), { pickConfig.launch("*/*") })

        SectionTitle(stringResource(R.string.settings_traffic))
        OutlinedTextField(
            value = traffic,
            onValueChange = {
                traffic = it
                trafficOk = vm.setTrafficUrl(it)
            },
            isError = !trafficOk,
            supportingText = { if (!trafficOk) Text(stringResource(R.string.settings_traffic_invalid)) },
            singleLine = true,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Uri),
            modifier = Modifier.fillMaxWidth().testTag("traffic"),
        )
        SectionTitle(stringResource(R.string.settings_engineer))
        OutlinedTextField(
            value = engineer,
            onValueChange = {
                engineer = it
                vm.setEngineer(it)
            },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        SectionTitle(stringResource(R.string.settings_app_language))
        for (tag in LocaleStore.SUPPORTED) {
            Choice(tag, s.appLanguage, langRes(tag)) {
                vm.setAppLanguage(it)
                onLanguageChanged()
            }
        }
        SectionTitle(stringResource(R.string.settings_report_language))
        for (tag in LocaleStore.SUPPORTED) Choice(tag, s.reportLanguage, langRes(tag), vm::setReportLanguage)

        SectionTitle(stringResource(R.string.settings_theme))
        Choice(AppTheme.DARK, s.theme, R.string.theme_dark, vm::setTheme)
        Choice(AppTheme.LIGHT, s.theme, R.string.theme_light, vm::setTheme)
        Choice(AppTheme.SUN, s.theme, R.string.theme_sun, vm::setTheme)

        SecondaryButton(
            stringResource(if (probing) R.string.settings_probe_running else R.string.settings_probe),
            vm::probe,
            enabled = !probing,
        )
        s.capabilities?.let { c ->
            fun yn(b: Boolean) = if (b) R.string.yes else R.string.no
            Text(
                stringResource(
                    R.string.settings_probe_result,
                    c.deviceModel,
                    "%.2f".format(c.measuredRateHz),
                    stringResource(yn(c.neighborRsrpReported)),
                    stringResource(yn(c.timingAdvanceReported)),
                    stringResource(yn(c.nrSaFieldsReported)),
                ),
                color = p.inkMuted,
            )
        }
        extra()
    }
}

private fun langRes(tag: String) = when (tag) {
    "ru" -> R.string.lang_ru
    "en" -> R.string.lang_en
    else -> R.string.lang_uz
}

@Composable
private fun <T> Choice(value: T, selected: T, label: Int, onSelect: (T) -> Unit) {
    Row(
        Modifier.fillMaxWidth().heightIn(min = MinTouch).selectable(selected = value == selected, role = Role.RadioButton) {
            onSelect(value)
        },
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected = value == selected, onClick = null)
        Text(stringResource(label), Modifier.padding(start = 12.dp))
    }
}

@Composable
private fun NumberField(label: Int, value: String, onChange: (String) -> Unit) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(stringResource(label)) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
        modifier = Modifier.fillMaxWidth(),
    )
}

private const val EVENT_MS = 3000L
