package com.aetherq.messenger.ui.contacts

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.FloatingActionButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.ListItem
import androidx.compose.material3.ListItemDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.aetherq.messenger.data.local.entity.ContactEntity
import com.aetherq.messenger.ui.theme.AetherTextSecondary

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ContactsScreen(
    contacts: List<ContactEntity>,
    onOpenChat: (String) -> Unit,
    onScanQr: () -> Unit,
    onShowOwnQr: () -> Unit,
    onSelfTest: () -> Unit,
) {
    Scaffold(
        containerColor = MaterialTheme.colorScheme.background,
        topBar = {
            TopAppBar(
                title = { Text("AETHER-Q Messenger", fontWeight = FontWeight.SemiBold) },
                actions = {
                    TextButton(onClick = onSelfTest) { Text("Self-test") }
                    TextButton(onClick = onShowOwnQr) { Text("Mening QR") }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                ),
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onScanQr,
                containerColor = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                elevation = FloatingActionButtonDefaults.elevation(4.dp),
            ) {
                Icon(Icons.Default.Add, contentDescription = "Kontakt qo'shish")
            }
        },
    ) { padding ->
        if (contacts.isEmpty()) {
            Box(Modifier.fillMaxSize().padding(padding), contentAlignment = Alignment.Center) {
                Text("Hali kontakt yo'q — QR skanerlab qo'shing", color = AetherTextSecondary)
            }
        } else {
            LazyColumn(Modifier.fillMaxSize().padding(padding)) {
                items(contacts, key = { it.userId }) { contact ->
                    ListItem(
                        headlineContent = { Text(contact.displayName, fontWeight = FontWeight.Medium) },
                        supportingContent = { Text(contact.userId, color = AetherTextSecondary) },
                        colors = ListItemDefaults.colors(containerColor = MaterialTheme.colorScheme.background),
                        modifier =
                            Modifier
                                .fillMaxWidth()
                                .clickable { onOpenChat(contact.userId) },
                    )
                }
            }
        }
    }
}
