package com.agrovision.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val AgroGreen = Color(0xFF2E7D32)
val AgroGreenDark = Color(0xFF1B5E20)
val AgroGreenLight = Color(0xFF66BB6A)
val AgroAmber = Color(0xFFF9A825)
val AgroOrange = Color(0xFFEF6C00)
val AgroBlue = Color(0xFF0288D1)
val AgroRed = Color(0xFFC62828)
val AgroTeal = Color(0xFF00897B)
val AgroPurple = Color(0xFF7B1FA2)

/** Grafiklar uchun palitra — desktop `app/theme.py` PALETTE bilan bir xil. */
val ChartPalette = listOf(
    AgroGreen, AgroGreenLight, AgroAmber, AgroOrange,
    AgroBlue, AgroPurple, AgroRed, AgroTeal,
    Color(0xFF5D4037), Color(0xFF3949AB),
)

/** Hosildorlik/NDVI kartogrammasi uchun uch bosqichli shkala. */
val MetricLow = AgroRed
val MetricMid = AgroAmber
val MetricHigh = AgroGreen

private val LightColors = lightColorScheme(
    primary = AgroGreen,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFC8E6C9),
    onPrimaryContainer = AgroGreenDark,
    secondary = AgroTeal,
    tertiary = AgroAmber,
    error = AgroRed,
    background = Color(0xFFF6FAF3),
    onBackground = Color(0xFF1A1C18),
    surface = Color.White,
    surfaceVariant = Color(0xFFE7EFE3),
    onSurfaceVariant = Color(0xFF43483F),
)

private val DarkColors = darkColorScheme(
    primary = AgroGreenLight,
    onPrimary = Color(0xFF00390B),
    primaryContainer = Color(0xFF1B5E20),
    onPrimaryContainer = Color(0xFFC8E6C9),
    secondary = Color(0xFF4DB6AC),
    tertiary = Color(0xFFFFD54F),
    error = Color(0xFFEF9A9A),
    background = Color(0xFF10140F),
    onBackground = Color(0xFFE2E3DD),
    surface = Color(0xFF1A1F18),
    surfaceVariant = Color(0xFF2A2F27),
    onSurfaceVariant = Color(0xFFC2C8BC),
)

@Composable
fun AgroVisionTheme(
    themeMode: String = "system",
    content: @Composable () -> Unit,
) {
    val dark = when (themeMode) {
        "dark" -> true
        "light" -> false
        else -> isSystemInDarkTheme()
    }
    MaterialTheme(colorScheme = if (dark) DarkColors else LightColors, content = content)
}
