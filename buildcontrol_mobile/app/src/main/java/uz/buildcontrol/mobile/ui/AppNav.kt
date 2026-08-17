package uz.buildcontrol.mobile.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Apartment
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material.icons.filled.SyncProblem
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.ui.screens.ExpensesScreen
import uz.buildcontrol.mobile.ui.screens.LoginScreen
import uz.buildcontrol.mobile.ui.screens.ProjectScreen
import uz.buildcontrol.mobile.ui.screens.ProjectsScreen
import uz.buildcontrol.mobile.ui.screens.SettingsScreen
import uz.buildcontrol.mobile.ui.screens.WarehouseScreen
import uz.buildcontrol.mobile.ui.theme.BcColors

private data class Tab(val route: String, val labelKey: String, val icon: ImageVector)

private val TABS = listOf(
    Tab("projects", "nav_projects", Icons.Default.Apartment),
    Tab("warehouse", "nav_warehouse", Icons.Default.Inventory2),
    Tab("expenses", "nav_expenses", Icons.Default.Payments),
    Tab("settings", "nav_settings", Icons.Default.Settings),
)

/** Root composable: login gate, bottom navigation and the sync indicator. */
@Composable
fun AppRoot() {
    var user by remember { mutableStateOf<CurrentUser?>(null) }
    var settingsFromLogin by remember { mutableStateOf(false) }
    val container = BuildControlApp.container

    LaunchedEffect(user) {
        if (user != null) container.sync.syncIfAuto()
    }

    val current = user
    when {
        current != null -> MainScaffold(current) { user = null }
        settingsFromLogin -> SettingsScreen(
            user = null,
            onLogout = {},
            onBack = { settingsFromLogin = false },
        )
        else -> LoginScreen(
            onSignedIn = { user = it },
            onOpenSettings = { settingsFromLogin = true },
        )
    }
}

@Composable
private fun MainScaffold(user: CurrentUser, onLogout: () -> Unit) {
    val nav = rememberNavController()
    val snackbar = remember { SnackbarHostState() }
    Scaffold(
        containerColor = BcColors.Background,
        bottomBar = { BottomBar(nav) },
        snackbarHost = { SnackbarHost(snackbar) },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            NavHost(navController = nav, startDestination = "projects") {
                composable("projects") {
                    ProjectsScreen(
                        user = user,
                        onOpenProject = { id -> nav.navigate("project/$id") },
                    )
                }
                composable(
                    route = "project/{id}",
                    arguments = listOf(navArgument("id") { type = NavType.LongType }),
                ) { entry ->
                    ProjectScreen(
                        user = user,
                        projectId = entry.arguments?.getLong("id") ?: 0L,
                        onBack = { nav.popBackStack() },
                    )
                }
                composable("warehouse") { WarehouseScreen(user) }
                composable("expenses") { ExpensesScreen(user, projectId = null) }
                composable("settings") {
                    SettingsScreen(user = user, onLogout = onLogout, onBack = null)
                }
            }
        }
    }
}

@Composable
private fun BottomBar(nav: NavHostController) {
    val entry by nav.currentBackStackEntryAsState()
    val route = entry?.destination?.route.orEmpty()
    NavigationBar(containerColor = BcColors.Sidebar, tonalElevation = 0.dp) {
        TABS.forEach { tab ->
            val selected = route == tab.route || route.startsWith(tab.route + "/")
            NavigationBarItem(
                selected = selected,
                onClick = {
                    if (!selected) {
                        nav.navigate(tab.route) {
                            popUpTo(nav.graph.startDestinationId) { saveState = true }
                            launchSingleTop = true
                            restoreState = true
                        }
                    }
                },
                icon = { Icon(tab.icon, contentDescription = tr(tab.labelKey)) },
                label = { Text(tr(tab.labelKey), style = MaterialTheme.typography.labelSmall) },
                colors = NavigationBarItemDefaults.colors(
                    selectedIconColor = BcColors.Accent,
                    selectedTextColor = BcColors.Text,
                    indicatorColor = BcColors.AccentSoft,
                    unselectedIconColor = BcColors.TextMuted,
                    unselectedTextColor = BcColors.TextFaint,
                ),
            )
        }
    }
}

/** Sync status button shown in every screen's top bar. */
@Composable
fun SyncAction(modifier: Modifier = Modifier) {
    val container = BuildControlApp.container
    val state by container.sync.state.collectAsStateWithLifecycle()
    val pending by container.db.syncDao().observePendingCount()
        .collectAsStateWithLifecycle(initialValue = 0)

    Row(verticalAlignment = Alignment.CenterVertically, modifier = modifier) {
        if (pending > 0) {
            Text(
                pending.toString(),
                color = BcColors.Warning,
                style = MaterialTheme.typography.labelSmall,
            )
            Spacer(Modifier.width(4.dp))
        }
        IconButton(onClick = { container.sync.syncNow() }) {
            when {
                state.running -> CircularProgressIndicator(
                    Modifier.size(18.dp),
                    color = BcColors.Warning,
                    strokeWidth = 2.dp,
                )
                state.failed -> Icon(Icons.Default.SyncProblem, null, tint = BcColors.Danger)
                else -> Icon(
                    Icons.Default.Sync,
                    null,
                    tint = if (pending > 0) BcColors.Warning else BcColors.TextMuted,
                )
            }
        }
    }
}

/** Background tint helper used by list rows. */
@Composable
fun rowBackground(index: Int): Modifier =
    Modifier.background(if (index % 2 == 0) BcColors.Surface else BcColors.SurfaceAlt)

@Composable
fun FullScreenBox(content: @Composable () -> Unit) {
    Box(Modifier.fillMaxSize().background(BcColors.Background)) { content() }
}
