package uz.sectorverify.feature.report

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlin.math.roundToInt
import uz.sectorverify.data.repo.StoredResult
import uz.sectorverify.format.SvJson
import uz.sectorverify.model.FindingType
import uz.sectorverify.model.SectorResult
import uz.sectorverify.ui.components.Card
import uz.sectorverify.ui.components.PolarDiagram
import uz.sectorverify.ui.components.PolarItem
import uz.sectorverify.ui.components.PrimaryButton
import uz.sectorverify.ui.components.SecondaryButton
import uz.sectorverify.ui.components.SectionTitle
import uz.sectorverify.ui.components.VerdictChip
import uz.sectorverify.ui.components.labelRes
import uz.sectorverify.ui.components.pciColor
import uz.sectorverify.ui.theme.LocalSvPalette
import uz.sectorverify.ui.util.Share

/** 5-ekran — natija: har ARFCN uchun qutb diagramma, verdikt jadvali, topilmalar, tavsiya etilgan choralar, qayta tekshiruv. */
@Composable
fun ResultRoute(onRecheck: (Long) -> Unit, onReport: (String) -> Unit, vm: ResultViewModel = hiltViewModel()) {
    val ui by vm.ui.collectAsStateWithLifecycle()
    val stored = ui.stored
    when {
        ui.loading -> Unit
        stored == null -> Text(stringResource(R.string.result_not_found), Modifier.padding(16.dp))
        else -> ResultScreen(stored, ui.plan?.code.orEmpty(), { ui.siteId?.let(onRecheck) }, { onReport(vm.sessionId) })
    }
}

@Composable
fun ResultScreen(stored: StoredResult, siteCode: String, onRecheck: () -> Unit, onReport: () -> Unit) {
    val p = LocalSvPalette.current
    val res = LocalContext.current.resources
    val planned = stored.sectors.filter { it.label != null }
    val binDeg = remember(stored.session.configJson) { SvJson.parseConfig(stored.session.configJson).binDeg }
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item { Text(stringResource(R.string.result_title, siteCode), style = MaterialTheme.typography.headlineSmall) }
        item {
            Card(Modifier.testTag("overall")) {
                Column(Modifier.weight(1f)) {
                    Text(stringResource(R.string.result_overall), style = MaterialTheme.typography.titleMedium)
                    Text(stringResource(R.string.result_coverage, (stored.session.coveragePct ?: 0.0).roundToInt()), color = p.inkMuted)
                }
                VerdictChip(stored.session.verdict)
            }
        }
        for ((key, list) in planned.groupBy { it.key.rat to it.key.arfcn }) {
            item { SectionTitle(stringResource(R.string.result_arfcn, key.first.name, key.second)) }
            item {
                PolarDiagram(
                    list.map {
                        PolarItem(
                            it.label.orEmpty(),
                            it.planAzimuthDeg,
                            it.estimate?.alphaDeg,
                            it.estimate?.ciLowDeg,
                            it.estimate?.ciHighDeg,
                            p.pciColor(it.key.pci),
                        )
                    },
                )
            }
        }
        item { SectionTitle(stringResource(R.string.result_table)) }
        items(stored.sectors, key = { it.key.toString() }) { SectorRow(it) }
        item { SectionTitle(stringResource(R.string.result_findings)) }
        items(stored.findings.filter { it.type == FindingType.SWAP }) { f ->
            Text(
                stringResource(
                    R.string.finding_swap,
                    f.detail["rat"].orEmpty(),
                    f.detail["arfcn"].orEmpty(),
                    f.detail["mapping"].orEmpty(),
                ),
                color = p.danger,
            )
        }
        items(stored.sectors.filter { it.verdict != uz.sectorverify.model.Verdict.PASS }, key = { "rec-${it.key}" }) { s ->
            Column(Modifier.fillMaxWidth()) {
                Text("${s.label ?: stringResource(R.string.result_unplanned)} · ${s.key}", style = MaterialTheme.typography.titleSmall)
                Text(Recommendations.forSector(res, s, stored.findings))
                if (s.missingBins.isNotEmpty()) {
                    Text(
                        stringResource(R.string.result_missing, Recommendations.directions(s.missingBins, binDeg)),
                        color = p.inkMuted,
                    )
                }
            }
        }
        item { PrimaryButton(stringResource(R.string.result_report), onReport, Modifier.testTag("report")) }
        item { SecondaryButton(stringResource(R.string.result_recheck), onRecheck, Modifier.testTag("recheck")) }
    }
}

@Composable
private fun SectorRow(s: SectorResult) {
    val p = LocalSvPalette.current
    val e = s.estimate
    Card {
        Column(Modifier.weight(1f)) {
            Text("${s.label ?: stringResource(R.string.result_unplanned)} · ${s.key}", style = MaterialTheme.typography.titleSmall)
            Text(
                stringResource(
                    R.string.result_row,
                    s.planAzimuthDeg?.roundToInt()?.toString() ?: "—",
                    e?.alphaDeg?.roundToInt()?.toString() ?: "—",
                    e?.ciHalfDeg?.roundToInt()?.toString() ?: "—",
                    s.errorDeg?.roundToInt()?.toString() ?: "—",
                ),
                color = p.inkMuted,
            )
            Text(stringResource(s.cause.labelRes()), style = MaterialTheme.typography.bodySmall)
        }
        VerdictChip(s.verdict)
    }
}

/** 6-ekran — hisobot. */
@Composable
fun ReportRoute(vm: ReportViewModel = hiltViewModel()) {
    val state by vm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val shareTitle = stringResource(R.string.report_share)
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Text(stringResource(R.string.report_title, vm.sessionId.take(SHORT_ID)), style = MaterialTheme.typography.headlineSmall)
        PrimaryButton(
            stringResource(R.string.report_generate),
            vm::generate,
            Modifier.testTag("generate"),
            enabled =
            state != ReportState.Working,
        )
        when (val s = state) {
            ReportState.Idle -> Unit
            ReportState.Working -> Text(stringResource(R.string.report_generating))
            is ReportState.Failed -> Text(stringResource(R.string.report_error, s.reason), color = LocalSvPalette.current.danger)
            is ReportState.Ready -> {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text(stringResource(R.string.report_ready, s.sha256.take(SHORT_SHA)), Modifier.testTag("ready"))
                }
                SecondaryButton(stringResource(R.string.report_view), { Share.view(context, s.pdf, PDF) })
                SecondaryButton(stringResource(R.string.report_share), { Share.send(context, s.pdf, PDF, shareTitle) })
                SecondaryButton(stringResource(R.string.report_zip), { Share.send(context, s.zip, ZIP, shareTitle) })
            }
        }
    }
}

private const val PDF = "application/pdf"
private const val ZIP = "application/zip"
private const val SHORT_ID = 8
private const val SHORT_SHA = 16
