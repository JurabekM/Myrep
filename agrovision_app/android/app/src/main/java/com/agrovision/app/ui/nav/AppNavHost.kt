package com.agrovision.app.ui.nav

import androidx.compose.runtime.Composable
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.agrovision.app.core.Session
import com.agrovision.app.ui.screens.*

@Composable
fun AppNavHost(onThemeChanged: (String) -> Unit) {
    val navController = rememberNavController()
    val logout: () -> Unit = {
        Session.logout()
        navController.navigate(Routes.LOGIN) { popUpTo(0) { inclusive = true } }
    }

    NavHost(navController = navController, startDestination = Routes.LOGIN) {
        composable(Routes.LOGIN) { LoginScreen(navController) }
        composable(Routes.DASHBOARD) { DashboardScreen(navController, logout) }
        composable(Routes.MAP) { MapScreen(navController, logout) }
        composable(Routes.ANALYTICS) { AnalyticsScreen(navController, logout) }
        composable(Routes.ML) { MlScreen(navController, logout) }
        composable(Routes.AI) { AiScreen(navController, logout) }
        composable(Routes.SATELLITE) { SatelliteScreen(navController, logout) }
        composable(Routes.WEATHER) { WeatherScreen(navController, logout) }
        composable(Routes.IRRIGATION) { IrrigationScreen(navController, logout) }
        composable(Routes.SOIL) { SoilScreen(navController, logout) }
        composable(Routes.MARKET) { MarketScreen(navController, logout) }
        composable(Routes.FINANCE) { FinanceScreen(navController, logout) }
        composable(Routes.RECORDS) { RecordsScreen(navController, logout) }
        composable(Routes.IMPORT) { ImportScreen(navController, logout) }
        composable(Routes.REPORTS) { ReportsScreen(navController, logout) }
        composable(Routes.ADMIN) { AdminScreen(navController, logout) }
        composable(Routes.SETTINGS) { SettingsScreen(navController, logout, onThemeChanged) }
    }
}
