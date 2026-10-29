package uz.mpay.wallet.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import uz.mpay.wallet.app.Lang
import uz.mpay.wallet.app.R

/** Sozlamalar ekrani holati va amallari (Activity beradi). */
class SettingsModel(
    val lang: Lang,
    val biometricAvailable: Boolean,
    val biometricUnlock: Boolean,
    val notifications: Boolean,
    val server: String,
    val serverPinned: Boolean,
    val version: String,
    val debugTools: Boolean,
    val onLang: (Lang) -> Unit,
    val onBiometric: (Boolean) -> Unit,
    val onNotifications: (Boolean) -> Unit,
    val onChangePin: () -> Unit,
    val onDefaultPayment: () -> Unit,
    val onVirtualNfc: () -> Unit,
    val onReset: () -> Unit,
    val onBack: () -> Unit,
)

@Composable
fun SettingsScreen(m: SettingsModel) {
    var langDialog by remember { mutableStateOf(false) }
    var resetDialog by remember { mutableStateOf(false) }
    val names = mapOf(Lang.UZ to "O'zbekcha", Lang.RU to "Русский", Lang.EN to "English")
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.settings), onBack = m.onBack)
        Column(Modifier.fillMaxSize().padding(horizontal = 20.dp).verticalScroll(rememberScrollState())) {
            SectionTitle(stringResource(R.string.set_general))
            Group {
                Item(MpayIcons.Globe, stringResource(R.string.set_language), names.getValue(m.lang), "set_lang") { langDialog = true }
                ToggleItem(Icons.Filled.Notifications, stringResource(R.string.set_notifications), m.notifications, "set_notify", m.onNotifications)
            }
            SectionTitle(stringResource(R.string.set_security))
            Group {
                Item(Icons.Filled.Lock, stringResource(R.string.set_change_pin), null, "set_pin", onClick = m.onChangePin)
                if (m.biometricAvailable) {
                    ToggleItem(MpayIcons.Fingerprint, stringResource(R.string.set_biometric), m.biometricUnlock, "set_bio", m.onBiometric)
                }
            }
            SectionTitle(stringResource(R.string.set_payments))
            Group {
                Item(MpayIcons.Contactless, stringResource(R.string.set_default_app), stringResource(R.string.set_default_app_sub), "set_default_app", onClick = m.onDefaultPayment)
                if (m.debugTools) Item(MpayIcons.Contactless, stringResource(R.string.set_virtual_nfc), "127.0.0.1:47661", "set_vnfc", onClick = m.onVirtualNfc)
            }
            SectionTitle(stringResource(R.string.set_about))
            Group {
                Item(Icons.Filled.Info, stringResource(R.string.set_version), m.version, "set_version") {}
                Item(MpayIcons.Shield, stringResource(R.string.set_server), m.server + "\n" + stringResource(if (m.serverPinned) R.string.set_server_pinned else R.string.set_server_tofu), "set_server") {}
            }
            Spacer(Modifier.height(16.dp))
            Group {
                Item(Icons.Filled.Delete, stringResource(R.string.set_reset), stringResource(R.string.set_reset_sub), "set_reset", danger = true) { resetDialog = true }
            }
            Spacer(Modifier.height(32.dp))
        }
    }
    if (langDialog) {
        AlertDialog(
            onDismissRequest = { langDialog = false },
            title = { Text(stringResource(R.string.set_language)) },
            text = { LangOptions(m.lang) { langDialog = false; if (it != m.lang) m.onLang(it) } },
            confirmButton = { TextButton({ langDialog = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
    if (resetDialog) {
        AlertDialog(
            onDismissRequest = { resetDialog = false },
            title = { Text(stringResource(R.string.set_reset)) },
            text = { Text(stringResource(R.string.set_reset_confirm)) },
            confirmButton = { TextButton({ resetDialog = false; m.onReset() }) { Text(stringResource(R.string.set_reset_do), color = MpayColors.Danger) } },
            dismissButton = { TextButton({ resetDialog = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun Group(content: @Composable () -> Unit) {
    Column(Modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(MpayColors.Surface)) { content() }
}

@Composable
private fun Item(icon: ImageVector, title: String, sub: String?, tag: String, danger: Boolean = false, onClick: () -> Unit) {
    Row(Modifier.fillMaxWidth().clickable(onClick = onClick).padding(16.dp).testTag(tag), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, tint = if (danger) MpayColors.Danger else MpayColors.Mint, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(14.dp))
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.bodyLarge, color = if (danger) MpayColors.Danger else MpayColors.TextPrimary)
            if (sub != null) Text(sub, style = MaterialTheme.typography.labelMedium, color = MpayColors.TextSecondary)
        }
    }
}

@Composable
private fun ToggleItem(icon: ImageVector, title: String, value: Boolean, tag: String, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth().clickable { onChange(!value) }.padding(horizontal = 16.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, tint = MpayColors.Mint, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(14.dp))
        Text(title, style = MaterialTheme.typography.bodyLarge, modifier = Modifier.weight(1f))
        Switch(value, onChange, modifier = Modifier.testTag(tag))
    }
}
