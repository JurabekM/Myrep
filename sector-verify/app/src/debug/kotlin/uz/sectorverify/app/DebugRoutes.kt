package uz.sectorverify.app

import androidx.compose.runtime.Composable
import uz.sectorverify.feature.survey.debug.DebugScreen

/** Debug builds only: the phase-2 collection debug screen. */
object DebugRoutes {
    const val ENABLED = true

    @Composable
    fun Screen() = DebugScreen()
}
