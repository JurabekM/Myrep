package uz.sectorverify.app

import androidx.compose.runtime.Composable
import uz.sectorverify.feature.survey.debug.DebugScreen

/** Faqat debug build'lar uchun: 2-bosqich yig'ish debug ekrani. */
object DebugRoutes {
    const val ENABLED = true

    @Composable
    fun Screen() = DebugScreen()
}
