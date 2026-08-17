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
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
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
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.data.db.MaterialRow
import uz.buildcontrol.mobile.data.db.WarehouseTxRow
import uz.buildcontrol.mobile.data.repo.StockException
import uz.buildcontrol.mobile.data.repo.WarehouseRepository
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.TxKind
import uz.buildcontrol.mobile.domain.Units
import uz.buildcontrol.mobile.ui.SyncAction
import uz.buildcontrol.mobile.ui.components.Badge
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.EmptyState
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.FormSheet
import uz.buildcontrol.mobile.ui.components.KeyValue
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.SearchField
import uz.buildcontrol.mobile.ui.theme.BcColors

fun txKind(kind: String): String = when (kind) {
    TxKind.IN -> "success"
    TxKind.OUT -> "info"
    TxKind.RETURN -> "accent"
    TxKind.ADJUST -> "warning"
    else -> "danger"
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WarehouseScreen(
    user: CurrentUser,
    projectId: Long? = null,
    embedded: Boolean = false,
) {
    val container = BuildControlApp.container
    var tab by remember { mutableIntStateOf(if (projectId == null) 0 else 1) }
    var query by remember { mutableStateOf("") }
    var addingMove by remember { mutableStateOf(false) }
    var addingMaterial by remember { mutableStateOf(false) }

    val stock by container.warehouse.observeStock()
        .collectAsStateWithLifecycle(initialValue = emptyList())
    val moves by (
        if (projectId == null) container.warehouse.observeMoves()
        else container.warehouse.observeMovesForProject(projectId)
        ).collectAsStateWithLifecycle(initialValue = emptyList())

    val body: @Composable (Modifier) -> Unit = { modifier ->
        Column(modifier.fillMaxSize()) {
            if (projectId == null) {
                TabRow(
                    selectedTabIndex = tab,
                    containerColor = BcColors.BackgroundAlt,
                    contentColor = BcColors.Accent,
                ) {
                    listOf("materials", "movements").forEachIndexed { index, key ->
                        Tab(
                            selected = tab == index,
                            onClick = { tab = index },
                            text = {
                                Text(
                                    tr(key),
                                    color = if (tab == index) BcColors.Text else BcColors.TextMuted,
                                )
                            },
                        )
                    }
                }
            }
            if (tab == 0 && projectId == null) {
                Column(Modifier.padding(horizontal = 14.dp)) {
                    Spacer(Modifier.height(8.dp))
                    SearchField(query, { query = it })
                    Spacer(Modifier.height(8.dp))
                }
                val filtered = stock.filter {
                    query.isBlank() || it.material.name.contains(query, true) ||
                        it.material.sku.contains(query, true)
                }
                if (filtered.isEmpty()) EmptyState()
                LazyColumn(
                    Modifier.padding(horizontal = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(filtered, key = { it.material.id }) { row -> StockCard(row) }
                    item { Spacer(Modifier.height(90.dp)) }
                }
            } else {
                if (moves.isEmpty()) EmptyState()
                LazyColumn(
                    Modifier.padding(horizontal = 14.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    item { Spacer(Modifier.height(6.dp)) }
                    items(moves, key = { it.id }) { move -> MoveCard(move, stock) }
                    item { Spacer(Modifier.height(90.dp)) }
                }
            }
        }
    }

    if (embedded) {
        Scaffold(
            containerColor = BcColors.Background,
            floatingActionButton = {
                if (user.can(Perm.WAREHOUSE_EDIT)) {
                    FloatingActionButton(
                        onClick = { addingMove = true },
                        containerColor = BcColors.Accent,
                    ) { Icon(Icons.Default.Add, contentDescription = tr("new_movement")) }
                }
            },
        ) { padding -> body(Modifier.padding(padding)) }
    } else {
        Scaffold(
            containerColor = BcColors.Background,
            topBar = {
                TopAppBar(
                    title = { Text(tr("nav_warehouse")) },
                    actions = { SyncAction() },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = BcColors.BackgroundAlt,
                        titleContentColor = BcColors.Text,
                    ),
                )
            },
            floatingActionButton = {
                if (user.can(Perm.WAREHOUSE_EDIT)) {
                    FloatingActionButton(
                        onClick = { if (tab == 0) addingMaterial = true else addingMove = true },
                        containerColor = BcColors.Accent,
                    ) { Icon(Icons.Default.Add, contentDescription = null) }
                }
            },
        ) { padding -> body(Modifier.padding(padding)) }
    }

    if (addingMove) {
        MoveSheet(user, projectId) { addingMove = false }
    }
    if (addingMaterial) {
        MaterialSheet(user) { addingMaterial = false }
    }
}

@Composable
private fun StockCard(row: WarehouseRepository.StockRow) {
    BcCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    row.material.name,
                    style = MaterialTheme.typography.titleSmall,
                    color = BcColors.Text,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    "${row.material.sku} · ${row.material.category.orEmpty()}",
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                )
            }
            if (row.isLow) Badge(tr("low_stock"), "danger")
        }
        Spacer(Modifier.height(6.dp))
        KeyValue(
            tr("stock"),
            "${Fmt.qty(row.balance)} ${I18n.enum("unit", row.material.unit)}",
            if (row.isLow) BcColors.Danger else BcColors.Success,
        )
        KeyValue(tr("min_stock"), Fmt.qty(row.material.minStock))
        KeyValue(tr("stock_value"), Fmt.money(row.value))
    }
}

