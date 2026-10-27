package uz.sectorverify.ui.theme

import androidx.compose.runtime.Immutable
import androidx.compose.ui.graphics.Color

/**
 * Myrep dizayn tokenlari (Claude Code dark theme uslubi; standart — dark).
 * Manba: baraka_oilasi/shared/design-tokens/tokens.json.
 */
@Immutable
data class SvPalette(
    val paper: Color,
    val sidebar: Color,
    val surface: Color,
    val line: Color,
    val fieldLine: Color,
    val ink: Color,
    val inkMuted: Color,
    val accent: Color,
    val accentInk: Color,
    val accentText: Color,
    val warn: Color,
    val danger: Color,
    val ok: Color,
    val chart1: Color,
    val chart2: Color,
)

val DarkPalette = SvPalette(
    paper = Color(0xFF262624),
    sidebar = Color(0xFF1F1E1D),
    surface = Color(0xFF30302E),
    line = Color(0xFF4A4945),
    fieldLine = Color(0xFF7D7B74),
    ink = Color(0xFFFAF9F5),
    inkMuted = Color(0xFFA6A39A),
    accent = Color(0xFFD97757),
    accentInk = Color(0xFF1F1E1D),
    accentText = Color(0xFFE8957A),
    warn = Color(0xFFE0A458),
    danger = Color(0xFFE5786D),
    ok = Color(0xFF7FB77E),
    chart1 = Color(0xFF3987E5),
    chart2 = Color(0xFFD95926),
)

val LightPalette = SvPalette(
    paper = Color(0xFFFAF9F5),
    sidebar = Color(0xFFF0EEE6),
    surface = Color(0xFFFFFFFF),
    line = Color(0xFFDAD8CE),
    fieldLine = Color(0xFF86847C),
    ink = Color(0xFF141413),
    inkMuted = Color(0xFF5E5D59),
    accent = Color(0xFFA9502F),
    accentInk = Color(0xFFFFFFFF),
    accentText = Color(0xFF953F21),
    warn = Color(0xFF9A5B13),
    danger = Color(0xFFA23B3B),
    ok = Color(0xFF2F6B2E),
    chart1 = Color(0xFF2A78D6),
    chart2 = Color(0xFFEB6834),
)

/** "Quyosh" rejimi: to'g'ri quyosh nuri ostida maksimal kontrast (qora fon, sof oq matn). */
val SunPalette = SvPalette(
    paper = Color(0xFF000000),
    sidebar = Color(0xFF000000),
    surface = Color(0xFF141414),
    line = Color(0xFFFFFFFF),
    fieldLine = Color(0xFFFFFFFF),
    ink = Color(0xFFFFFFFF),
    inkMuted = Color(0xFFE6E6E6),
    accent = Color(0xFFFFB38A),
    accentInk = Color(0xFF000000),
    accentText = Color(0xFFFFC2A3),
    warn = Color(0xFFFFD27F),
    danger = Color(0xFFFF9C94),
    ok = Color(0xFF9DE09B),
    chart1 = Color(0xFF7FB8FF),
    chart2 = Color(0xFFFF9466),
)
