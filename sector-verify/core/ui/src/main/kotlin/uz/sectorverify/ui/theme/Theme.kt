package uz.sectorverify.ui.theme

import androidx.compose.material3.ColorScheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import uz.sectorverify.ui.R

enum class ThemeMode { DARK, LIGHT, SUN }

val LocalSvPalette = staticCompositionLocalOf { DarkPalette }

val NotoSans = FontFamily(
    Font(R.font.noto_sans_regular, FontWeight.Normal),
    Font(R.font.noto_sans_bold, FontWeight.Bold),
)

private fun SvPalette.toScheme(dark: Boolean): ColorScheme {
    val base = if (dark) darkColorScheme() else lightColorScheme()
    return base.copy(
        primary = accent,
        onPrimary = accentInk,
        secondary = accentText,
        onSecondary = accentInk,
        background = paper,
        onBackground = ink,
        surface = paper,
        onSurface = ink,
        surfaceVariant = surface,
        onSurfaceVariant = inkMuted,
        surfaceContainer = surface,
        surfaceContainerLow = sidebar,
        surfaceContainerHigh = surface,
        surfaceContainerHighest = surface,
        outline = fieldLine,
        outlineVariant = line,
        error = danger,
        onError = accentInk,
    )
}

private fun TextStyle.noto() = copy(fontFamily = NotoSans)

private val SvTypography = Typography().let { t ->
    Typography(
        displayLarge = t.displayLarge.noto(),
        displayMedium = t.displayMedium.noto(),
        displaySmall = t.displaySmall.noto(),
        headlineLarge = t.headlineLarge.noto(),
        headlineMedium = t.headlineMedium.noto(),
        headlineSmall = t.headlineSmall.noto(),
        titleLarge = t.titleLarge.noto(),
        titleMedium = t.titleMedium.noto(),
        titleSmall = t.titleSmall.noto(),
        bodyLarge = t.bodyLarge.noto(),
        bodyMedium = t.bodyMedium.noto(),
        bodySmall = t.bodySmall.noto(),
        labelLarge = t.labelLarge.noto(),
        labelMedium = t.labelMedium.noto(),
        labelSmall = t.labelSmall.noto(),
    )
}

/** Standart mavzu — dark (Myrep UI qoidasi). */
@Composable
fun SectorVerifyTheme(mode: ThemeMode = ThemeMode.DARK, content: @Composable () -> Unit) {
    val palette = when (mode) {
        ThemeMode.DARK -> DarkPalette
        ThemeMode.LIGHT -> LightPalette
        ThemeMode.SUN -> SunPalette
    }
    CompositionLocalProvider(LocalSvPalette provides palette) {
        MaterialTheme(
            colorScheme = palette.toScheme(dark = mode != ThemeMode.LIGHT),
            typography = SvTypography,
            content = content,
        )
    }
}
