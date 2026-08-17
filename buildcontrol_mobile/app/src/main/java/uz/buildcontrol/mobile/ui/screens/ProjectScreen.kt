package uz.buildcontrol.mobile.ui.screens

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.ScrollableTabRow
import androidx.compose.material3.Tab
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.data.db.EstimateItemRow
import uz.buildcontrol.mobile.data.db.SiteLogRow
import uz.buildcontrol.mobile.data.db.WorkStageRow
import uz.buildcontrol.mobile.data.repo.EstimateRepository
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.ItemStatus
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.ProjectTotals
import uz.buildcontrol.mobile.domain.StageStatus
import uz.buildcontrol.mobile.domain.Units
import uz.buildcontrol.mobile.ui.SyncAction
import uz.buildcontrol.mobile.ui.components.Badge
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.EmptyState
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.FormSheet
import uz.buildcontrol.mobile.ui.components.KeyValue
import uz.buildcontrol.mobile.ui.components.MetricTile
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.SectionTitle
import uz.buildcontrol.mobile.ui.components.UsageBar
import uz.buildcontrol.mobile.ui.theme.BcColors

private val TAB_KEYS = listOf(
    "tab_overview", "tab_estimate", "tab_purchases", "tab_warehouse", "tab_stages", "tab_expenses",
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectScreen(user: CurrentUser, projectId: Long, onBack: () -> Unit) {
    val container = BuildControlApp.container
    var tab by remember { mutableIntStateOf(0) }
    val project by container.projects.observeProject(projectId)
        .collectAsStateWithLifecycle(initialValue = null)

    Scaffold(
        containerColor = BcColors.Background,
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            project?.name ?: "",
                            style = MaterialTheme.typography.titleMedium,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Text(
                            "${project?.code.orEmpty()} · ${project?.client.orEmpty()}",
                            style = MaterialTheme.typography.labelSmall,
                            color = BcColors.TextMuted,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    }
                },
                actions = { SyncAction() },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BcColors.BackgroundAlt,
                    titleContentColor = BcColors.Text,
                    navigationIconContentColor = BcColors.TextMuted,
                ),
            )
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding)) {
            ScrollableTabRow(
                selectedTabIndex = tab,
                containerColor = BcColors.BackgroundAlt,
                contentColor = BcColors.Accent,
                edgePadding = 8.dp,
            ) {
                TAB_KEYS.forEachIndexed { index, key ->
                    Tab(
                        selected = tab == index,
                        onClick = { tab = index },
                        text = {
                            Text(
                                tr(key),
                                style = MaterialTheme.typography.labelLarge,
                                color = if (tab == index) BcColors.Text else BcColors.TextMuted,
                            )
                        },
                    )
                }
            }
            when (tab) {
                0 -> OverviewTab(projectId)
                1 -> EstimateTab(user, projectId)
                2 -> PurchasesTab(user, projectId)
                3 -> WarehouseScreen(user, projectId = projectId, embedded = true)
                4 -> StagesTab(user, projectId)
                else -> ExpensesScreen(user, projectId = projectId, embedded = true)
            }
        }
    }
}

// --------------------------------------------------------------------------- //
// Overview
// --------------------------------------------------------------------------- //

