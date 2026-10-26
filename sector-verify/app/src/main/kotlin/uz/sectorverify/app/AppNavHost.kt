package uz.sectorverify.app

import androidx.compose.runtime.Composable
import androidx.compose.ui.res.stringResource
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import uz.sectorverify.feature.plan.SiteCardRoute
import uz.sectorverify.feature.plan.SitesRoute
import uz.sectorverify.feature.report.ReportRoute
import uz.sectorverify.feature.report.ResultRoute
import uz.sectorverify.feature.settings.SettingsRoute
import uz.sectorverify.feature.survey.ui.LiveRoute
import uz.sectorverify.feature.survey.ui.PreCheckRoute
import uz.sectorverify.model.SessionMode
import uz.sectorverify.ui.components.SecondaryButton

object Routes {
    const val SITES = "sites"
    const val SITE = "site/{siteId}"
    const val PRECHECK = "precheck/{siteId}?mode={mode}"
    const val LIVE = "live/{sessionId}"
    const val RESULT = "result/{sessionId}"
    const val REPORT = "report/{sessionId}"
    const val SETTINGS = "settings"
    const val DEBUG = "debug"

    fun site(id: Long) = "site/$id"

    fun precheck(siteId: Long, mode: SessionMode) = "precheck/$siteId?mode=${mode.name}"

    fun live(id: String) = "live/$id"

    fun result(id: String) = "result/$id"

    fun report(id: String) = "report/$id"
}

@Composable
fun AppNavHost(onLanguageChanged: () -> Unit, nav: NavHostController = rememberNavController()) {
    val siteArg = navArgument("siteId") { type = NavType.LongType }
    val sessionArg = navArgument("sessionId") { type = NavType.StringType }
    NavHost(nav, startDestination = Routes.SITES) {
        composable(Routes.SITES) {
            SitesRoute(
                onOpenSite = { nav.navigate(Routes.site(it)) },
                onSettings = { nav.navigate(Routes.SETTINGS) },
                onResumed = { nav.navigate(Routes.live(it)) },
            )
        }
        composable(Routes.SITE, listOf(siteArg)) {
            SiteCardRoute(
                onPreCheck = { nav.navigate(Routes.precheck(it, SessionMode.FULL)) },
                onOpenSession = { nav.navigate(Routes.result(it)) },
            )
        }
        composable(
            Routes.PRECHECK,
            listOf(
                siteArg,
                navArgument("mode") {
                    type = NavType.StringType
                    defaultValue = SessionMode.FULL.name
                },
            ),
        ) {
            PreCheckRoute(onStarted = { id -> nav.navigate(Routes.live(id)) { popUpTo(Routes.SITE) } })
        }
        composable(Routes.LIVE, listOf(sessionArg)) {
            LiveRoute(onFinished = { id -> nav.navigate(Routes.result(id)) { popUpTo(Routes.SITE) } })
        }
        composable(Routes.RESULT, listOf(sessionArg)) {
            ResultRoute(
                onRecheck = { siteId -> nav.navigate(Routes.precheck(siteId, SessionMode.RECHECK)) },
                onReport = { nav.navigate(Routes.report(it)) },
            )
        }
        composable(Routes.REPORT, listOf(sessionArg)) { ReportRoute() }
        composable(Routes.SETTINGS) {
            SettingsRoute(
                onLanguageChanged = onLanguageChanged,
                extra = {
                    if (DebugRoutes.ENABLED) SecondaryButton(stringResource(R.string.debug_open), { nav.navigate(Routes.DEBUG) })
                },
            )
        }
        if (DebugRoutes.ENABLED) composable(Routes.DEBUG) { DebugRoutes.Screen() }
    }
}
