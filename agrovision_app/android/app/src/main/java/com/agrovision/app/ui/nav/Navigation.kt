package com.agrovision.app.ui.nav

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.ui.graphics.vector.ImageVector

object Routes {
    const val LOGIN = "login"
    const val DASHBOARD = "dashboard"
    const val MAP = "map"
    const val ANALYTICS = "analytics"
    const val ML = "ml"
    const val SATELLITE = "satellite"
    const val WEATHER = "weather"
    const val MARKET = "market"
    const val IRRIGATION = "irrigation"
    const val FINANCE = "finance"
    const val AI = "ai"
    const val RECORDS = "records"
    const val REPORTS = "reports"
    const val IMPORT = "import"
    const val SOIL = "soil"
    const val ADMIN = "admin"
    const val SETTINGS = "settings"
}

data class NavItem(
    val route: String,
    val label: String,
    val icon: ImageVector,
    val permission: String,
    val group: String,
)

/** Yon menyu — desktop 14 sahifasi + Ma'lumotlar/Import/Tuproq tahlili. */
val NAV_ITEMS = listOf(
    NavItem(Routes.DASHBOARD, "Bosh sahifa", Icons.Filled.SpaceDashboard, "view_dashboard", "Umumiy"),
    NavItem(Routes.MAP, "Xarita", Icons.Filled.Map, "view_dashboard", "Umumiy"),
    NavItem(Routes.ANALYTICS, "Analitika", Icons.Filled.Insights, "view_dashboard", "Tahlil"),
    NavItem(Routes.ML, "Machine Learning", Icons.Filled.Psychology, "view_dashboard", "Tahlil"),
    NavItem(Routes.AI, "AI Yordamchi", Icons.Filled.SmartToy, "use_ai", "Tahlil"),
    NavItem(Routes.SATELLITE, "Sun'iy yo'ldosh", Icons.Filled.SatelliteAlt, "view_dashboard", "Monitoring"),
    NavItem(Routes.WEATHER, "Ob-havo", Icons.Filled.WbCloudy, "view_dashboard", "Monitoring"),
    NavItem(Routes.IRRIGATION, "Sug'orish", Icons.Filled.WaterDrop, "view_dashboard", "Monitoring"),
    NavItem(Routes.SOIL, "Tuproq tahlili", Icons.Filled.Grass, "view_dashboard", "Monitoring"),
    NavItem(Routes.MARKET, "Bozor", Icons.Filled.Storefront, "view_dashboard", "Iqtisod"),
    NavItem(Routes.FINANCE, "Moliya", Icons.Filled.Payments, "view_finance", "Iqtisod"),
    NavItem(Routes.RECORDS, "Ma'lumotlar", Icons.Filled.PlaylistAdd, "edit_data", "Boshqaruv"),
    NavItem(Routes.IMPORT, "Import", Icons.Filled.UploadFile, "import_data", "Boshqaruv"),
    NavItem(Routes.REPORTS, "Hisobotlar", Icons.Filled.Description, "export_reports", "Boshqaruv"),
    NavItem(Routes.ADMIN, "Administrator", Icons.Filled.AdminPanelSettings, "manage_users", "Boshqaruv"),
    NavItem(Routes.SETTINGS, "Sozlamalar", Icons.Filled.Settings, "manage_settings", "Boshqaruv"),
)
