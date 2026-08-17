package uz.buildcontrol.mobile.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.KeyboardArrowDown
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.ui.theme.BcColors
import uz.buildcontrol.mobile.ui.theme.BcRadius
import uz.buildcontrol.mobile.ui.theme.badgeColors

/** Rounded surface used for every block of content. */
@Composable
fun BcCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit,
) {
    val shape = RoundedCornerShape(BcRadius.md)
    Card(
        modifier = modifier
            .fillMaxWidth()
            .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier),
        shape = shape,
        colors = CardDefaults.cardColors(containerColor = BcColors.Surface),
        border = androidx.compose.foundation.BorderStroke(1.dp, BcColors.Border),
    ) {
        Column(Modifier.padding(14.dp), content = content)
    }
}

/** Small status pill. */
@Composable
fun Badge(text: String, kind: String = "neutral", modifier: Modifier = Modifier) {
    val (fg, bg) = badgeColors(kind)
    Box(
        modifier = modifier
            .background(bg, RoundedCornerShape(9.dp))
            .padding(horizontal = 9.dp, vertical = 3.dp)
    ) {
        Text(text, color = fg, style = MaterialTheme.typography.labelSmall, maxLines = 1)
    }
}

/** Caption + value line used across detail screens. */
@Composable
fun KeyValue(
    label: String,
    value: String,
    valueColor: androidx.compose.ui.graphics.Color = BcColors.Text,
    modifier: Modifier = Modifier,
) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 3.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = BcColors.TextMuted, style = MaterialTheme.typography.bodySmall)
        Spacer(Modifier.width(12.dp))
        Text(
            value,
            color = valueColor,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.Medium,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** KPI tile shown on the project overview. */
@Composable
fun MetricTile(
    title: String,
    value: String,
    hint: String = "",
    kind: String = "neutral",
    modifier: Modifier = Modifier,
) {
    val (fg, _) = badgeColors(kind)
    BcCard(modifier) {
        Text(title, color = BcColors.TextMuted, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(4.dp))
        Text(
            value,
            color = if (kind == "neutral") BcColors.Text else fg,
            style = MaterialTheme.typography.titleLarge,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        if (hint.isNotBlank()) {
            Spacer(Modifier.height(2.dp))
            Text(hint, color = BcColors.TextFaint, style = MaterialTheme.typography.labelSmall)
        }
    }
}

/** Budget usage bar; turns amber past 90% and red when over budget. */
@Composable
fun UsageBar(ratio: Double, modifier: Modifier = Modifier) {
    val color = when {
        ratio > 1.0 -> BcColors.Danger
        ratio >= 0.9 -> BcColors.Warning
        else -> BcColors.Success
    }
    LinearProgressIndicator(
        progress = { ratio.coerceIn(0.0, 1.0).toFloat() },
        modifier = modifier.fillMaxWidth().height(8.dp),
        color = color,
        trackColor = BcColors.BackgroundAlt,
        strokeCap = androidx.compose.ui.graphics.StrokeCap.Round,
        gapSize = 0.dp,
        drawStopIndicator = {},
    )
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier, trailing: (@Composable () -> Unit)? = null) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(text, style = MaterialTheme.typography.titleMedium, color = BcColors.Text)
        trailing?.invoke()
    }
}

