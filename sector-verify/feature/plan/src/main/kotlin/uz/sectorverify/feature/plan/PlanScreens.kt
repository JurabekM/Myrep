package uz.sectorverify.feature.plan

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import java.text.DateFormat
import java.util.Date
import uz.sectorverify.data.db.SessionEntity
import uz.sectorverify.data.repo.SiteSummary
import uz.sectorverify.model.SitePlan
import uz.sectorverify.ui.components.Card
import uz.sectorverify.ui.components.MinTouch
import uz.sectorverify.ui.components.PolarDiagram
import uz.sectorverify.ui.components.PolarItem
import uz.sectorverify.ui.components.PrimaryButton
import uz.sectorverify.ui.components.SectionTitle
import uz.sectorverify.ui.components.VerdictChip
import uz.sectorverify.ui.components.pciColor
import uz.sectorverify.ui.theme.LocalSvPalette

/** 1-ekran — saytlar (§8.1). */
@Composable
fun SitesRoute(onOpenSite: (Long) -> Unit, onSettings: () -> Unit, onResumed: (String) -> Unit, vm: SitesViewModel = hiltViewModel()) {
    val context = LocalContext.current
    val sites by vm.sites.collectAsStateWithLifecycle()
    val query by vm.query.collectAsStateWithLifecycle()
    val import by vm.import.collectAsStateWithLifecycle()
    val resume by vm.resume.collectAsStateWithLifecycle()
    val resumeBlocked by vm.resumeBlocked.collectAsStateWithLifecycle()
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        uri?.let { u -> context.contentResolver.openInputStream(u)?.use { vm.importCsv(it.readBytes().toString(Charsets.UTF_8)) } }
    }
    SitesScreen(sites, query, vm::setQuery, { picker.launch("*/*") }, onOpenSite, onSettings)
    import?.let { ImportDialog(it, vm::dismissImport) }
    resume?.let { r ->
        AlertDialog(
            onDismissRequest = {},
            title = { Text(stringResource(R.string.resume_title)) },
            text = {
                Column {
                    Text(
                        if (r.recording) {
                            stringResource(R.string.resume_recording, r.siteCode, r.samples)
                        } else {
                            stringResource(R.string.resume_text, r.siteCode, r.samples)
                        },
                    )
                    if (resumeBlocked) Text(stringResource(R.string.resume_no_permission), color = LocalSvPalette.current.danger)
                }
            },
            confirmButton = {
                TextButton(onClick = { vm.resume()?.let(onResumed) }, modifier = Modifier.heightIn(min = MinTouch)) {
                    Text(stringResource(if (r.recording) R.string.resume_open else R.string.resume_continue))
                }
            },
            dismissButton = {
                if (!r.recording) {
                    TextButton(onClick = vm::abandon, modifier = Modifier.heightIn(min = MinTouch)) {
                        Text(stringResource(R.string.resume_abandon))
                    }
                }
            },
        )
    }
}

@Composable
fun SitesScreen(
    sites: List<SiteSummary>,
    query: String,
    onQuery: (String) -> Unit,
    onImport: () -> Unit,
    onOpenSite: (Long) -> Unit,
    onSettings: () -> Unit,
) {
    Column(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(stringResource(R.string.sites_title), style = MaterialTheme.typography.headlineMedium, modifier = Modifier.weight(1f))
            IconButton(onClick = onSettings, modifier = Modifier.heightIn(min = MinTouch).width(MinTouch)) {
                Icon(Icons.Filled.Settings, contentDescription = stringResource(R.string.sites_settings))
            }
        }
        OutlinedTextField(
            value = query,
            onValueChange = onQuery,
            label = { Text(stringResource(R.string.sites_search)) },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().testTag("search"),
        )
        PrimaryButton(stringResource(R.string.sites_import), onImport, Modifier.testTag("import"))
        if (sites.isEmpty() && query.isEmpty()) {
            Text(stringResource(R.string.sites_empty), color = LocalSvPalette.current.inkMuted)
        }
        LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
            items(sites, key = { it.id }) { s ->
                Card(Modifier.clickable { onOpenSite(s.id) }.heightIn(min = MinTouch).testTag("site-${s.code}")) {
                    Column(Modifier.weight(1f)) {
                        Text(s.code, style = MaterialTheme.typography.titleMedium)
                        Text("${s.name} · ${stringResource(R.string.sites_sectors, s.sectors)}", color = LocalSvPalette.current.inkMuted)
                    }
                    VerdictChip(s.lastVerdict)
                }
            }
        }
    }
}

