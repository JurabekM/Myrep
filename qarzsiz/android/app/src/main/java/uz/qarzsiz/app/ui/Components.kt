package uz.qarzsiz.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.Text as M3Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import android.content.Context
import android.widget.Toast
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.Script
import uz.qarzsiz.core.Translit

/** Tanlangan interfeys yozuvi. Hamma matn shu yerdan o'tadi: [Text] va [t]. */
val LocalScript = staticCompositionLocalOf { Script.LATIN }

/** Ilova matni tanlangan yozuvda (lotin → kirill). */
@Composable
@ReadOnlyComposable
fun t(text: String): String = Translit.apply(text, LocalScript.current)

/**
 * Ilovadagi yagona `Text`: matnni tanlangan yozuvga o'giradi. `raw = true` — foydalanuvchining
 * erkin matni (izoh, o'z odati) o'zgarishsiz chiqadi.
 */
@Composable
fun Text(
    text: String,
    modifier: Modifier = Modifier,
    color: Color = Color.Unspecified,
    style: TextStyle = LocalTextStyle.current,
    fontWeight: FontWeight? = null,
    raw: Boolean = false,
) {
    M3Text(if (raw) text else t(text), modifier = modifier, color = color, style = style, fontWeight = fontWeight)
}

/** Qisqa xabar tanlangan yozuvda. */
fun Context.toast(message: String, script: Script) =
    Toast.makeText(this, Translit.apply(message, script), Toast.LENGTH_SHORT).show()

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScreenScaffold(
    title: String,
    onBack: (() -> Unit)? = null,
    actions: @Composable RowScope.() -> Unit = {},
    content: @Composable ColumnScope.() -> Unit,
) {
    Column(Modifier.fillMaxWidth().fillMaxHeight().background(Tok.paper)) {
        TopAppBar(
            title = { Text(title, style = MaterialTheme.typography.titleLarge) },
            navigationIcon = {
                if (onBack != null) {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = t("Orqaga"))
                    }
                }
            },
            actions = actions,
            colors = TopAppBarDefaults.topAppBarColors(
                containerColor = Tok.paper,
                titleContentColor = Tok.ink,
                navigationIconContentColor = Tok.ink,
                actionIconContentColor = Tok.ink,
            ),
        )
        Column(
            Modifier.fillMaxWidth().weight(1f).verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp).padding(bottom = 24.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
            content = content,
        )
    }
}

@Composable
fun Panel(
    modifier: Modifier = Modifier,
    border: Color = Tok.line,
    onClick: (() -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(14.dp)
    Column(
        modifier.fillMaxWidth().clip(shape).background(Tok.surface).border(1.dp, border, shape)
            .let { if (onClick != null) it.clickable(onClick = onClick) else it }
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
        content = content,
    )
}

@Composable
fun Muted(text: String, modifier: Modifier = Modifier) =
    Text(text, modifier = modifier, style = MaterialTheme.typography.bodySmall, color = Tok.inkMuted)

@Composable
fun SectionTitle(text: String) =
    Text(text, style = MaterialTheme.typography.titleMedium, color = Tok.ink, modifier = Modifier.padding(top = 8.dp))

@Composable
fun BigNumber(text: String, color: Color = Tok.accent) =
    Text(text, style = MaterialTheme.typography.headlineMedium, color = color, fontWeight = FontWeight.Bold)

@Composable
fun KeyValue(key: String, value: String, valueColor: Color = Tok.ink) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.Top) {
        Text(key, style = MaterialTheme.typography.bodyMedium, color = Tok.inkMuted, modifier = Modifier.weight(1f))
        Spacer(Modifier.width(12.dp))
        Text(value, style = MaterialTheme.typography.bodyMedium, color = valueColor, fontWeight = FontWeight.Bold)
    }
}

/** Progress chizig'i, `bp` — 0..10000. */
@Composable
fun ProgressLine(bp: Int, color: Color = Tok.accent, label: String = "Yopilgan qismi") {
    val fraction = (bp.coerceIn(0, 10_000)) / 10_000f
    val description = t("$label: ${MoneyFormat.percent(bp)}")
    Box(
        Modifier.fillMaxWidth().height(8.dp).clip(RoundedCornerShape(4.dp)).background(Tok.line)
            .semantics { contentDescription = description },
    ) {
        Box(Modifier.fillMaxWidth(fraction).fillMaxHeight().background(color))
    }
}

@Composable
fun PrimaryButton(text: String, modifier: Modifier = Modifier, enabled: Boolean = true, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        enabled = enabled,
        modifier = modifier.fillMaxWidth().heightIn(min = 48.dp),
        shape = RoundedCornerShape(12.dp),
        colors = ButtonDefaults.buttonColors(
            containerColor = Tok.accent,
            contentColor = Tok.accentInk,
            disabledContainerColor = Tok.line,
            disabledContentColor = Tok.inkMuted,
        ),
        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
    ) { Text(text, style = MaterialTheme.typography.labelLarge) }
}

@Composable
fun SecondaryButton(text: String, modifier: Modifier = Modifier, color: Color = Tok.ink, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier.fillMaxWidth().heightIn(min = 48.dp),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, Tok.fieldLine),
        colors = ButtonDefaults.outlinedButtonColors(contentColor = color),
    ) { Text(text, style = MaterialTheme.typography.labelLarge) }
}

