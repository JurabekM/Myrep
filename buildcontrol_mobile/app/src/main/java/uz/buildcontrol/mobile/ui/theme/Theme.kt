package uz.buildcontrol.mobile.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp

/** Palette shared with the desktop application. */
object BcColors {
    val Background = Color(0xFF111827)
    val BackgroundAlt = Color(0xFF151B26)
    val Sidebar = Color(0xFF0D131F)
    val Surface = Color(0xFF1E293B)
    val SurfaceAlt = Color(0xFF243044)
    val SurfaceHover = Color(0xFF2B384E)
    val Border = Color(0xFF2C3A50)
    val BorderStrong = Color(0xFF3A4A63)

    val Text = Color(0xFFE6EDF6)
    val TextMuted = Color(0xFF93A2B7)
    val TextFaint = Color(0xFF64748B)

    val Accent = Color(0xFF3B82F6)
    val AccentSoft = Color(0xFF1D3557)
    val Success = Color(0xFF22C55E)
    val SuccessSoft = Color(0xFF14311F)
    val Warning = Color(0xFFF5B342)
    val WarningSoft = Color(0xFF3A2E12)
    val Danger = Color(0xFFEF4444)
    val DangerSoft = Color(0xFF3A1A1C)
    val Info = Color(0xFF38BDF8)
    val InfoSoft = Color(0xFF12303D)
    val NeutralSoft = Color(0xFF25324A)
}

/** Semantic badge colouring, mirroring the desktop `status_colors` helper. */
fun badgeColors(kind: String): Pair<Color, Color> = when (kind) {
    "success" -> BcColors.Success to BcColors.SuccessSoft
    "warning" -> BcColors.Warning to BcColors.WarningSoft
    "danger" -> BcColors.Danger to BcColors.DangerSoft
    "info" -> BcColors.Info to BcColors.InfoSoft
    "accent" -> BcColors.Accent to BcColors.AccentSoft
    else -> BcColors.TextMuted to BcColors.NeutralSoft
}

private val DarkScheme = darkColorScheme(
    primary = BcColors.Accent,
    onPrimary = Color.White,
    primaryContainer = BcColors.AccentSoft,
    onPrimaryContainer = BcColors.Text,
    secondary = BcColors.Info,
    onSecondary = Color.White,
    background = BcColors.Background,
    onBackground = BcColors.Text,
    surface = BcColors.Surface,
    onSurface = BcColors.Text,
    surfaceVariant = BcColors.SurfaceAlt,
    onSurfaceVariant = BcColors.TextMuted,
    surfaceContainer = BcColors.Surface,
    surfaceContainerHigh = BcColors.SurfaceAlt,
    surfaceContainerHighest = BcColors.SurfaceHover,
    error = BcColors.Danger,
    onError = Color.White,
    errorContainer = BcColors.DangerSoft,
    onErrorContainer = BcColors.Danger,
    outline = BcColors.BorderStrong,
    outlineVariant = BcColors.Border,
    scrim = Color(0xCC000000),
)

private val BcTypography = Typography(
    headlineMedium = TextStyle(fontSize = 24.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.sp),
    headlineSmall = TextStyle(fontSize = 20.sp, fontWeight = FontWeight.Bold),
    titleLarge = TextStyle(fontSize = 18.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
    titleSmall = TextStyle(fontSize = 13.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 15.sp),
    bodyMedium = TextStyle(fontSize = 14.sp),
    bodySmall = TextStyle(fontSize = 12.sp),
    labelLarge = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Medium),
    labelSmall = TextStyle(fontSize = 11.sp, fontWeight = FontWeight.Medium),
)

/** Corner radii used across the app (8–12 dp, as on the desktop). */
object BcRadius {
    val sm = 8.dp
    val md = 10.dp
    val lg = 12.dp
}

@Composable
fun BuildControlTheme(content: @Composable () -> Unit) {
    @Suppress("UNUSED_EXPRESSION")
    isSystemInDarkTheme() // the app is dark-only by design
    MaterialTheme(colorScheme = DarkScheme, typography = BcTypography, content = content)
}
