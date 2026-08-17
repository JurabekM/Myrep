package com.aetherq.messenger.ui.nav

import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.aetherq.messenger.AppContainer
import com.aetherq.messenger.crypto.ContactCardCodec
import com.aetherq.messenger.crypto.SelfTest
import com.aetherq.messenger.ui.SimpleViewModelFactory
import com.aetherq.messenger.ui.chat.ChatScreen
import com.aetherq.messenger.ui.chat.ChatViewModel
import com.aetherq.messenger.ui.contacts.ContactsScreen
import com.aetherq.messenger.ui.contacts.ContactsViewModel
import com.aetherq.messenger.ui.contacts.OwnQrScreen
import com.aetherq.messenger.ui.contacts.ScanContactScreen

@Composable
fun AppNav(container: AppContainer) {
    val navController = rememberNavController()
    var selfTestResult by remember { mutableStateOf<SelfTest.Result?>(null) }
    val contactsViewModel: ContactsViewModel =
        viewModel(factory = SimpleViewModelFactory { ContactsViewModel(container.repository) })

    NavHost(navController = navController, startDestination = "contacts") {
        composable("contacts") {
            val contacts by contactsViewModel.contacts.collectAsState()
            ContactsScreen(
                contacts = contacts,
                onOpenChat = { userId -> navController.navigate("chat/$userId") },
                onScanQr = { navController.navigate("scan") },
                onShowOwnQr = { navController.navigate("own_qr") },
                onSelfTest = { selfTestResult = SelfTest.run() },
            )
        }

        composable("own_qr") {
            val card = ContactCardCodec.fromIdentity(container.identity)
            OwnQrScreen(payload = ContactCardCodec.encode(card))
        }

        composable("scan") {
            ScanContactScreen(
                onScanned = { raw ->
                    runCatching { ContactCardCodec.decode(raw) }
                        .onSuccess { card -> contactsViewModel.addContact(card, "Kontakt-${card.userId.take(6)}") }
                    navController.popBackStack()
                },
                onCancelled = { navController.popBackStack() },
            )
        }

        composable("chat/{userId}") { backStackEntry ->
            val userId = backStackEntry.arguments?.getString("userId")
            val contacts by contactsViewModel.contacts.collectAsState()
            val contact = contacts.find { it.userId == userId }
            if (contact != null) {
                val chatViewModel: ChatViewModel =
                    viewModel(
                        key = userId,
                        factory = SimpleViewModelFactory { ChatViewModel(container.repository, contact) },
                    )
                val messages by chatViewModel.messages.collectAsState()
                ChatScreen(
                    contact = contact,
                    messages = messages,
                    onSend = chatViewModel::send,
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }

    selfTestResult?.let { result ->
        AlertDialog(
            onDismissRequest = { selfTestResult = null },
            title = { Text(if (result.success) "Self-test: MUVAFFAQIYATLI" else "Self-test: XATO") },
            text = { Text(result.details) },
            confirmButton = { TextButton(onClick = { selfTestResult = null }) { Text("OK") } },
        )
    }
}
