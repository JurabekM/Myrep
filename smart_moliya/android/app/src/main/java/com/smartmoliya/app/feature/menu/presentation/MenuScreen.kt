package com.smartmoliya.app.feature.menu.presentation

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.EmojiEvents
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp

@Composable
fun MenuScreen(
    onNavigateToPayments: () -> Unit,
    onNavigateToGamification: () -> Unit,
    onNavigateToFamily: () -> Unit,
    onNavigateToProfile: () -> Unit
) {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Text(text = "Menyu", style = MaterialTheme.typography.headlineSmall)

        if (com.smartmoliya.app.BuildConfig.OFFLINE_MODE) {
            MenuItem(Icons.Default.CreditCard, "Hamyonni to'ldirish", "Naqd to'ldirish (qurilmada)", onNavigateToPayments)
            MenuItem(Icons.Default.EmojiEvents, "Yutuqlar", "XP, nishonlar, challenge'lar", onNavigateToGamification)
            MenuItem(Icons.Default.Groups, "Vazifalar va mukofotlar", "Vazifa bajarilsa mukofot hamyonga tushadi", onNavigateToFamily)
        } else {
            MenuItem(Icons.Default.CreditCard, "Hamyonni to'ldirish", "Click / Payme / Uzum Bank", onNavigateToPayments)
            MenuItem(Icons.Default.EmojiEvents, "Yutuqlar", "XP, nishonlar, challenge'lar, reyting", onNavigateToGamification)
            MenuItem(Icons.Default.Groups, "Oila rejimi", "Pocket money, vazifalar, mukofotlar", onNavigateToFamily)
        }
        MenuItem(Icons.Default.Person, "Profil va sozlamalar", "Tema tanlash, hisob ma'lumotlari", onNavigateToProfile)
    }
}

@Composable
private fun MenuItem(icon: ImageVector, title: String, subtitle: String, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(MaterialTheme.colorScheme.surface, RoundedCornerShape(18.dp))
            .clickable(onClick = onClick)
            .padding(16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary
            )
        }
        Column(
            modifier = Modifier
                .weight(1f)
                .padding(horizontal = 14.dp)
        ) {
            Text(text = title, style = MaterialTheme.typography.titleSmall)
            Text(
                text = subtitle,
                style = MaterialTheme.typography.labelMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        Icon(
            imageVector = Icons.Default.ChevronRight,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}