@Composable
private fun fieldColors() = OutlinedTextFieldDefaults.colors(
    focusedBorderColor = Tok.accent,
    unfocusedBorderColor = Tok.fieldLine,
    focusedLabelColor = Tok.accentText,
    unfocusedLabelColor = Tok.inkMuted,
    cursorColor = Tok.accent,
    focusedTextColor = Tok.ink,
    unfocusedTextColor = Tok.ink,
    errorBorderColor = Tok.danger,
    errorLabelColor = Tok.danger,
    errorSupportingTextColor = Tok.danger,
    focusedSupportingTextColor = Tok.inkMuted,
    unfocusedSupportingTextColor = Tok.inkMuted,
)

@Composable
fun TextInput(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    hint: String? = null,
    error: String? = null,
    singleLine: Boolean = true,
    minLines: Int = 1,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        modifier = modifier.fillMaxWidth(),
        singleLine = singleLine,
        minLines = minLines,
        isError = error != null,
        supportingText = (error ?: hint)?.let { { Text(it) } },
        keyboardOptions = KeyboardOptions(imeAction = if (singleLine) ImeAction.Next else ImeAction.Default),
        colors = fieldColors(),
        shape = RoundedCornerShape(12.dp),
    )
}

/** Summa maydoni: raqam klaviaturasi, kiritilganda «1 500 000» ko'rinishi pastda tasdiqlanadi. */
@Composable
fun MoneyInput(
    value: String,
    onChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    suffix: String = "so'm",
    hint: String? = null,
    required: Boolean = false,
) {
    val parsed = MoneyFormat.parse(value)
    val error = when {
        value.isBlank() && required -> "Summani kiriting"
        value.isNotBlank() && parsed == null -> "Faqat raqam: 1500000 yoki 1500000,50"
        else -> null
    }
    val echo = if (parsed != null) "= ${MoneyFormat.amount(parsed)} $suffix" else hint
    OutlinedTextField(
        value = value,
        onValueChange = { onChange(it.filter { ch -> ch.isDigit() || ch == ',' || ch == '.' || ch == ' ' }) },
        label = { Text(label) },
        modifier = modifier.fillMaxWidth(),
        singleLine = true,
        isError = error != null,
        supportingText = (error ?: echo)?.let { { Text(it) } },
        suffix = { Text(suffix, color = Tok.inkMuted) },
        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal, imeAction = ImeAction.Next),
        colors = fieldColors(),
        shape = RoundedCornerShape(12.dp),
    )
}

@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun <T> ChoiceRow(options: List<T>, selected: T, label: (T) -> String, onSelect: (T) -> Unit) {
    androidx.compose.foundation.layout.FlowRow(
        horizontalArrangement = Arrangement.spacedBy(8.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        options.forEach { o ->
            FilterChip(
                selected = o == selected,
                onClick = { onSelect(o) },
                label = { Text(label(o)) },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = Tok.surface,
                    labelColor = Tok.ink,
                    selectedContainerColor = Tok.accent,
                    selectedLabelColor = Tok.accentInk,
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = o == selected,
                    borderColor = Tok.fieldLine,
                    selectedBorderColor = Tok.accent,
                ),
            )
        }
    }
}

/** Yozuv tanlovi: har variant o'z yozuvida ko'rsatiladi («Lotin», «Кирилл»). */
@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun ScriptChoice(selected: Script, onSelect: (Script) -> Unit) {
    androidx.compose.foundation.layout.FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
        Script.entries.forEach { s ->
            FilterChip(
                selected = s == selected,
                onClick = { onSelect(s) },
                label = { Text(s.label, raw = true) },
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = Tok.surface,
                    labelColor = Tok.ink,
                    selectedContainerColor = Tok.accent,
                    selectedLabelColor = Tok.accentInk,
                ),
                border = FilterChipDefaults.filterChipBorder(
                    enabled = true,
                    selected = s == selected,
                    borderColor = Tok.fieldLine,
                    selectedBorderColor = Tok.accent,
                ),
            )
        }
    }
}

/** Ogohlantirish yoki eslatma bloki. */
@Composable
fun Notice(text: String, color: Color = Tok.warn, title: String? = null) {
    val shape = RoundedCornerShape(12.dp)
    Column(
        Modifier.fillMaxWidth().clip(shape).background(Tok.sidebar).border(1.dp, color, shape).padding(12.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        if (title != null) Text(title, style = MaterialTheme.typography.titleSmall, color = color)
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
    }
}

@Composable
fun Disclaimer() = Muted("Ta'limiy vosita. Moliyaviy yoki yuridik maslahat emas. Hisoblar taxminiy — bank hisobi farq qilishi mumkin.")

@Composable
fun Tag(text: String, color: Color) {
    Text(
        text,
        style = MaterialTheme.typography.labelMedium,
        color = color,
        modifier = Modifier.clip(RoundedCornerShape(6.dp)).border(1.dp, color, RoundedCornerShape(6.dp))
            .padding(horizontal = 8.dp, vertical = 2.dp),
    )
}

@Composable
fun Bullets(items: List<String>) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        items.forEach { t ->
            Row {
                Text("•", color = Tok.accentText, modifier = Modifier.width(16.dp))
                Text(t, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
            }
        }
    }
}