@Composable
private fun OverviewTab(projectId: Long) {
    val container = BuildControlApp.container
    var totals by remember { mutableStateOf(ProjectTotals()) }
    val project by container.projects.observeProject(projectId)
        .collectAsStateWithLifecycle(initialValue = null)

    LaunchedEffect(projectId, project) {
        container.estimates.recalcActuals(projectId)
        container.work.refreshDelays(projectId)
        totals = container.projects.totals(projectId)
    }

    Column(
        Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(14.dp)
    ) {
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricTile(tr("budget"), Fmt.money(totals.plannedBudget), modifier = Modifier.weight(1f))
            MetricTile(
                tr("actual_cost"),
                Fmt.money(totals.actual),
                kind = if (totals.isOverBudget) "danger" else "neutral",
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            MetricTile(
                tr("remaining_funds"),
                Fmt.money(totals.remaining),
                kind = if (totals.remaining < 0) "danger" else "success",
                modifier = Modifier.weight(1f),
            )
            MetricTile(
                tr("estimate_total"),
                Fmt.money(totals.estimateTotal),
                hint = if (totals.overBudgetItems > 0)
                    "${tr("over_budget")}: ${totals.overBudgetItems}" else "",
                kind = if (totals.overBudgetItems > 0) "warning" else "neutral",
                modifier = Modifier.weight(1f),
            )
        }
        Spacer(Modifier.height(12.dp))
        BcCard {
            SectionTitle(tr("budget_usage"))
            UsageBar(totals.usageRatio)
            Spacer(Modifier.height(8.dp))
            KeyValue(tr("committed_cost"), Fmt.money(totals.committed))
            KeyValue(tr("materials_issued"), Fmt.money(totals.materialIssued))
            KeyValue(
                tr("pending_purchases"),
                totals.pendingPurchases.toString(),
                if (totals.pendingPurchases > 0) BcColors.Warning else BcColors.Text,
            )
            KeyValue(
                tr("delayed_stages"),
                totals.delayedStages.toString(),
                if (totals.delayedStages > 0) BcColors.Danger else BcColors.Text,
            )
            KeyValue(
                tr("stages_summary"),
                "${totals.doneStages} / ${totals.totalStages}",
            )
            KeyValue(tr("percent_done"), Fmt.percent(totals.avgProgress))
        }
        Spacer(Modifier.height(12.dp))
        BcCard {
            SectionTitle(tr("project"))
            KeyValue(tr("address"), project?.address.orEmpty().ifBlank { "—" })
            KeyValue(tr("project_type"), I18n.enum("ptype", project?.projectType))
            KeyValue(tr("start_date"), Fmt.date(project?.startDate))
            KeyValue(tr("end_date"), Fmt.date(project?.endDate))
            KeyValue(tr("status"), I18n.enum("pstatus", project?.status))
        }
        Spacer(Modifier.height(24.dp))
    }
}

// --------------------------------------------------------------------------- //
// Estimate
// --------------------------------------------------------------------------- //

