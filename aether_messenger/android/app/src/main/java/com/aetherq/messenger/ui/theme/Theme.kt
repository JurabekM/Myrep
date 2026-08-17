package com.aetherq.messenger.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

// AETHER-Q brend palitrasi — desktop (WPF) versiyasi bilan bir xil (DarkTheme.xaml).
val AetherBackground = Color(0xFF0B1220)
val AetherSurface = Color(0xFF131C2E)
val AetherSurfaceRaised = Color(0xFF1B2740)
val AetherBorder = Color(0xFF28324A)
val AetherAccent = Color(0xFF4FD1C5)
val AetherAccentPressed = Color(0xFF38A99E)
val AetherTextPrimary = Color(0xFFE8EDF5)
val AetherTextSecondary = Color(0xFF8B97AC)
val AetherBubbleOutgoing = Color(0xFF1F6F66)
val AetherBubbleIncoming = AetherSurfaceRaised
val AetherDanger = Color(0xFFF87171)

private val AetherDarkColors = darkColorScheme(
    primary = AetherAccent,
    onPrimary = Color(0xFF06110F),
    primaryContainer = AetherAccentPressed,
    onPrimaryContainer = AetherTextPrimary,
    secondary = AetherAccent,
    background = AetherBackground,
    onBackground = AetherTextPrimary,
    surface = AetherSurface,
    onSurface = AetherTextPrimary,
    surfaceVariant = AetherSurfaceRaised,
    onSurfaceVariant = AetherTextPrimary,
    outline = AetherBorder,
    error = AetherDanger,
)

/**
 * Ilova har doim zamonaviy dark-tema bilan ochiladi — tizim yorug'/qorong'i sozlamasidan
 * qat'iy nazar (desktop versiyasi bilan bir xil ko'rinish siyosati).
 */
@Composable
fun AetherMessengerTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = AetherDarkColors,
        content = content,
    )
}
