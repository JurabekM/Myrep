package uz.sectorverify.feature.survey.ui

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.sectorverify.analysis.LiveCell
import uz.sectorverify.feature.survey.CheckId
import uz.sectorverify.feature.survey.CheckItem
import uz.sectorverify.feature.survey.CheckStatus
import uz.sectorverify.feature.survey.R
import uz.sectorverify.feature.survey.SurveyState
import uz.sectorverify.feature.survey.runtimePermissions
import uz.sectorverify.model.SitePlan
import uz.sectorverify.telephony.TrafficStatus
import uz.sectorverify.ui.components.Card
import uz.sectorverify.ui.components.CoverageRadar
import uz.sectorverify.ui.components.PrimaryButton
import uz.sectorverify.ui.components.SecondaryButton
import uz.sectorverify.ui.components.SectionTitle
import uz.sectorverify.ui.components.labelRes
import uz.sectorverify.ui.components.verdictColor
import uz.sectorverify.ui.theme.LocalSvPalette

/** 3-ekran — oldindan tekshiruv (§8.1). */
@Composable
fun PreCheckRoute(onStarted: (String) -> Unit, vm: PreCheckViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val context = LocalContext.current
    var askedOnce by rememberSaveable { mutableStateOf(false) }
    val permissions = rememberLauncherForActivityResult(ActivityResultContracts.RequestMultiplePermissions()) {
        askedOnce = true
        vm.refresh()
    }
    LaunchedEffect(ui.startedSessionId) {
        ui.startedSessionId?.let {
            vm.consumeStarted()
            onStarted(it)
        }
    }
    val version = context.packageManager.getPackageInfo(context.packageName, 0).versionName.orEmpty()
    PreCheckScreen(
        plan = ui.plan,
        items = ui.result?.items.orEmpty(),
        canStart = ui.result?.canStart == true,
        onPermissions = {
            permissions.launch(runtimePermissions())
        },
        onStart = { vm.start(version) },
        showOpenSettings = askedOnce && ui.result?.items?.any { it.id == CheckId.PERMISSIONS && it.status == CheckStatus.BLOCK } == true,
        onOpenSettings = {
            context.startActivity(
                Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", context.packageName, null))
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK),
            )
        },
    )
}

@Composable
fun PreCheckScreen(
    plan: SitePlan?,
    items: List<CheckItem>,
    canStart: Boolean,
    onPermissions: () -> Unit,
    onStart: () -> Unit,
    showOpenSettings: Boolean = false,
    onOpenSettings: () -> Unit = {},
) {
    val p = LocalSvPalette.current
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Text(stringResource(R.string.precheck_title, plan?.code.orEmpty()), style = MaterialTheme.typography.headlineSmall) }
        items(items, key = { it.id }) { item ->
            Card(Modifier.testTag("check-${item.id}")) {
                val color = when (item.status) {
                    CheckStatus.OK -> p.ok
                    CheckStatus.WARN -> p.warn
                    CheckStatus.BLOCK -> p.danger
                }
                val statusText = stringResource(item.status.labelRes())
                Box(Modifier.size(16.dp).background(color, CircleShape).semantics { contentDescription = statusText })
                Column(Modifier.weight(1f)) {
                    Text(stringResource(item.id.titleRes()), style = MaterialTheme.typography.titleSmall)
                    Text(checkDetail(item), color = p.inkMuted, style = MaterialTheme.typography.bodySmall)
                }
            }
        }
        val needsPermissions = items.any { (it.id == CheckId.PERMISSIONS || it.id == CheckId.NOTIFICATIONS) && it.status != CheckStatus.OK }
        if (needsPermissions) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(stringResource(R.string.perm_why_location), style = MaterialTheme.typography.bodySmall)
                    Text(stringResource(R.string.perm_why_phone), style = MaterialTheme.typography.bodySmall)
                    Text(stringResource(R.string.perm_why_notifications), style = MaterialTheme.typography.bodySmall)
                }
            }
            item { SecondaryButton(stringResource(R.string.precheck_permissions), onPermissions) }
        }
        if (showOpenSettings) {
            item { Text(stringResource(R.string.perm_denied), color = p.danger) }
            item { SecondaryButton(stringResource(R.string.perm_open_settings), onOpenSettings) }
        }
        if (!canStart) item { Text(stringResource(R.string.precheck_blocked), color = p.danger) }
        item { PrimaryButton(stringResource(R.string.precheck_start), onStart, Modifier.testTag("start"), enabled = canStart) }
    }
}

private fun CheckStatus.labelRes() = when (this) {
    CheckStatus.OK -> R.string.check_status_ok
    CheckStatus.WARN -> R.string.check_status_warn
    CheckStatus.BLOCK -> R.string.check_status_block
}

