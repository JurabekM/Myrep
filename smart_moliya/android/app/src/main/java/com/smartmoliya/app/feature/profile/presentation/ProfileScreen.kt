package com.smartmoliya.app.feature.profile.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.offset
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.BuildConfig
import com.smartmoliya.app.ui.components.SectionHeader
import com.smartmoliya.app.ui.theme.AppThemeId
import com.smartmoliya.app.ui.theme.themePreviewColors

@Composable
fun ProfileScreen(onLoggedOut: () -> Unit, viewModel: ProfileViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val currentTheme by viewModel.currentTheme.collectAsState()

    LaunchedEffect(state.loggedOut) {
        if (state.loggedOut) onLoggedOut()
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp)
    ) {
        item {
            Text(text = "Profil va sozlamalar", style = MaterialTheme.typography.headlineSmall)
        }

        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp))
                    .padding(16.dp)
            ) {
                if (BuildConfig.OFFLINE_MODE) {
                    Text(text = "Offline rejim", style = MaterialTheme.typography.titleMedium)
                    Text(
                        text = "Barcha ma'lumotlaringiz faqat shu qurilmada, shifrlangan bazada saqlanadi. " +
                            "Hisob, server va internetga ulanish talab qilinmaydi.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(top = 6.dp)
                    )
                } else {
                    Text(
                        text = state.user?.full_name ?: "Foydalanuvchi",
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = state.user?.phone ?: state.user?.email ?: "",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }

        item { SectionHeader(title = "🎨 Ilova mavzusi") }

        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(20.dp))
                    .padding(8.dp)
            ) {
                AppThemeId.entries.forEach { themeId ->
                    ThemeOptionRow(
                        themeId = themeId,
                        selected = themeId == currentTheme,
                        onSelect = { viewModel.setTheme(themeId) }
                    )
                }
            }
        }

        if (!BuildConfig.OFFLINE_MODE) {
            item {
                Button(
                    onClick = { viewModel.logout() },
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(top = 8.dp)
                ) {
                    Text("Chiqish")
                }
            }
        }
    }
}

@Composable
private fun ThemeOptionRow(themeId: AppThemeId, selected: Boolean, onSelect: () -> Unit) {
    val previewColors = themePreviewColors(themeId)

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onSelect)
            .background(
                if (selected) MaterialTheme.colorScheme.primary.copy(alpha = 0.12f)
                else MaterialTheme.colorScheme.surface,
                RoundedCornerShape(14.dp)
            )
            .padding(horizontal = 12.dp, vertical = 12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Uchta rang doirachasi - tema ko'rgazmasi
        Row {
            previewColors.forEachIndexed { index, color ->
                Box(
                    modifier = Modifier
                        .offset(x = (-6 * index).dp)
                        .size(26.dp)
                        .background(color, CircleShape)
                        .border(2.dp, MaterialTheme.colorScheme.surface, CircleShape)
                )
            }
        }
        Text(
            text = themeId.title,
            style = MaterialTheme.typography.titleSmall,
            modifier = Modifier
                .weight(1f)
                .padding(start = 8.dp)
        )
        if (selected) {
            Icon(
                imageVector = Icons.Default.Check,
                contentDescription = "Tanlangan",
                tint = MaterialTheme.colorScheme.primary
            )
        }
    }
}
