package com.uzerp.mobile.ui.common

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.uzerp.mobile.core.money
import com.uzerp.mobile.ui.theme.UzAccent
import com.uzerp.mobile.ui.theme.UzAmber
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzRed
import com.uzerp.mobile.ui.theme.UzViolet
import java.math.BigDecimal

/** Standart sahifa qobig'i: sarlavha, orqaga tugma, FAB (ixtiyoriy). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ScreenScaffold(
    title: String,
    onBack: (() -> Unit)? = null,
    fabIcon: androidx.compose.ui.graphics.vector.ImageVector? = null,
    onFabClick: (() -> Unit)? = null,
    content: @Composable (PaddingValues) -> Unit,
) {
    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(title, fontWeight = FontWeight.SemiBold) },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Orqaga")
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface),
            )
        },
        floatingActionButton = {
            if (fabIcon != null && onFabClick != null) {
                FloatingActionButton(onClick = onFabClick, containerColor = UzAccent) {
                    Icon(fabIcon, contentDescription = null, tint = Color.White)
                }
            }
        },
        content = content,
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SearchField(value: String, onValueChange: (String) -> Unit, placeholder: String = "Qidiruv...") {
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        placeholder = { Text(placeholder) },
        leadingIcon = { Icon(Icons.Filled.Search, null, tint = UzMuted) },
        singleLine = true,
        shape = androidx.compose.foundation.shape.RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
        colors = OutlinedTextFieldDefaults.colors(focusedBorderColor = UzAccent, unfocusedBorderColor = MaterialTheme.colorScheme.outline),
    )
}

/**
 * Ro'yxat elementi kartochkasi (bosilganda `onClick`). [leadingIcon]
 * berilsa chap tomonda rangli yumaloq ikonka konteyneri chiziladi —
 * barcha ro'yxatlarga bir xil zamonaviy ko'rinish beradi.
 */
@Composable
fun ListRowCard(
    title: String,
    subtitle: String? = null,
    trailing: String? = null,
    badge: (@Composable () -> Unit)? = null,
    onClick: (() -> Unit)? = null,
    leadingIcon: androidx.compose.ui.graphics.vector.ImageVector? = null,
    iconTint: Color = UzAccent,
) {
    val baseModifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 5.dp)
    Card(
        modifier = if (onClick != null) baseModifier.clickable(onClick = onClick) else baseModifier,
        shape = androidx.compose.foundation.shape.RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(14.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            if (leadingIcon != null) {
                Box(
                    modifier = Modifier
                        .padding(end = 12.dp)
                        .size(42.dp)
                        .background(
                            iconTint.copy(alpha = 0.15f),
                            androidx.compose.foundation.shape.RoundedCornerShape(13.dp),
                        ),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(leadingIcon, contentDescription = null, tint = iconTint, modifier = Modifier.size(22.dp))
                }
            }
            Column(modifier = Modifier.weight(1f)) {
                Text(title, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.SemiBold)
                if (subtitle != null) {
                    Text(subtitle, color = UzMuted, style = MaterialTheme.typography.bodyMedium)
                }
            }
            if (trailing != null) {
                Text(trailing, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.SemiBold)
            }
            if (badge != null) {
                Spacer(Modifier.width(8.dp))
                badge()
            }
        }
    }
}

/** Holat belgisi (rangli) — web `badge()` bilan bir xil ranglar. */
@Composable
fun StatusChip(status: String) {
    val (label, color) = statusStyle(status)
    Surface(color = color.copy(alpha = 0.16f), shape = androidx.compose.foundation.shape.RoundedCornerShape(20.dp)) {
        Text(
            label,
            color = color,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp),
        )
    }
}

private fun statusStyle(status: String): Pair<String, Color> = when (status) {
    "draft" -> "Qoralama" to UzMuted
    "confirmed" -> "Tasdiqlangan" to UzAccent
    "partial" -> "Qisman to'langan" to UzAmber
    "paid" -> "To'langan" to UzGreen
    "received" -> "Qabul qilingan" to UzAccent
    "cancelled" -> "Bekor qilingan" to UzRed
    "done" -> "Yakunlangan" to UzGreen
    "open" -> "Ochiq" to UzAccent
    "pending" -> "Kutilmoqda" to UzAmber
    "approved" -> "Tasdiqlangan" to UzGreen
    "rejected" -> "Rad etilgan" to UzRed
    "active" -> "Faol" to UzGreen
    "new" -> "Yangi" to UzAccent
    "contacted" -> "Aloqa qilindi" to UzAmber
    "qualified" -> "Malakali" to UzViolet
    "won" -> "Yutildi" to UzGreen
    "lost" -> "Yo'qotildi" to UzRed
    "terminated" -> "Bo'shatilgan" to UzRed
    "leave" -> "Ta'tilda" to UzAmber
    else -> status to UzMuted
}

/** Bo'sh ro'yxat holati matni. */
@Composable
fun EmptyState(text: String) {
    Box(modifier = Modifier.fillMaxWidth().padding(32.dp), contentAlignment = Alignment.Center) {
        Text(text, color = UzMuted, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
fun LoadingState() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator(color = UzAccent)
    }
}

@Composable
fun ErrorBanner(message: String) {
    Surface(color = UzRed.copy(alpha = 0.12f), modifier = Modifier.fillMaxWidth().padding(16.dp, 8.dp)) {
        Text(message, color = UzRed, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodyMedium)
    }
}

/** Pul qiymatini formatlab ko'rsatadi. */
@Composable
fun MoneyText(value: BigDecimal, color: Color = MaterialTheme.colorScheme.onSurface) {
    Text(money(value), color = color, fontWeight = FontWeight.SemiBold)
}

@Composable
fun SectionLabel(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.labelSmall,
        color = UzMuted,
        modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp),
    )
}
