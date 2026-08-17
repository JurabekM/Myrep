package com.uzerp.mobile.ui.backup

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.ui.common.ErrorBanner
import com.uzerp.mobile.ui.common.ScreenScaffold
import com.uzerp.mobile.ui.theme.UzGreen
import com.uzerp.mobile.ui.theme.UzMuted
import com.uzerp.mobile.ui.theme.UzRed

@Composable
fun BackupScreen(onBack: () -> Unit, viewModel: BackupViewModel = hiltViewModel()) {
    val state by viewModel.state.collectAsState()
    var pendingRestoreUri by remember { mutableStateOf<Uri?>(null) }

    val pickLauncher = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri ->
        if (uri != null) pendingRestoreUri = uri
    }

    ScreenScaffold(title = "Zaxira nusxa", onBack = onBack) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp)) {
            Text(
                "Butun mahalliy ma'lumotlar bazasi (savdo, ombor, buxgalteriya, HR — hammasi) " +
                    "bitta faylga zaxiralanadi. Hech qanday tarmoq ishlatilmaydi — fayl faqat shu " +
                    "qurilmaning Yuklab olinganlar/UzERP papkasiga saqlanadi.",
                style = MaterialTheme.typography.bodyMedium,
                color = UzMuted,
            )

            state.error?.let { ErrorBanner(it) }
            state.message?.let { msg ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    colors = CardDefaults.cardColors(containerColor = UzGreen.copy(alpha = 0.12f)),
                ) {
                    Text(msg, color = UzGreen, modifier = Modifier.padding(12.dp), style = MaterialTheme.typography.bodyMedium)
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth().padding(top = 20.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Zaxira nusxa yaratish", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text(
                        "Joriy bazaning to'liq nusxasini saqlaydi.",
                        style = MaterialTheme.typography.bodySmall,
                        color = UzMuted,
                        modifier = Modifier.padding(top = 4.dp, bottom = 10.dp),
                    )
                    if (state.isLoading && !state.restoring) {
                        CircularProgressIndicator(color = UzGreen, modifier = Modifier.padding(8.dp))
                    } else {
                        Button(
                            onClick = viewModel::backup,
                            colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = UzGreen),
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("Zaxira nusxa yaratish") }
                    }
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text("Zaxiradan tiklash", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, color = UzRed)
                    Text(
                        "DIQQAT: joriy barcha ma'lumotlar tanlangan zaxira fayli bilan " +
                            "almashtiriladi. Bu amalni ortga qaytarib bo'lmaydi.",
                        style = MaterialTheme.typography.bodySmall,
                        color = UzMuted,
                        modifier = Modifier.padding(top = 4.dp, bottom = 10.dp),
                    )
                    if (state.isLoading && state.restoring) {
                        CircularProgressIndicator(color = UzRed, modifier = Modifier.padding(8.dp))
                    } else {
                        OutlinedButton(
                            onClick = { pickLauncher.launch(arrayOf("*/*")) },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("Zaxira faylni tanlash va tiklash") }
                    }
                }
            }
        }
    }

    pendingRestoreUri?.let { uri ->
        AlertDialog(
            onDismissRequest = { pendingRestoreUri = null },
            title = { Text("Tiklashni tasdiqlang") },
            text = { Text("Bu joriy ma'lumotlarni tanlangan zaxira fayli bilan almashtiradi va ilova qayta ishga tushiriladi. Davom etasizmi?") },
            confirmButton = {
                Button(
                    onClick = {
                        val u = uri
                        pendingRestoreUri = null
                        viewModel.restore(u) {
                            android.os.Process.killProcess(android.os.Process.myPid())
                        }
                    },
                    colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = UzRed),
                ) { Text("Ha, tiklash") }
            },
            dismissButton = { TextButton(onClick = { pendingRestoreUri = null }) { Text("Bekor qilish") } },
        )
    }
}
