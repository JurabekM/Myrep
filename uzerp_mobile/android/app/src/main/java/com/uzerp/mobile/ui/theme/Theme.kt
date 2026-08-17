package com.uzerp.mobile.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val UzDarkColors = darkColorScheme(
    primary = UzAccent,
    onPrimary = Color.White,
    secondary = UzViolet,
    background = UzBg,
    onBackground = UzText,
    surface = UzPanel,
    onSurface = UzText,
    surfaceVariant = UzPanel2,
    onSurfaceVariant = UzMuted,
    outline = UzBorder,
    error = UzRed,
)

/**
 * UzERP dark theme — hozircha faqat qorong'i mavzu qo'llab-quvvatlanadi
 * (web va desktop versiyalar bilan vizual muvofiqlik uchun).
 */
@Composable
fun UzErpTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = UzDarkColors,
        typography = UzTypography,
        content = content,
    )
}