@Composable
private fun MoveCard(move: WarehouseTxRow, stock: List<WarehouseRepository.StockRow>) {
    val material = stock.firstOrNull { it.material.id == move.materialId }?.material
    BcCard {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column(Modifier.weight(1f)) {
                Text(
                    material?.name ?: "—",
                    style = MaterialTheme.typography.titleSmall,
                    color = BcColors.Text,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Text(
                    Fmt.date(move.txDate),
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                )
            }
            Badge(I18n.enum("tx", move.kind), txKind(move.kind))
        }
        Spacer(Modifier.height(6.dp))
        KeyValue(
            tr("quantity"),
            "${Fmt.qty(move.quantity)} ${I18n.enum("unit", material?.unit ?: "piece")}",
        )
        KeyValue(tr("total"), Fmt.money(move.total))
        if (!move.note.isNullOrBlank()) {
            Text(move.note, style = MaterialTheme.typography.bodySmall, color = BcColors.TextMuted)
        }
    }
}

@Composable
private fun MoveSheet(user: CurrentUser, projectId: Long?, onDone: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var materials by remember { mutableStateOf(listOf<MaterialRow>()) }
    var projects by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var items by remember { mutableStateOf(listOf<Pair<Long?, String>>()) }
    var materialId by remember { mutableStateOf<Long?>(null) }
    var kind by remember { mutableStateOf(TxKind.IN) }
    var qty by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var chosenProject by remember { mutableStateOf(projectId) }
    var itemId by remember { mutableStateOf<Long?>(null) }
    var note by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }

    LaunchedEffect(Unit) {
        materials = container.warehouse.materials()
        materialId = materials.firstOrNull()?.id
        projects = listOf<Pair<Long?, String>>(null to "—") +
            container.projects.projects().map { it.id as Long? to it.name }
    }
    LaunchedEffect(chosenProject) {
        items = listOf<Pair<Long?, String>>(null to "—") +
            (chosenProject?.let { pid ->
                container.estimates.items(pid).map { it.id as Long? to it.name }
            } ?: emptyList())
    }
    LaunchedEffect(materialId) {
        val material = materials.firstOrNull { it.id == materialId }
        if (material != null && price.isBlank()) price = Fmt.qty(material.standardPrice)
    }

    FormSheet(
        title = tr("new_movement"),
        onDismiss = onDone,
        error = error,
        onSave = {
            val chosen = materialId
            if (chosen == null || qty.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.warehouse.registerMove(
                        user,
                        WarehouseTxRow(
                            txDate = Fmt.today(),
                            kind = kind,
                            materialId = chosen,
                            quantity = Fmt.parseNumber(qty),
                            unitPrice = Fmt.parseNumber(price),
                            projectId = chosenProject,
                            estimateItemId = itemId,
                            note = note.trim(),
                        ),
                    )
                    onDone()
                } catch (exc: StockException) {
                    error = tr(exc.key)
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Picker(
            tr("material"),
            materials.map { it.id as Long? to "${it.sku} — ${it.name}" },
            materialId,
            { materialId = it },
        )
        Picker(tr("type"), TxKind.all.map { it to I18n.enum("tx", it) }, kind, { kind = it })
        Field(tr("quantity"), qty, { qty = it }, numeric = true, required = true)
        Field(tr("unit_price"), price, { price = it }, numeric = true)
        if (projectId == null) {
            Picker(tr("project"), projects, chosenProject, { chosenProject = it })
        }
        Picker(tr("estimate_item"), items, itemId, { itemId = it })
        Field(tr("note"), note, { note = it }, singleLine = false)
    }
}

@Composable
private fun MaterialSheet(user: CurrentUser, onDone: () -> Unit) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()
    var sku by remember { mutableStateOf("") }
    var name by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("") }
    var unit by remember { mutableStateOf("piece") }
    var minStock by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var error by remember { mutableStateOf("") }

    FormSheet(
        title = tr("new_material"),
        onDismiss = onDone,
        error = error,
        onSave = {
            if (sku.isBlank() || name.isBlank()) {
                error = tr("required_field")
                return@FormSheet
            }
            scope.launch {
                try {
                    container.warehouse.saveMaterial(
                        user,
                        MaterialRow(
                            sku = sku.trim(),
                            name = name.trim(),
                            category = category.trim(),
                            unit = unit,
                            minStock = Fmt.parseNumber(minStock),
                            standardPrice = Fmt.parseNumber(price),
                        ),
                    )
                    onDone()
                } catch (exc: StockException) {
                    error = tr(exc.key)
                } catch (exc: Exception) {
                    error = exc.message ?: "error"
                }
            }
        },
    ) {
        Field(tr("sku"), sku, { sku = it }, required = true)
        Field(tr("name"), name, { name = it }, required = true)
        Field(tr("category"), category, { category = it })
        Picker(tr("unit"), Units.all.map { it to I18n.enum("unit", it) }, unit, { unit = it })
        Field(tr("min_stock"), minStock, { minStock = it }, numeric = true)
        Field(tr("standard_price"), price, { price = it }, numeric = true)
    }
}