@Composable
private fun ImportDialog(o: ImportOutcome, onDismiss: () -> Unit) {
    val res = LocalContext.current.resources
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = { TextButton(onClick = onDismiss) { Text(stringResource(uz.sectorverify.ui.R.string.common_ok)) } },
        title = {
            Text(
                if (o.errors.isEmpty()) {
                    stringResource(R.string.sites_imported, o.imported)
                } else {
                    stringResource(R.string.sites_import_failed, o.errors.size)
                },
            )
        },
        text = {
            if (o.errors.isNotEmpty()) {
                LazyColumn(Modifier.heightIn(max = 360.dp)) { items(o.errors) { Text(it.localized(res)) } }
            }
        },
    )
}

/** 2-ekran — sayt kartasi: reja jadvali va rejadagi azimutlarning qutb diagrammasi. */
@Composable
fun SiteCardRoute(onPreCheck: (Long) -> Unit, onOpenSession: (String) -> Unit, vm: SiteCardViewModel = hiltViewModel()) {
    val plan by vm.plan.collectAsStateWithLifecycle()
    val history by vm.history.collectAsStateWithLifecycle()
    plan?.let { SiteCardScreen(it, history, { onPreCheck(vm.siteId) }, onOpenSession) }
}

@Composable
fun SiteCardScreen(plan: SitePlan, history: List<SessionEntity>, onPreCheck: () -> Unit, onOpenSession: (String) -> Unit) {
    val p = LocalSvPalette.current
    LazyColumn(Modifier.fillMaxSize().padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        item {
            Text("${plan.code} · ${plan.name}", style = MaterialTheme.typography.headlineSmall)
            Text("%.5f, %.5f · %s".format(plan.lat, plan.lon, plan.mccMnc), color = p.inkMuted)
        }
        item { PrimaryButton(stringResource(R.string.card_precheck), onPreCheck, Modifier.testTag("precheck")) }
        item { SectionTitle(stringResource(R.string.card_plan)) }
        for ((key, sectors) in plan.sectors.groupBy { Triple(it.rat, it.arfcn, it.band) }) {
            item {
                Text(
                    stringResource(R.string.card_arfcn, key.first.name, key.second, key.third),
                    style = MaterialTheme.typography.titleSmall,
                )
            }
            item { PolarDiagram(sectors.map { PolarItem(it.label, it.azimuthDeg, color = p.pciColor(it.pci)) }) }
            items(sectors) { s ->
                Row(Modifier.fillMaxWidth()) {
                    Text(s.label, Modifier.weight(1f))
                    Text("${s.rat}/${s.arfcn}/${s.pci}", Modifier.weight(2f))
                    Text("%.0f° · HPBW %.0f°".format(s.azimuthDeg, s.hpbwDeg), Modifier.weight(2f))
                }
            }
        }
        item { SectionTitle(stringResource(R.string.card_history)) }
        if (history.isEmpty()) item { Text(stringResource(R.string.card_no_history), color = p.inkMuted) }
        items(history, key = { it.id }) { s ->
            Card(Modifier.clickable { onOpenSession(s.id) }.heightIn(min = MinTouch)) {
                Text(DateFormat.getDateTimeInstance().format(Date(s.startedAt)), Modifier.weight(1f))
                Text(s.mode.name, color = p.inkMuted)
                Spacer(Modifier.width(4.dp))
                VerdictChip(s.verdict)
            }
        }
    }
}
