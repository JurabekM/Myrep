package uz.mpay.wallet.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/** M-Pay ranglari (qorong'i mavzu; launcher ikonkasi va demo bilan bir oila). */
object MpayColors {
    val Mint = Color(0xFF7CE0B5)
    val MintDim = Color(0xFF4FB38A)
    val Background = Color(0xFF0B1410)
    val Surface = Color(0xFF14201B)
    val SurfaceHigh = Color(0xFF1C2B25)
    val Outline = Color(0xFF2E4038)
    val TextPrimary = Color(0xFFE8F5EE)
    val TextSecondary = Color(0xFF9DB5AA)
    val Warning = Color(0xFFFFB74D)
    val Danger = Color(0xFFFF6E6E)
    val Success = Color(0xFF7CE0B5)
    val CardTop = Color(0xFF138A64)
    val CardBottom = Color(0xFF0B3D2E)
    val CardSuspended = Color(0xFF3A4540)

    fun cardBrush(active: Boolean): Brush =
        if (active) Brush.linearGradient(listOf(CardTop, CardBottom)) else Brush.linearGradient(listOf(CardSuspended, Color(0xFF202826)))
}

private val scheme = darkColorScheme(
    primary = MpayColors.Mint,
    onPrimary = Color(0xFF00382A),
    secondary = MpayColors.MintDim,
    background = MpayColors.Background,
    onBackground = MpayColors.TextPrimary,
    surface = MpayColors.Surface,
    onSurface = MpayColors.TextPrimary,
    surfaceVariant = MpayColors.SurfaceHigh,
    onSurfaceVariant = MpayColors.TextSecondary,
    surfaceContainer = MpayColors.Surface,
    surfaceContainerHigh = MpayColors.SurfaceHigh,
    surfaceContainerHighest = MpayColors.SurfaceHigh,
    outline = MpayColors.Outline,
    error = MpayColors.Danger,
)

private val typography = Typography(
    headlineMedium = TextStyle(fontSize = 26.sp, fontWeight = FontWeight.Bold, letterSpacing = 0.2.sp),
    titleLarge = TextStyle(fontSize = 20.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.SemiBold),
    bodyLarge = TextStyle(fontSize = 16.sp),
    bodyMedium = TextStyle(fontSize = 14.sp),
    labelLarge = TextStyle(fontSize = 15.sp, fontWeight = FontWeight.SemiBold),
    labelMedium = TextStyle(fontSize = 12.sp, fontWeight = FontWeight.Medium),
)

@Composable
fun MpayTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography, content = content)
}
