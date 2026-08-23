package uz.distribos.app.ui

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp

/**
 * Zamonaviy dark tema — desktop palitrasi bilan bir xil.
 *
 * Agent kun bo'yi quyoshda telefonga qaraydi, shuning uchun yorug'lik
 * rejimi ham to'liq qo'llab-quvvatlanadi. Lekin **default dark**:
 * ombor va savdo nuqtalarida ekran ko'proq xira joyda ishlatiladi.
 */

private val Accent = Color(0xFF4F7CFF)
private val AccentLight = Color(0xFF6B91FF)

private val DarkColors = darkColorScheme(
    primary = AccentLight,
    onPrimary = Color(0xFF0F1219),
    primaryContainer = Color(0xFF1E2A4A),
    onPrimaryContainer = AccentLight,
    secondary = Color(0xFF98A2B8),
    onSecondary = Color(0xFF0F1219),
    // `secondaryContainer` navigatsiya indikatori uchun ishlatiladi —
    // uni bermasak Material'ning standart SIYOHRANG i chiqadi va ilova
    // "shablon"dek ko'rinadi.
    secondaryContainer = Color(0xFF1E2A4A),
    onSecondaryContainer = AccentLight,
    tertiary = Color(0xFF3ECF8E),
    onTertiary = Color(0xFF0F1219),
    background = Color(0xFF0F1219),
    onBackground = Color(0xFFE6E9F0),
    surface = Color(0xFF161A23),
    onSurface = Color(0xFFE6E9F0),
    surfaceVariant = Color(0xFF1D2230),
    onSurfaceVariant = Color(0xFF98A2B8),
    outline = Color(0xFF3A4257),
    error = Color(0xFFFF5F56),
    onError = Color(0xFF0F1219),
    errorContainer = Color(0xFF3A1614),
    onErrorContainer = Color(0xFFFF5F56),
)

private val LightColors = lightColorScheme(
    primary = Accent,
    onPrimary = Color.White,
    primaryContainer = Color(0xFFDDE6FF),
    onPrimaryContainer = Color(0xFF16265C),
    secondary = Color(0xFF5A6478),
    onSecondary = Color.White,
    secondaryContainer = Color(0xFFDDE6FF),
    onSecondaryContainer = Color(0xFF16265C),
    tertiary = Color(0xFF1F9D63),
    onTertiary = Color.White,
    background = Color(0xFFF7F8FB),
    onBackground = Color(0xFF141821),
    surface = Color.White,
    onSurface = Color(0xFF141821),
    surfaceVariant = Color(0xFFEEF1F6),
    onSurfaceVariant = Color(0xFF5A6478),
    outline = Color(0xFFC7CDDA),
    error = Color(0xFFCC2F27),
)

/** Holat ranglari — `StatusTone` bilan mos (desktop bilan bir xil ma'no). */
object StatusColors {
    val ok = Color(0xFF3ECF8E)
    val progress = Color(0xFF4F9CFF)
    val warning = Color(0xFFF0B04A)
    val error = Color(0xFFFF5F56)

    fun of(tone: StatusTone): Color = when (tone) {
        StatusTone.OK -> ok
        StatusTone.PROGRESS -> progress
        StatusTone.WARNING -> warning
        StatusTone.ERROR -> error
    }
}

enum class StatusTone { OK, PROGRESS, WARNING, ERROR }

private val AppTypography = Typography(
    headlineMedium = TextStyle(fontSize = 24.sp, fontWeight = FontWeight.SemiBold),
    titleLarge = TextStyle(fontSize = 20.sp, fontWeight = FontWeight.SemiBold),
    titleMedium = TextStyle(fontSize = 16.sp, fontWeight = FontWeight.Medium),
    bodyLarge = TextStyle(fontSize = 16.sp),
    bodyMedium = TextStyle(fontSize = 14.sp),
    labelLarge = TextStyle(fontSize = 14.sp, fontWeight = FontWeight.Medium),
    labelMedium = TextStyle(fontSize = 12.sp),
)

/**
 * @param darkTheme `null` — tizim sozlamasiga ergashadi.
 *
 * Sukut bo'yicha DARK: ombor va savdo nuqtalarida ekran ko'pincha xira
 * joyda ishlatiladi, va desktop tomoni ham dark. Foydalanuvchi tizim
 * temasiga o'tkazishi mumkin.
 */
@Composable
fun DistribosTheme(
    darkTheme: Boolean? = true,
    content: @Composable () -> Unit,
) {
    val useDark = darkTheme ?: isSystemInDarkTheme()
    MaterialTheme(
        colorScheme = if (useDark) DarkColors else LightColors,
        typography = AppTypography,
        content = content,
    )
}
