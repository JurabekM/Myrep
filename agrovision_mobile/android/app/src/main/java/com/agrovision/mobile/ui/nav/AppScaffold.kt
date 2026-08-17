package com.agrovision.mobile.ui.nav

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Agriculture
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material.icons.filled.WifiOff
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavHostController
import com.agrovision.mobile.core.NetworkStatus
import com.agrovision.mobile.core.Rbac
import com.agrovision.mobile.core.Session
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AppScaffold(
    navController: NavHostController,
    title: String,
    onLogout: () -> Unit,
    content: @Composable (PaddingValues) -> Unit,
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val role = Session.current?.role

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            ModalDrawerSheet {
                Row(Modifier.padding(20.dp), verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Filled.Agriculture, contentDescription = null)
                    Spacer(Modifier.width(10.dp))
                    Column {
                        Text("AgroVision", style = MaterialTheme.typography.titleLarge)
                        Text("Mobil", style = MaterialTheme.typography.labelSmall)
                    }
                }
                HorizontalDivider()
                NAV_ITEMS.filter { Rbac.has(role, it.permission) }.forEach { item ->
                    NavigationDrawerItem(
                        icon = { Icon(item.icon, contentDescription = null) },
                        label = { Text(item.label) },
                        selected = false,
                        onClick = {
                            scope.launch { drawerState.close() }
                            navController.navigate(item.route) {
                                launchSingleTop = true
                                popUpTo(Routes.DASHBOARD) { inclusive = false }
                            }
                        },
                        modifier = Modifier.padding(horizontal = 8.dp),
                    )
                }
                HorizontalDivider(Modifier.padding(vertical = 8.dp))
                NavigationDrawerItem(
                    icon = { Icon(Icons.Filled.Logout, contentDescription = null) },
                    label = { Text("Chiqish") },
                    selected = false,
                    onClick = onLogout,
                    modifier = Modifier.padding(horizontal = 8.dp),
                )
            }
        },
    ) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(title) },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Filled.Menu, contentDescription = "Menyu")
                        }
                    },
                    actions = {
                        val context = LocalContext.current
                        val online = remember { NetworkStatus.isOnline(context) }
                        AssistChip(
                            onClick = {},
                            enabled = false,
                            leadingIcon = {
                                Icon(
                                    if (online) Icons.Filled.Wifi else Icons.Filled.WifiOff,
                                    contentDescription = null, modifier = Modifier.size(16.dp),
                                )
                            },
                            label = { Text(if (online) "Onlayn" else "Offlayn", style = MaterialTheme.typography.labelSmall) },
                            modifier = Modifier.padding(end = 8.dp),
                        )
                    },
                )
            },
        ) { padding ->
            content(padding)
        }
    }
}
