package uz.sectorverify.app

import androidx.compose.runtime.Composable

/** Release builds: no debug screen. */
object DebugRoutes {
    const val ENABLED = false

    @Composable
    fun Screen() = Unit
}
