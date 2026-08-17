package com.agrovision.app.ui.nav

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.agrovision.app.core.I18n
import com.agrovision.app.core.NetworkStatus
import com.agrovision.app.core.Rbac
import com.agrovision.app.core.Session
import com.agrovision.app.data.local.SearchRow
import com.agrovision.app.ui.common.DataTable
import com.agrovision.app.ui.common.EmptyState
import kotlinx.coroutines.launch

/**
 * Ilova karkasi: yon menyu (drawer), yuqori panel, global qidiruv va
 * onlayn/offlayn ko'rsatkichi. Barcha ekranlar shu karkas ichida ochiladi.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScaffold(
    navController: NavHostController,
    title: String,
    onLogout: () -> Unit,
    onSearch: (suspend (String) -> List<SearchRow>)? = null,
    actions: @Composable RowScope.() -> Unit = {},
    content: @Composable (PaddingValues) -> Unit,
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    val role = Session.current?.role
    var searchVisible by remember { mutableStateOf(false) }
    var searchQuery by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf<List<SearchRow>>(emptyList()) }
    val online = remember { NetworkStatus.hasNetwork(context) }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet(Modifier.width(292.dp)) {
                DrawerHeader()
                HorizontalDivider()
                Column(Modifier.weight(1f).verticalScroll(rememberScrollState())) {
                    NAV_ITEMS.filter { Rbac.has(role, it.permission) }
                        .groupBy { it.group }
                        .forEach { (group, items) ->
                            Text(
                                I18n.t(group),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                modifier = Modifier.padding(start = 24.dp, top = 12.dp, bottom = 4.dp),
                            )
                            items.forEach { item ->
                                NavigationDrawerItem(
                                    icon = { Icon(item.icon, contentDescription = null) },
                                    label = { Text(I18n.t(item.label)) },
                                    selected = title == I18n.t(item.label),
                                    onClick = {
                                        scope.launch { drawerState.close() }
                                        if (title != I18n.t(item.label)) {
                                            navController.navigate(item.route) {
                                                launchSingleTop = true
                                                popUpTo(Routes.DASHBOARD) { inclusive = false }
                                            }
                                        }
                                    },
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 1.dp),
                                )
                            }
                        }
                }
                HorizontalDivider()
                NavigationDrawerItem(
                    icon = { Icon(Icons.Filled.Logout, contentDescription = null) },
                    label = { Text(I18n.t("Chiqish")) },
                    selected = false,
                    onClick = onLogout,
                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                )
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(title, maxLines = 1) },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Filled.Menu, contentDescription = "Menyu")
                        }
                    },
                    actions = {
                        if (onSearch != null) {
                            IconButton(onClick = { searchVisible = true }) {
                                Icon(Icons.Filled.Search, contentDescription = I18n.t("Qidiruv"))
                            }
                        }
                        actions()
                        Icon(
                            imageVector = if (online) Icons.Filled.CloudDone else Icons.Filled.CloudOff,
                            contentDescription = if (online) "Onlayn" else "Offlayn",
                            tint = MaterialTheme.colorScheme.onSurfaceVariant,
                            modifier = Modifier.padding(end = 12.dp).size(20.dp),
                        )
                    },
                )
            },
            content = content,
        )
    }

    if (searchVisible && onSearch != null) {
        AlertDialog(
            onDismissRequest = { searchVisible = false; searchQuery = ""; searchResults = emptyList() },
            title = { Text(I18n.t("Qidiruv")) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = searchQuery,
                        onValueChange = { query ->
                            searchQuery = query
                            scope.launch { searchResults = onSearch(query) }
                        },
                        label = { Text("Fermer, xo'jalik, dala, ekin, hudud…") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth(),
                    )
                    if (searchQuery.isNotBlank() && searchResults.isEmpty()) {
                        EmptyState("Hech narsa topilmadi.")
                    } else if (searchResults.isNotEmpty()) {
                        Box(Modifier.heightIn(max = 320.dp).verticalScroll(rememberScrollState())) {
                            DataTable(
                                headers = listOf("Turi", "Nomi", "Tafsilot"),
                                rows = searchResults.map { listOf(it.turi, it.nomi, it.tafsilot) },
                                weights = listOf(0.8f, 1.2f, 1.6f),
                            )
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = { searchVisible = false; searchQuery = ""; searchResults = emptyList() }) {
                    Text("Yopish")
                }
            },
        )
    }
}

@Composable
private fun DrawerHeader() {
    val user = Session.current
    Row(Modifier.fillMaxWidth().padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(
            Modifier.size(44.dp).background(MaterialTheme.colorScheme.primary, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(
                Icons.Filled.Agriculture,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onPrimary,
                modifier = Modifier.size(24.dp),
            )
        }
        Spacer(Modifier.width(12.dp))
        Column {
            Text("AgroVision", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
            Text(
                user?.let { "${it.fullName} · ${Rbac.label(it.role)}" } ?: "Qishloq xo'jaligi platformasi",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
            )
        }
    }
}
