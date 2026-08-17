package uz.buildcontrol.mobile.ui.screens

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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
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
import uz.buildcontrol.mobile.data.db.ProjectRow
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.ProjectStatus
import uz.buildcontrol.mobile.domain.ProjectTotals
import uz.buildcontrol.mobile.domain.ProjectType
import uz.buildcontrol.mobile.ui.SyncAction
import uz.buildcontrol.mobile.ui.components.Badge
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.EmptyState
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.FormSheet
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.SearchField
import uz.buildcontrol.mobile.ui.components.UsageBar
import uz.buildcontrol.mobile.ui.theme.BcColors

fun projectStatusKind(status: String): String = when (status) {
    ProjectStatus.ACTIVE -> "success"
    ProjectStatus.PLANNED -> "info"
    ProjectStatus.SUSPENDED -> "warning"
    ProjectStatus.COMPLETED -> "accent"
    else -> "neutral"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectsScreen(user: CurrentUser, onOpenProject: (Long) -> Unit) {
    val container = BuildControlApp.container

    var query by remember { mutableStateOf("") }
    var showForm by remember { mutableStateOf(false) }
    var totals by remember { mutableStateOf(mapOf<Long, ProjectTotals>()) }

    val projects by container.projects.observeProjects(false)
        .collectAsStateWithLifecycle(initialValue = emptyList())

    LaunchedEffect(projects) {
        totals = projects.associate { it.id to container.projects.totals(it.id) }
    }

    val filtered = projects.filter {
        query.isBlank() ||
            it.name.contains(query, true) ||
            it.code.contains(query, true) ||
            (it.client ?: "").contains(query, true)
    }

    Scaffold(
        containerColor = BcColors.Background,
        topBar = {
            TopAppBar(
                title = { Text(tr("projects"), style = MaterialTheme.typography.titleLarge) },
                actions = { SyncAction() },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BcColors.BackgroundAlt,
                    titleContentColor = BcColors.Text,
                ),
            )
        },
        floatingActionButton = {
            if (user.can(Perm.PROJECT_EDIT)) {
                FloatingActionButton(
                    onClick = { showForm = true },
                    containerColor = BcColors.Accent,
                ) { Icon(Icons.Default.Add, contentDescription = tr("new_project")) }
            }
        },
    ) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).padding(horizontal = 14.dp)) {
            Spacer(Modifier.height(8.dp))
            SearchField(query, { query = it })
            Spacer(Modifier.height(10.dp))
            if (filtered.isEmpty()) {
                EmptyState()
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    items(filtered, key = { it.id }) { project ->
                        ProjectCard(project, totals[project.id]) { onOpenProject(project.id) }
                    }
                    item { Spacer(Modifier.height(80.dp)) }
                }
            }
        }
    }

    if (showForm) {
        ProjectFormSheet(
            user = user,
            initial = null,
            onDismiss = { showForm = false },
            onSaved = { showForm = false },
        )
    }
}

@Composable
private fun ProjectCard(project: ProjectRow, totals: ProjectTotals?, onClick: () -> Unit) {
    BcCard(onClick = onClick) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    project.name,
                    style = MaterialTheme.typography.titleMedium,
                    color = BcColors.Text,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    "${project.code} · ${project.client.orEmpty()}",
                    style = MaterialTheme.typography.bodySmall,
                    color = BcColors.TextMuted,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            Badge(I18n.enum("pstatus", project.status), projectStatusKind(project.status))
        }
        Spacer(Modifier.height(10.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Column {
                Text(tr("budget"), color = BcColors.TextFaint, style = MaterialTheme.typography.labelSmall)
                Text(
                    Fmt.money(project.plannedBudget),
                    color = BcColors.Text,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                )
            }
            Column(horizontalAlignment = Alignment.End) {
                Text(
                    tr("actual_cost"),
                    color = BcColors.TextFaint,
                    style = MaterialTheme.typography.labelSmall,
                )
                Text(
                    Fmt.money(totals?.actual ?: 0.0),
                    color = if (totals?.isOverBudget == true) BcColors.Danger else BcColors.Text,
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Medium,
                )
            }
        }
        Spacer(Modifier.height(8.dp))
        UsageBar(totals?.usageRatio ?: 0.0)
        if (totals != null) {
            Spacer(Modifier.height(6.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text(
                    Fmt.percent(totals.usageRatio * 100),
                    color = BcColors.TextMuted,
                    style = MaterialTheme.typography.labelSmall,
                )
                if (totals.delayedStages > 0) {
                    Text(
                        "${tr("delayed_stages")}: ${totals.delayedStages}",
                        color = BcColors.Danger,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
                if (totals.pendingPurchases > 0) {
                    Text(
                        "${tr("pending_purchases")}: ${totals.pendingPurchases}",
                        color = BcColors.Warning,
                        style = MaterialTheme.typography.labelSmall,
                    )
                }
            }
        }
    }
}

/** Create / edit form for a project. */
@Composable
fun ProjectFormSheet(
    user: CurrentUser,
    initial: ProjectRow?,
    onDismiss: () -> Unit,
    onSaved: (Long) -> Unit,
) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()

    var name by remember { mutableStateOf(initial?.name ?: "") }
    var client by remember { mutableStateOf(initial?.client ?: "") }
    var address by remember { mutableStateOf(initial?.address ?: "") }
    var budget by remember { mutableStateOf(initial?.plannedBudget?.let { Fmt.qty(it) } ?: "") }
    var type by remember { mutableStateOf(initial?.projectType ?: "renovation") }
    var status by remember { mutableStateOf(initial?.status ?: ProjectStatus.PLANNED) }
    var startDate by remember { mutableStateOf(initial?.startDate ?: Fmt.today()) }
    var endDate by remember { mutableStateOf(initial?.endDate ?: Fmt.plusDays(Fmt.today(), 90)) }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = if (initial == null) tr("new_project") else tr("edit"),
        onDismiss = onDismiss,
        error = error,
        onSave = {
            if (name.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    val row = (initial ?: ProjectRow()).copy(
                        name = name.trim(),
                        client = client.trim(),
                        address = address.trim(),
                        plannedBudget = Fmt.parseNumber(budget),
                        projectType = type,
                        status = status,
                        startDate = startDate.ifBlank { null },
                        endDate = endDate.ifBlank { null },
                    )
                    val id = container.projects.save(user, row)
                    onSaved(id)
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("project_name"), name, { name = it }, required = true)
        Field(tr("client"), client, { client = it })
        Field(tr("address"), address, { address = it })
        Field(tr("planned_budget"), budget, { budget = it }, numeric = true)
        Picker(
            tr("project_type"),
            ProjectType.all.map { it to I18n.enum("ptype", it) },
            type,
            { type = it },
        )
        Picker(
            tr("status"),
            ProjectStatus.all.map { it to I18n.enum("pstatus", it) },
            status,
            { status = it },
        )
        Field(tr("start_date"), startDate, { startDate = it })
        Field(tr("end_date"), endDate, { endDate = it })
    }
}
