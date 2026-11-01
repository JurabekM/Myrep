package uz.qarzsiz.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Typography
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.sp
import uz.qarzsiz.app.R

/** Myrep dizayn qoidasi: Claude Code dark theme uslubi (baraka_oilasi/shared/design-tokens/tokens.json). */
object Tok {
    val paper = Color(0xFF262624)
    val sidebar = Color(0xFF1F1E1D)
    val surface = Color(0xFF30302E)
    val line = Color(0xFF4A4945)
    val fieldLine = Color(0xFF7D7B74)
    val ink = Color(0xFFFAF9F5)
    val inkMuted = Color(0xFFA6A39A)
    val accent = Color(0xFFD97757)
    val accentInk = Color(0xFF1F1E1D)
    val accentText = Color(0xFFE8957A)
    val warn = Color(0xFFE0A458)
    val danger = Color(0xFFE5786D)
    /** B toifa (foizsiz) — tokens.json `zarur` rangi (paper ustida ≥ 4.5:1). */
    val calm = Color(0xFF7FA9D6)
}

val NotoSans = FontFamily(
    Font(R.font.noto_sans_regular, FontWeight.Normal),
    Font(R.font.noto_sans_bold, FontWeight.Bold),
)

private val scheme = darkColorScheme(
    primary = Tok.accent,
    onPrimary = Tok.accentInk,
    secondary = Tok.calm,
    onSecondary = Tok.accentInk,
    background = Tok.paper,
    onBackground = Tok.ink,
    surface = Tok.paper,
    onSurface = Tok.ink,
    surfaceVariant = Tok.surface,
    onSurfaceVariant = Tok.inkMuted,
    surfaceContainer = Tok.sidebar,
    surfaceContainerHigh = Tok.surface,
    surfaceContainerHighest = Tok.surface,
    surfaceContainerLow = Tok.sidebar,
    outline = Tok.fieldLine,
    outlineVariant = Tok.line,
    error = Tok.danger,
    onError = Tok.accentInk,
)

private fun style(size: Int, weight: FontWeight = FontWeight.Normal, line: Int = (size * 1.4).toInt()) =
    TextStyle(fontFamily = NotoSans, fontWeight = weight, fontSize = size.sp, lineHeight = line.sp)

private val typography = Typography(
    displaySmall = style(32, FontWeight.Bold),
    headlineMedium = style(26, FontWeight.Bold),
    headlineSmall = style(22, FontWeight.Bold),
    titleLarge = style(20, FontWeight.Bold),
    titleMedium = style(17, FontWeight.Bold),
    titleSmall = style(15, FontWeight.Bold),
    bodyLarge = style(16),
    bodyMedium = style(15),
    bodySmall = style(13),
    labelLarge = style(15, FontWeight.Bold),
    labelMedium = style(13, FontWeight.Bold),
    labelSmall = style(12),
)

@Composable
fun QarzsizTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = scheme, typography = typography, content = content)
}
