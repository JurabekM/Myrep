package uz.dehqonkomakchi.app.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Slider
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.dehqonkomakchi.app.BuildConfig
import uz.dehqonkomakchi.app.R
import uz.dehqonkomakchi.app.work.IrrigationReminderWorker

@Composable
fun SettingsScreen(
    onOpenPrivacy: () -> Unit,
    onOpenTerms: () -> Unit,
    viewModel: SettingsViewModel = hiltViewModel(),
) {
    val settings by viewModel.settings.collectAsState()
    val context = LocalContext.current
    var showDeleteConfirm by remember { mutableStateOf(false) }

    Scaffold { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            Text(stringResource(R.string.settings_title), style = MaterialTheme.typography.headlineMedium)

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.settings_region), style = MaterialTheme.typography.titleMedium)
                    Text("${settings.region} — ${settings.district}", style = MaterialTheme.typography.bodyLarge)
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.padding(16.dp).fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                ) {
                    Text(stringResource(R.string.settings_notifications), style = MaterialTheme.typography.titleMedium)
                    Switch(
                        checked = settings.notificationsEnabled,
                        onCheckedChange = { enabled ->
                            viewModel.setNotifications(enabled)
                            if (enabled) IrrigationReminderWorker.schedule(context) else IrrigationReminderWorker.cancel(context)
                        },
                    )
                }
            }

            Card(modifier = Modifier.fillMaxWidth()) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Text(stringResource(R.string.settings_text_size), style = MaterialTheme.typography.titleMedium)
                    Slider(
                        value = settings.textScale,
                        onValueChange = { viewModel.setTextScale(it) },
                        valueRange = 0.85f..1.4f,
                        steps = 4,
                    )
                }
            }

            OutlinedButton(onClick = onOpenPrivacy, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.settings_privacy_policy))
            }
            OutlinedButton(onClick = onOpenTerms, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.settings_terms))
            }
            Button(onClick = { showDeleteConfirm = true }, modifier = Modifier.fillMaxWidth()) {
                Text(stringResource(R.string.settings_delete_data))
            }

            Text(
                "${stringResource(R.string.settings_version)}: ${BuildConfig.VERSION_NAME}",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text(stringResource(R.string.settings_delete_data)) },
            text = { Text(stringResource(R.string.settings_delete_data_confirm)) },
            confirmButton = {
                Button(onClick = { viewModel.deleteAllData(); showDeleteConfirm = false }) {
                    Text(stringResource(R.string.action_delete))
                }
            },
            dismissButton = { Button(onClick = { showDeleteConfirm = false }) { Text(stringResource(R.string.action_cancel)) } },
        )
    }
}