@Composable
private fun EstimateTab(user: CurrentUser, projectId: Long) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var tree by remember { mutableStateOf(EstimateRepository.Tree(null)) }
    var reload by remember { mutableIntStateOf(0) }
    var editing by remember { mutableStateOf<EstimateItemRow?>(null) }
    var addingSection by remember { mutableStateOf(false) }
    var addingItemIn by remember { mutableStateOf<Long?>(null) }

    LaunchedEffect(projectId, reload) {
        container.estimates.recalcActuals(projectId)
        val version = container.estimates.ensureVersion(projectId)
        val sections = container.estimates.sections(projectId)
        val items = container.estimates.items(projectId)
        tree = buildTree(version, sections, items)
    }

    val canEdit = user.can(Perm.ESTIMATE_EDIT) && tree.editable

    Column(Modifier.fillMaxSize()) {
        BcCard(Modifier.padding(horizontal = 14.dp, vertical = 8.dp)) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "${tr("estimate_version")} v${tree.version?.versionNo ?: 1}",
                    style = MaterialTheme.typography.titleSmall,
                    color = BcColors.Text,
                )
                Badge(
                    I18n.enum("estatus", tree.version?.status),
                    when (tree.version?.status) {
                        "approved" -> "success"
                        "submitted" -> "warning"
                        "revision" -> "info"
                        else -> "neutral"
                    },
                )
            }
            Spacer(Modifier.height(8.dp))
            KeyValue(tr("plan_total"), Fmt.money(tree.planTotal))
            KeyValue(tr("actual_total"), Fmt.money(tree.actualTotal))
            KeyValue(
                tr("variance"),
                Fmt.money(tree.variance),
                if (tree.variance > 0) BcColors.Danger else BcColors.Success,
            )
            if (!tree.editable) {
                Spacer(Modifier.height(6.dp))
                Text(
                    tr("estimate_locked"),
                    color = BcColors.Warning,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
        }

        if (tree.roots.isEmpty()) {
            EmptyState(tr("no_estimate"))
        }

        LazyColumn(
            Modifier.weight(1f).padding(horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            tree.roots.forEach { node -> sectionItems(node, 0, canEdit, { editing = it }) { addingItemIn = it } }
            item {
                if (canEdit) {
                    Spacer(Modifier.height(8.dp))
                    uz.buildcontrol.mobile.ui.components.GhostButton(
                        tr("add_section"),
                        onClick = { addingSection = true },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
                Spacer(Modifier.height(70.dp))
            }
        }
    }

    if (addingSection) {
        var name by remember { mutableStateOf("") }
        var code by remember { mutableStateOf("") }
        FormSheet(
            title = tr("add_section"),
            onDismiss = { addingSection = false },
            onSave = {
                scope.launch {
                    val version = container.estimates.ensureVersion(projectId)
                    runCatching {
                        container.estimates.addSection(user, version.id, name, null, code)
                    }
                    addingSection = false
                    reload++
                }
            },
        ) {
            Field(tr("name"), name, { name = it }, required = true)
            Field(tr("code"), code, { code = it })
        }
    }

    val sectionForItem = addingItemIn
    if (sectionForItem != null || editing != null) {
        EstimateItemSheet(
            user = user,
            initial = editing,
            sectionId = sectionForItem ?: editing?.sectionId ?: 0L,
            onDismiss = {
                addingItemIn = null
                editing = null
            },
            onSaved = {
                addingItemIn = null
                editing = null
                reload++
            },
        )
    }
}

private fun buildTree(
    version: uz.buildcontrol.mobile.data.db.EstimateVersionRow,
    sections: List<uz.buildcontrol.mobile.data.db.EstimateSectionRow>,
    items: List<EstimateItemRow>,
): EstimateRepository.Tree {
    val nodes = sections.associate { it.id to EstimateRepository.Node(it) }
    items.forEach { item -> nodes[item.sectionId]?.items?.add(item) }
    val roots = mutableListOf<EstimateRepository.Node>()
    for (section in sections) {
        val node = nodes[section.id] ?: continue
        val parent = section.parentId?.let { nodes[it] }
        if (parent != null) parent.children.add(node) else roots.add(node)
    }
    return EstimateRepository.Tree(version, roots, items)
}

private fun androidx.compose.foundation.lazy.LazyListScope.sectionItems(
    node: EstimateRepository.Node,
    depth: Int,
    canEdit: Boolean,
    onEditItem: (EstimateItemRow) -> Unit,
    onAddItem: (Long) -> Unit,
) {
    item(key = "s${node.section.id}") {
        BcCard {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    "${node.section.code.orEmpty()} ${node.section.name}".trim(),
                    style = MaterialTheme.typography.titleSmall,
                    fontWeight = FontWeight.Bold,
                    color = BcColors.Text,
                    modifier = Modifier.weight(1f).padding(start = (depth * 10).dp),
                )
                Text(
                    Fmt.money(node.planTotal, withSuffix = false),
                    style = MaterialTheme.typography.bodyMedium,
                    color = BcColors.TextMuted,
                )
            }
            if (node.variance > 0) {
                Text(
                    "${tr("variance")}: ${Fmt.money(node.variance)}",
                    color = BcColors.Danger,
                    style = MaterialTheme.typography.labelSmall,
                )
            }
            node.items.forEach { item ->
                EstimateItemRowView(item, canEdit) { onEditItem(item) }
            }
            if (canEdit) {
                Spacer(Modifier.height(6.dp))
                uz.buildcontrol.mobile.ui.components.GhostButton(
                    tr("add_item"),
                    onClick = { onAddItem(node.section.id) },
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
    node.children.forEach { child -> sectionItems(child, depth + 1, canEdit, onEditItem, onAddItem) }
}

@Composable
private fun EstimateItemRowView(item: EstimateItemRow, canEdit: Boolean, onClick: () -> Unit) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(top = 8.dp)
            .then(
                if (canEdit) Modifier.padding(0.dp) else Modifier
            )
    ) {
        Row(
            Modifier.fillMaxWidth().then(
                if (canEdit) Modifier.androidxClickable(onClick) else Modifier
            ),
            horizontalArrangement = Arrangement.SpaceBetween,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    "${item.code.orEmpty()} ${item.name}".trim(),
                    style = MaterialTheme.typography.bodyMedium,
                    color = BcColors.Text,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    "${Fmt.qty(item.quantity)} ${I18n.enum("unit", item.unit)} × " +
                        Fmt.money(item.planUnitPrice, withSuffix = false),
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    Fmt.money(item.planTotal, withSuffix = false),
                    style = MaterialTheme.typography.bodyMedium,
                    color = BcColors.Text,
                )
                Text(
                    Fmt.money(item.actualCost, withSuffix = false),
                    style = MaterialTheme.typography.labelSmall,
                    color = if (item.variance > 0) BcColors.Danger else BcColors.TextMuted,
                )
            }
        }
    }
}

private fun Modifier.androidxClickable(onClick: () -> Unit): Modifier = this.clickable(onClick = onClick)

