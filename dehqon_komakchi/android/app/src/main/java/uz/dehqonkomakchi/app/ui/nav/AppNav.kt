package uz.dehqonkomakchi.app.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CameraAlt
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.automirrored.filled.MenuBook
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.ui.diagnose.DiagnoseScreen
import uz.dehqonkomakchi.app.ui.irrigation.IrrigationScreen
import uz.dehqonkomakchi.app.ui.ledger.LedgerScreen
import uz.dehqonkomakchi.app.ui.market.MarketScreen
import uz.dehqonkomakchi.app.ui.onboarding.OnboardingScreen
import uz.dehqonkomakchi.app.ui.settings.PrivacyPolicyScreen
import uz.dehqonkomakchi.app.ui.settings.SettingsScreen
import uz.dehqonkomakchi.app.ui.settings.TermsScreen

private data class BottomTab(val route: String, val labelRes: Int, val icon: androidx.compose.ui.graphics.vector.ImageVector)

private val bottomTabs = listOf(
    BottomTab(Routes.DIAGNOSE, R.string.nav_diagnose, Icons.Filled.CameraAlt),
    BottomTab(Routes.IRRIGATION, R.string.nav_irrigation, Icons.Filled.WaterDrop),
    BottomTab(Routes.LEDGER, R.string.nav_ledger, Icons.AutoMirrored.Filled.MenuBook),
    BottomTab(Routes.MARKET, R.string.nav_market, Icons.Filled.Storefront),
    BottomTab(Routes.SETTINGS, R.string.nav_settings, Icons.Filled.Settings),
)

@Composable
fun DehqonNavHost(userPrefs: UserPrefs) {
    val settings by userPrefs.settings.collectAsState(initial = null)
    val navController = rememberNavController()

    val startDestination = when (settings?.onboardingComplete) {
        true -> Routes.HOME
        false -> Routes.ONBOARDING
        null -> null // still loading
    }

    if (startDestination == null) return

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Routes.ONBOARDING) {
            OnboardingScreen(onComplete = {
                navController.navigate(Routes.HOME) {
                    popUpTo(Routes.ONBOARDING) { inclusive = true }
                }
            })
        }
        composable(Routes.HOME) { HomeScaffold() }
    }
}

@Composable
private fun HomeScaffold() {
    val navController = rememberNavController()

    Scaffold(
        bottomBar = {
            val navBackStackEntry by navController.currentBackStackEntryAsState()
            val currentDestination = navBackStackEntry?.destination
            NavigationBar {
                bottomTabs.forEach { tab ->
                    val selected = currentDestination?.hierarchy?.any { it.route == tab.route } == true
                    NavigationBarItem(
                        selected = selected,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = stringResource(tab.labelRes)) },
                        label = { Text(stringResource(tab.labelRes)) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Routes.DIAGNOSE,
            modifier = Modifier.padding(padding),
        ) {
            composable(Routes.DIAGNOSE) { DiagnoseScreen() }
            composable(Routes.IRRIGATION) { IrrigationScreen() }
            composable(Routes.LEDGER) { LedgerScreen() }
            composable(Routes.MARKET) { MarketScreen() }
            composable(Routes.SETTINGS) {
                SettingsScreen(
                    onOpenPrivacy = { navController.navigate(Routes.PRIVACY_POLICY) },
                    onOpenTerms = { navController.navigate(Routes.TERMS) },
                )
            }
            composable(Routes.PRIVACY_POLICY) { PrivacyPolicyScreen() }
            composable(Routes.TERMS) { TermsScreen() }
        }
    }
}