@Composable
fun EmptyState(text: String = tr("no_data"), modifier: Modifier = Modifier) {
    Box(modifier.fillMaxWidth().padding(28.dp), contentAlignment = Alignment.Center) {
        Text(text, color = BcColors.TextFaint, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
fun SearchField(value: String, onChange: (String) -> Unit, modifier: Modifier = Modifier) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        modifier = modifier.fillMaxWidth(),
        singleLine = true,
        placeholder = { Text(tr("search")) },
        leadingIcon = { Icon(Icons.Default.Search, null, tint = BcColors.TextMuted) },
        shape = RoundedCornerShape(BcRadius.sm),
    )
}

/** Labelled text input used by every form sheet. */
@Composable
fun Field(
    label: String,
    value: String,
    onChange: (String) -> Unit,
    modifier: Modifier = Modifier,
    numeric: Boolean = false,
    singleLine: Boolean = true,
    required: Boolean = false,
    enabled: Boolean = true,
    isError: Boolean = false,
) {
    Column(modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(
            if (required) "$label *" else label,
            color = BcColors.TextMuted,
            style = MaterialTheme.typography.labelSmall,
        )
        Spacer(Modifier.height(3.dp))
        OutlinedTextField(
            value = value,
            onValueChange = onChange,
            modifier = Modifier.fillMaxWidth(),
            singleLine = singleLine,
            minLines = if (singleLine) 1 else 3,
            enabled = enabled,
            isError = isError,
            keyboardOptions = androidx.compose.foundation.text.KeyboardOptions(
                keyboardType = if (numeric) KeyboardType.Decimal else KeyboardType.Text
            ),
            shape = RoundedCornerShape(BcRadius.sm),
        )
    }
}

/** Dropdown bound to `[value, label]` options. */
@Composable
fun <T> Picker(
    label: String,
    options: List<Pair<T, String>>,
    selected: T?,
    onSelect: (T) -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    var expanded by remember { mutableStateOf(false) }
    val current = options.firstOrNull { it.first == selected }?.second ?: "—"
    Column(modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Text(label, color = BcColors.TextMuted, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(3.dp))
        Box {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .border(1.dp, BcColors.BorderStrong, RoundedCornerShape(BcRadius.sm))
                    .background(BcColors.BackgroundAlt, RoundedCornerShape(BcRadius.sm))
                    .clickable(enabled = enabled) { expanded = true }
                    .padding(horizontal = 14.dp, vertical = 15.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    current,
                    color = if (enabled) BcColors.Text else BcColors.TextFaint,
                    style = MaterialTheme.typography.bodyMedium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f),
                )
                Icon(Icons.Default.KeyboardArrowDown, null, tint = BcColors.TextMuted)
            }
            DropdownMenu(
                expanded = expanded,
                onDismissRequest = { expanded = false },
                modifier = Modifier.background(BcColors.SurfaceAlt),
            ) {
                Column(Modifier.heightIn().verticalScroll(rememberScrollState())) {
                    options.forEach { (value, text) ->
                        DropdownMenuItem(
                            text = { Text(text, color = BcColors.Text) },
                            onClick = {
                                onSelect(value)
                                expanded = false
                            },
                            trailingIcon = {
                                if (value == selected) {
                                    Icon(Icons.Default.Check, null, tint = BcColors.Accent)
                                }
                            },
                        )
                    }
                }
            }
        }
    }
}

private fun Modifier.heightIn(): Modifier = this.then(Modifier.height(320.dp))

@Composable
fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier.fillMaxWidth().padding(vertical = 6.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, color = BcColors.Text, style = MaterialTheme.typography.bodyMedium)
        Switch(checked = checked, onCheckedChange = onChange)
    }
}

/** Bottom sheet hosting a form; `onSave` returns false to keep it open. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FormSheet(
    title: String,
    onDismiss: () -> Unit,
    onSave: () -> Unit,
    saveLabel: String = tr("save"),
    error: String = "",
    content: @Composable androidx.compose.foundation.layout.ColumnScope.() -> Unit,
) {
    val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
    ModalBottomSheet(
        onDismissRequest = onDismiss,
        sheetState = sheetState,
        containerColor = BcColors.BackgroundAlt,
        dragHandle = null,
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 18.dp)
                .padding(top = 18.dp, bottom = 24.dp)
                .verticalScroll(rememberScrollState())
        ) {
            Text(title, style = MaterialTheme.typography.titleLarge, color = BcColors.Text)
            Spacer(Modifier.height(10.dp))
            content()
            if (error.isNotBlank()) {
                Spacer(Modifier.height(6.dp))
                Text(error, color = BcColors.Danger, style = MaterialTheme.typography.bodySmall)
            }
            Spacer(Modifier.height(14.dp))
            Row(horizontalArrangement = Arrangement.End, modifier = Modifier.fillMaxWidth()) {
                TextButton(onClick = onDismiss) { Text(tr("cancel"), color = BcColors.TextMuted) }
                Spacer(Modifier.width(8.dp))
                PrimaryButton(saveLabel, onClick = onSave)
            }
        }
    }
}

@Composable
fun PrimaryButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    androidx.compose.material3.Button(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(BcRadius.sm),
    ) { Text(text) }
}

@Composable
fun GhostButton(
    text: String,
    onClick: () -> Unit,
    modifier: Modifier = Modifier,
    enabled: Boolean = true,
) {
    androidx.compose.material3.OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        enabled = enabled,
        shape = RoundedCornerShape(BcRadius.sm),
    ) { Text(text, color = if (enabled) BcColors.Text else BcColors.TextFaint) }
}

@Composable
fun ConfirmDialog(
    title: String,
    text: String,
    onConfirm: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        containerColor = BcColors.SurfaceAlt,
        title = { Text(title, color = BcColors.Text) },
        text = { Text(text, color = BcColors.TextMuted) },
        confirmButton = { TextButton(onClick = onConfirm) { Text(tr("yes")) } },
        dismissButton = {
            TextButton(onClick = onDismiss) { Text(tr("no"), color = BcColors.TextMuted) }
        },
    )
}

/** Circular status dot used in list rows. */
@Composable
fun Dot(kind: String, modifier: Modifier = Modifier) {
    val (fg, _) = badgeColors(kind)
    Box(modifier.size(8.dp).background(fg, RoundedCornerShape(4.dp)))
}