@Composable
private fun EstimateItemSheet(
    user: CurrentUser,
    initial: EstimateItemRow?,
    sectionId: Long,
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var name by remember { mutableStateOf(initial?.name ?: "") }
    var code by remember { mutableStateOf(initial?.code ?: "") }
    var qty by remember { mutableStateOf(initial?.quantity?.let { Fmt.qty(it) } ?: "") }
    var price by remember { mutableStateOf(initial?.planUnitPrice?.let { Fmt.qty(it) } ?: "") }
    var unit by remember { mutableStateOf(initial?.unit ?: "piece") }
    var status by remember { mutableStateOf(initial?.status ?: ItemStatus.PLANNED) }
    var progress by remember { mutableStateOf(initial?.progressPercent?.let { Fmt.qty(it) } ?: "0") }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = if (initial == null) tr("add_item") else tr("item"),
        onDismiss = onDismiss,
        error = error,
        onSave = {
            if (name.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.estimates.saveItem(
                        user,
                        (initial ?: EstimateItemRow()).copy(
                            sectionId = initial?.sectionId ?: sectionId,
                            name = name.trim(),
                            code = code.trim(),
                            unit = unit,
                            quantity = Fmt.parseNumber(qty),
                            planUnitPrice = Fmt.parseNumber(price),
                            progressPercent = Fmt.parseNumber(progress),
                            status = status,
                        ),
                    )
                    onSaved()
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("name"), name, { name = it }, required = true)
        Field(tr("code"), code, { code = it })
        Field(tr("quantity"), qty, { qty = it }, numeric = true, required = true)
        Picker(tr("unit"), Units.all.map { it to I18n.enum("unit", it) }, unit, { unit = it })
        Field(tr("plan_unit_price"), price, { price = it }, numeric = true)
        Field(tr("percent_done"), progress, { progress = it }, numeric = true)
        Picker(
            tr("status"),
            ItemStatus.all.map { it to I18n.enum("istatus", it) },
            status,
            { status = it },
        )
    }
}

// --------------------------------------------------------------------------- //
// Stages
// --------------------------------------------------------------------------- //

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun StagesTab(user: CurrentUser, projectId: Long) {
    val container = BuildControlApp.container
    val stages by container.work.observeStages(projectId)
        .collectAsStateWithLifecycle(initialValue = emptyList())
    val logs by container.work.observeLogs(projectId)
        .collectAsStateWithLifecycle(initialValue = emptyList())
    var editing by remember { mutableStateOf<WorkStageRow?>(null) }
    var adding by remember { mutableStateOf(false) }
    var addingLog by remember { mutableStateOf(false) }

    LaunchedEffect(projectId) { container.work.refreshDelays(projectId) }

    Scaffold(
        containerColor = BcColors.Background,
        floatingActionButton = {
            if (user.can(Perm.STAGE_EDIT)) {
                FloatingActionButton(
                    onClick = { addingLog = true },
                    containerColor = BcColors.Accent,
                ) { Icon(Icons.Default.Add, contentDescription = tr("new_log")) }
            }
        },
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            item { SectionTitle(tr("stages")) }
            if (stages.isEmpty()) item { EmptyState() }
            items(stages, key = { it.id }) { stage ->
                BcCard(onClick = { if (user.can(Perm.STAGE_EDIT)) editing = stage }) {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Text(
                            stage.name,
                            style = MaterialTheme.typography.titleSmall,
                            color = BcColors.Text,
                            modifier = Modifier.weight(1f),
                            maxLines = 2,
                            overflow = TextOverflow.Ellipsis,
                        )
                        Badge(I18n.enum("sstatus", stage.status), stageKind(stage.status))
                    }
                    Spacer(Modifier.height(6.dp))
                    UsageBar(stage.progressPercent / 100.0)
                    Spacer(Modifier.height(6.dp))
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(
                            "${Fmt.date(stage.planStart)} — ${Fmt.date(stage.planEnd)}",
                            color = BcColors.TextMuted,
                            style = MaterialTheme.typography.labelSmall,
                        )
                        Text(
                            Fmt.percent(stage.progressPercent, 0),
                            color = BcColors.TextMuted,
                            style = MaterialTheme.typography.labelSmall,
                        )
                    }
                }
            }
            item {
                if (user.can(Perm.STAGE_EDIT)) {
                    uz.buildcontrol.mobile.ui.components.GhostButton(
                        tr("new_stage"),
                        onClick = { adding = true },
                        modifier = Modifier.fillMaxWidth(),
                    )
                }
            }
            item { SectionTitle(tr("site_log")) }
            if (logs.isEmpty()) item { EmptyState() }
            items(logs, key = { "log${it.id}" }) { log -> SiteLogCard(log) }
            item { Spacer(Modifier.height(80.dp)) }
        }
    }

    if (adding || editing != null) {
        StageSheet(
            user = user,
            projectId = projectId,
            initial = editing,
            onDismiss = { adding = false; editing = null },
            onSaved = { adding = false; editing = null },
        )
    }
    if (addingLog) {
        SiteLogSheet(
            user = user,
            projectId = projectId,
            stages = stages,
            onDismiss = { addingLog = false },
            onSaved = { addingLog = false },
        )
    }
}

