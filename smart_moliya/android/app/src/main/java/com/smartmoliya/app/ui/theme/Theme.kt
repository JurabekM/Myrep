package com.smartmoliya.app.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext

@Composable
fun SmartMoliyaTheme(
    appThemeId: AppThemeId = AppThemeId.DARK_MODERN,
    content: @Composable () -> Unit
) {
    val systemDark = isSystemInDarkTheme()
    val context = LocalContext.current
    val spec = remember(appThemeId, systemDark) { resolveThemeSpec(appThemeId, context, systemDark) }

    CompositionLocalProvider(LocalAppGradient provides spec.gradient) {
        MaterialTheme(
            colorScheme = spec.colorScheme,
            typography = MoliyaTypography,
            content = content
        )
    }
}
