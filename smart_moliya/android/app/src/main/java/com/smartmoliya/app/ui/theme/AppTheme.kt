package com.smartmoliya.app.ui.theme

import android.content.Context
import android.os.Build
import androidx.compose.material3.ColorScheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.dynamicDarkColorScheme
import androidx.compose.material3.dynamicLightColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

/**
 * Ilova temalari. Foydalanuvchi Profil sahifasida tanlaydi, tanlov saqlanadi
 * (ThemeManager) va butun ilova darhol qayta bo'yaladi.
 */
enum class AppThemeId(val title: String) {
    DARK_MODERN("Dark Modern"),
    AMOLED("AMOLED qora"),
    OCEAN("Okean"),
    SUNSET("Shafaq"),
    LIGHT("Yorug'"),
    DYNAMIC("Tizim rangi")
}

data class AppThemeSpec(
    val colorScheme: ColorScheme,
    /** Bosh sahifadagi balans kartasi kabi "hero" elementlar gradienti. */
    val gradient: List<Color>,
    val isDark: Boolean
)

/** Kompozitsiya bo'ylab joriy tema gradientini uzatish uchun. */
val LocalAppGradient = staticCompositionLocalOf { listOf(Color(0xFF059669), Color(0xFF34D399)) }

private val DarkModernScheme = darkColorScheme(
    primary = Color(0xFF4ADE80),
    onPrimary = Color(0xFF052E16),
    primaryContainer = Color(0xFF14532D),
    onPrimaryContainer = Color(0xFFBBF7D0),
    secondary = Color(0xFF60A5FA),
    onSecondary = Color(0xFF0C2547),
    secondaryContainer = Color(0xFF1E3A5F),
    onSecondaryContainer = Color(0xFFBFDBFE),
    tertiary = Color(0xFFFBBF24),
    background = Color(0xFF0D1117),
    onBackground = Color(0xFFE6EDF3),
    surface = Color(0xFF161B22),
    onSurface = Color(0xFFE6EDF3),
    surfaceVariant = Color(0xFF21262E),
    onSurfaceVariant = Color(0xFF9BA3AF),
    outline = Color(0xFF3B4351),
    error = Color(0xFFF87171)
)

private val AmoledScheme = DarkModernScheme.copy(
    background = Color(0xFF000000),
    surface = Color(0xFF0A0A0A),
    surfaceVariant = Color(0xFF141414),
    outline = Color(0xFF2A2A2A)
)

private val OceanScheme = darkColorScheme(
    primary = Color(0xFF38BDF8),
    onPrimary = Color(0xFF06283D),
    primaryContainer = Color(0xFF0C4A6E),
    onPrimaryContainer = Color(0xFFBAE6FD),
    secondary = Color(0xFF818CF8),
    tertiary = Color(0xFF34D399),
    background = Color(0xFF0B1220),
    onBackground = Color(0xFFE2E8F0),
    surface = Color(0xFF111A2C),
    onSurface = Color(0xFFE2E8F0),
    surfaceVariant = Color(0xFF1A2540),
    onSurfaceVariant = Color(0xFF94A3B8),
    outline = Color(0xFF334366),
    error = Color(0xFFFB7185)
)

private val SunsetScheme = darkColorScheme(
    primary = Color(0xFFC084FC),
    onPrimary = Color(0xFF2E1065),
    primaryContainer = Color(0xFF4C1D95),
    onPrimaryContainer = Color(0xFFE9D5FF),
    secondary = Color(0xFFF472B6),
    tertiary = Color(0xFFFBBF24),
    background = Color(0xFF14101F),
    onBackground = Color(0xFFEDE9F6),
    surface = Color(0xFF1E1730),
    onSurface = Color(0xFFEDE9F6),
    surfaceVariant = Color(0xFF2A2040),
    onSurfaceVariant = Color(0xFFA79EC0),
    outline = Color(0xFF453861),
    error = Color(0xFFFB7185)
)

private val LightScheme = lightColorScheme(
    primary = Color(0xFF059669),
    onPrimary = Color(0xFFFFFFFF),
    primaryContainer = Color(0xFFD1FAE5),
    onPrimaryContainer = Color(0xFF064E3B),
    secondary = Color(0xFF2563EB),
    secondaryContainer = Color(0xFFDBEAFE),
    tertiary = Color(0xFFD97706),
    background = Color(0xFFF6F8F7),
    onBackground = Color(0xFF111827),
    surface = Color(0xFFFFFFFF),
    onSurface = Color(0xFF111827),
    surfaceVariant = Color(0xFFEDF1EF),
    onSurfaceVariant = Color(0xFF5B6472),
    outline = Color(0xFFD3DAD6),
    error = Color(0xFFDC2626)
)

fun resolveThemeSpec(id: AppThemeId, context: Context, systemDark: Boolean): AppThemeSpec = when (id) {
    AppThemeId.DARK_MODERN -> AppThemeSpec(
        DarkModernScheme, listOf(Color(0xFF059669), Color(0xFF10B981), Color(0xFF34D399)), isDark = true
    )
    AppThemeId.AMOLED -> AppThemeSpec(
        AmoledScheme, listOf(Color(0xFF047857), Color(0xFF10B981)), isDark = true
    )
    AppThemeId.OCEAN -> AppThemeSpec(
        OceanScheme, listOf(Color(0xFF0284C7), Color(0xFF0EA5E9), Color(0xFF38BDF8)), isDark = true
    )
    AppThemeId.SUNSET -> AppThemeSpec(
        SunsetScheme, listOf(Color(0xFF7C3AED), Color(0xFFA855F7), Color(0xFFEC4899)), isDark = true
    )
    AppThemeId.LIGHT -> AppThemeSpec(
        LightScheme, listOf(Color(0xFF059669), Color(0xFF34D399)), isDark = false
    )
    AppThemeId.DYNAMIC -> {
        val scheme = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (systemDark) dynamicDarkColorScheme(context) else dynamicLightColorScheme(context)
        } else {
            if (systemDark) DarkModernScheme else LightScheme
        }
        AppThemeSpec(scheme, listOf(scheme.primary, scheme.tertiary), isDark = systemDark)
    }
}

/** Tema tanlash sahifasidagi ko'rgazma ranglari. */
fun themePreviewColors(id: AppThemeId): List<Color> = when (id) {
    AppThemeId.DARK_MODERN -> listOf(Color(0xFF0D1117), Color(0xFF4ADE80), Color(0xFF60A5FA))
    AppThemeId.AMOLED -> listOf(Color(0xFF000000), Color(0xFF4ADE80), Color(0xFF21262E))
    AppThemeId.OCEAN -> listOf(Color(0xFF0B1220), Color(0xFF38BDF8), Color(0xFF818CF8))
    AppThemeId.SUNSET -> listOf(Color(0xFF14101F), Color(0xFFC084FC), Color(0xFFF472B6))
    AppThemeId.LIGHT -> listOf(Color(0xFFF6F8F7), Color(0xFF059669), Color(0xFF2563EB))
    AppThemeId.DYNAMIC -> listOf(Color(0xFF888888), Color(0xFFBBBBBB), Color(0xFF555555))
}