fun stageKind(status: String): String = when (status) {
    StageStatus.DONE -> "success"
    StageStatus.IN_PROGRESS -> "accent"
    StageStatus.REVIEW -> "info"
    StageStatus.DELAYED -> "danger"
    StageStatus.BLOCKED -> "warning"
    else -> "neutral"
}

@Composable
private fun SiteLogCard(log: SiteLogRow) {
    BcCard {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                Fmt.date(log.logDate),
                style = MaterialTheme.typography.labelMedium,
                color = BcColors.TextMuted,
            )
            Text(
                Fmt.percent(log.progressPercent, 0),
                style = MaterialTheme.typography.labelMedium,
                color = BcColors.Accent,
            )
        }
        Spacer(Modifier.height(4.dp))
        Text(log.workDone.orEmpty(), style = MaterialTheme.typography.bodyMedium, color = BcColors.Text)
        if (!log.issue.isNullOrBlank()) {
            Spacer(Modifier.height(4.dp))
            Text(
                "${tr("issue")}: ${log.issue}",
                style = MaterialTheme.typography.bodySmall,
                color = BcColors.Warning,
            )
        }
        if (log.workersCount > 0) {
            Text(
                "${tr("workers_count")}: ${log.workersCount}",
                style = MaterialTheme.typography.labelSmall,
                color = BcColors.TextFaint,
            )
        }
    }
}

@Composable
private fun StageSheet(
    user: CurrentUser,
    projectId: Long,
    initial: WorkStageRow?,
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var name by remember { mutableStateOf(initial?.name ?: "") }
    var planStart by remember { mutableStateOf(initial?.planStart ?: Fmt.today()) }
    var planEnd by remember { mutableStateOf(initial?.planEnd ?: Fmt.plusDays(Fmt.today(), 14)) }
    var progress by remember { mutableStateOf(initial?.progressPercent?.let { Fmt.qty(it) } ?: "0") }
    var status by remember { mutableStateOf(initial?.status ?: StageStatus.NOT_STARTED) }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = if (initial == null) tr("new_stage") else tr("stage"),
        onDismiss = onDismiss,
        error = error,
        onSave = {
            if (name.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.work.saveStage(
                        user,
                        (initial ?: WorkStageRow()).copy(
                            projectId = projectId,
                            name = name.trim(),
                            planStart = planStart.ifBlank { null },
                            planEnd = planEnd.ifBlank { null },
                            progressPercent = Fmt.parseNumber(progress),
                            status = status,
                        ),
                    )
                    onSaved()
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("name"), name, { name = it }, required = true)
        Field(tr("plan_start"), planStart, { planStart = it })
        Field(tr("plan_end"), planEnd, { planEnd = it })
        Field(tr("percent_done"), progress, { progress = it }, numeric = true)
        Picker(
            tr("status"),
            StageStatus.all.map { it to I18n.enum("sstatus", it) },
            status,
            { status = it },
        )
    }
}

@Composable
private fun SiteLogSheet(
    user: CurrentUser,
    projectId: Long,
    stages: List<WorkStageRow>,
    onDismiss: () -> Unit,
    onSaved: () -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var stageId by remember { mutableStateOf(stages.firstOrNull()?.id) }
    var work by remember { mutableStateOf("") }
    var progress by remember { mutableStateOf("") }
    var workers by remember { mutableStateOf("") }
    var issue by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = tr("new_log"),
        onDismiss = onDismiss,
        error = error,
        onSave = {
            if (work.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.work.saveLog(
                        user,
                        SiteLogRow(
                            projectId = projectId,
                            stageId = stageId,
                            logDate = Fmt.today(),
                            workDone = work.trim(),
                            progressPercent = Fmt.parseNumber(progress),
                            workersCount = Fmt.parseNumber(workers).toInt(),
                            issue = issue.trim(),
                        ),
                    )
                    onSaved()
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Picker(
            tr("stage"),
            stages.map { it.id as Long? to it.name },
            stageId,
            { stageId = it },
        )
        Field(tr("work_done"), work, { work = it }, singleLine = false, required = true)
        Field(tr("percent_done"), progress, { progress = it }, numeric = true)
        Field(tr("workers_count"), workers, { workers = it }, numeric = true)
        Field(tr("issue"), issue, { issue = it }, singleLine = false)
    }
}
