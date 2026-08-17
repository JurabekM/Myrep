package com.agrovision.mobile.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val AgroGreen = Color(0xFF2E7D32)
val AgroGreenLight = Color(0xFF66BB6A)
val AgroAccent = Color(0xFFF9A825)
val AgroError = Color(0xFFC62828)
val AgroInfo = Color(0xFF0288D1)

val ChartPalette = listOf(
    Color(0xFF2E7D32), Color(0xFF66BB6A), Color(0xFFF9A825), Color(0xFFEF6C00),
    Color(0xFF0288D1), Color(0xFF7B1FA2), Color(0xFFC62828), Color(0xFF00897B),
)

private val LightColors = lightColorScheme(
    primary = AgroGreen,
    secondary = AgroGreenLight,
    tertiary = AgroAccent,
    error = AgroError,
    background = Color(0xFFF7FAF3),
    surface = Color.White,
)

private val DarkColors = darkColorScheme(
    primary = AgroGreenLight,
    secondary = AgroGreen,
    tertiary = AgroAccent,
    error = Color(0xFFEF9A9A),
    background = Color(0xFF10140F),
    surface = Color(0xFF1B2118),
)

@Composable
fun AgroVisionTheme(darkTheme: Boolean = isSystemInDarkTheme(), content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = if (darkTheme) DarkColors else LightColors,
        typography = MaterialTheme.typography,
        content = content,
    )
}