private fun CheckId.titleRes() = when (this) {
    CheckId.PERMISSIONS -> R.string.check_permissions
    CheckId.NOTIFICATIONS -> R.string.check_notifications
    CheckId.SIM -> R.string.check_sim
    CheckId.NETWORK_MODE -> R.string.check_network
    CheckId.GPS -> R.string.check_gps
    CheckId.GPS_ACCURACY -> R.string.check_gps_accuracy
    CheckId.CAPABILITIES -> R.string.check_capabilities
    CheckId.PLANNED_CELLS -> R.string.check_planned_cells
    CheckId.TRAFFIC -> R.string.check_traffic
}

@Composable
private fun checkDetail(item: CheckItem): String {
    val ok = item.status == CheckStatus.OK
    return when (item.id) {
        CheckId.PERMISSIONS -> stringResource(if (ok) R.string.check_permissions_ok else R.string.check_permissions_bad)
        CheckId.NOTIFICATIONS -> stringResource(if (ok) R.string.check_notifications_ok else R.string.check_notifications_bad)
        CheckId.SIM -> if (ok) stringResource(R.string.check_sim_ok, item.args[1]) else stringResource(R.string.check_sim_bad, item.args[0])
        CheckId.NETWORK_MODE -> stringResource(if (ok) R.string.check_network_ok else R.string.check_network_bad)
        CheckId.GPS -> stringResource(if (ok) R.string.check_gps_ok else R.string.check_gps_bad)
        CheckId.GPS_ACCURACY -> stringResource(R.string.check_gps_accuracy_value, item.args[0], item.args[1])
        CheckId.CAPABILITIES -> stringResource(if (ok) R.string.check_capabilities_ok else R.string.check_capabilities_bad, item.args[0])
        CheckId.PLANNED_CELLS -> stringResource(R.string.check_planned_cells_value, item.args[0], item.args[1])
        CheckId.TRAFFIC -> stringResource(if (ok) R.string.check_traffic_ok else R.string.check_traffic_bad)
    }
}

/** 4-ekran — jonli o'lchov (§8.1). */
@Composable
fun LiveRoute(onFinished: (String) -> Unit, vm: LiveViewModel = hiltViewModel()) {
    val s by vm.state.collectAsStateWithLifecycle()
    val plan by vm.plan.collectAsStateWithLifecycle()
    val stopping by vm.stopping.collectAsStateWithLifecycle()
    LaunchedEffect(s.finishedSessionId) {
        if (s.finishedSessionId == vm.sessionId) onFinished(vm.sessionId)
    }
    plan?.let { LiveScreen(it, s, stopping, vm::finish) }
}

@Composable
fun LiveScreen(plan: SitePlan, s: SurveyState, stopping: Boolean, onFinish: () -> Unit) {
    val p = LocalSvPalette.current
    val live = s.live
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Text(plan.code, style = MaterialTheme.typography.headlineSmall)
            Text(stringResource(R.string.live_stats, s.samples, s.fixes, s.rateHz), color = p.inkMuted)
            s.lastFix?.let { Text(stringResource(R.string.live_gps, it.accM.toInt()), color = p.inkMuted) }
            Text(trafficText(s.traffic), color = p.inkMuted)
        }
        if (s.readyAtSamples != null) {
            item {
                Card { Text(stringResource(R.string.live_ready), color = p.ok, style = MaterialTheme.typography.titleMedium) }
            }
        }
        item { MapCanvas(plan, s.track) }
        item { SectionTitle(stringResource(uz.sectorverify.ui.R.string.radar_title)) }
        item { CoverageRadar(live?.coveredBins ?: List(COVERAGE_BINS) { false }, Modifier.padding(horizontal = 48.dp)) }
        items(live?.cells.orEmpty(), key = { it.key.toString() }) { CellCard(it) }
        item { PrimaryButton(stringResource(R.string.live_finish), onFinish, Modifier.testTag("finish"), enabled = !stopping) }
        if (stopping) item { Text(stringResource(R.string.live_analyzing), color = p.inkMuted) }
    }
}

@Composable
private fun CellCard(c: LiveCell) {
    val p = LocalSvPalette.current
    val status = stringResource(c.status.labelRes())
    Card {
        Box(Modifier.size(16.dp).background(p.verdictColor(c.status), CircleShape).semantics { contentDescription = status })
        Column(Modifier.weight(1f)) {
            Text("${c.label ?: stringResource(R.string.live_unplanned)} · ${c.key}", style = MaterialTheme.typography.titleSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(stringResource(R.string.live_rsrp, c.lastRsrp?.toInt()?.toString() ?: "—"))
                Text(
                    stringResource(
                        R.string.live_azimuth,
                        c.alphaDeg?.toInt()?.toString() ?: "—",
                        c.planAzimuthDeg?.toInt()?.toString() ?: "—",
                    ),
                )
            }
            Text(stringResource(R.string.live_samples, c.nSamples, c.nBins), color = p.inkMuted, style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun trafficText(t: TrafficStatus?): String = when (t) {
    null, TrafficStatus.Disabled -> stringResource(R.string.live_traffic_off)
    is TrafficStatus.Ok -> stringResource(R.string.live_traffic_ok, t.latencyMs)
    is TrafficStatus.Error -> stringResource(R.string.live_traffic_error, t.reason)
}

private const val COVERAGE_BINS = 36
