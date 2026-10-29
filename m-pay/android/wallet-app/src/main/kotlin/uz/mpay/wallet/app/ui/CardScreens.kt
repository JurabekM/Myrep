package uz.mpay.wallet.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.runtime.snapshotFlow
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import uz.mpay.core.WalletCard
import uz.mpay.wallet.app.Format
import uz.mpay.wallet.app.Lang
import uz.mpay.wallet.app.R
import uz.mpay.wallet.app.Screen
import uz.mpay.wallet.app.WalletViewModel

@Composable
fun CardScreen(vm: WalletViewModel, tokenId: String) {
    val card = vm.cards.firstOrNull { it.tokenId == tokenId }
    var confirmDelete by remember { mutableStateOf(false) }
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.card_manage), onBack = { vm.back() })
        if (card == null) {
            EmptyState(MpayIcons.Card, stringResource(R.string.err_card_not_found), "")
            return
        }
        Column(Modifier.fillMaxSize().padding(horizontal = 20.dp).verticalScroll(rememberScrollState())) {
            CardVisual(card)
            Spacer(Modifier.height(16.dp))
            if (card.state == "SUSPENDED") {
                Banner(
                    Icons.Filled.Warning,
                    if (card.suspendedBy == "BANK") stringResource(R.string.banner_suspended_bank) else stringResource(R.string.banner_suspended_self),
                    MpayColors.Warning,
                )
            } else if (!card.onDevice) {
                Banner(Icons.Filled.Info, stringResource(R.string.banner_not_on_device), MpayColors.Warning)
            } else if (card.luksLeft == 0) {
                Banner(Icons.Filled.Info, stringResource(R.string.banner_no_keys), MpayColors.Warning)
            }
            Column(Modifier.clip(RoundedCornerShape(16.dp)).background(MpayColors.Surface).padding(horizontal = 16.dp, vertical = 6.dp)) {
                InfoRow(stringResource(R.string.info_bank_card), card.fpanMasked ?: "—")
                HorizontalDivider(color = MpayColors.Outline)
                InfoRow(stringResource(R.string.info_token), card.dpanMasked)
                HorizontalDivider(color = MpayColors.Outline)
                InfoRow(stringResource(R.string.info_expiry), Format.expiry(card.expiryYymm))
                HorizontalDivider(color = MpayColors.Outline)
                InfoRow(stringResource(R.string.info_state), stateText(card))
                if (card.onDevice) {
                    HorizontalDivider(color = MpayColors.Outline)
                    InfoRow(stringResource(R.string.info_keys), stringResource(R.string.info_keys_value, card.luksLeft))
                }
            }
            Spacer(Modifier.height(16.dp))
            if (card.onDevice && !card.isDefault && card.state == "ACTIVE") {
                ActionRow(Icons.Filled.Star, stringResource(R.string.make_default), "make_default") { vm.setDefault(card.tokenId) }
            }
            if (card.onDevice) {
                ActionRow(MpayIcons.History, stringResource(R.string.history), "card_history") { vm.go(Screen.History(card.tokenId)) }
            }
            when {
                card.state == "ACTIVE" -> ActionRow(MpayIcons.Pause, stringResource(R.string.suspend), "suspend") { vm.suspend(card.tokenId) }
                card.state == "SUSPENDED" && card.suspendedBy != "BANK" -> ActionRow(MpayIcons.Play, stringResource(R.string.resume), "resume") { vm.resume(card.tokenId) }
            }
            if (card.payable) {
                ActionRow(MpayIcons.Key, stringResource(R.string.refresh_keys), "replenish") { vm.replenish(card.tokenId) }
            }
            ActionRow(Icons.Filled.Delete, stringResource(R.string.delete_card), "delete", danger = true) { confirmDelete = true }
            Spacer(Modifier.height(24.dp))
        }
    }
    if (confirmDelete && card != null) {
        AlertDialog(
            onDismissRequest = { confirmDelete = false },
            title = { Text(stringResource(R.string.delete_card)) },
            text = { Text(stringResource(R.string.delete_confirm, Format.last4(card.dpanMasked))) },
            confirmButton = {
                TextButton({ confirmDelete = false; vm.delete(card.tokenId) }) { Text(stringResource(R.string.delete), color = MpayColors.Danger) }
            },
            dismissButton = { TextButton({ confirmDelete = false }) { Text(stringResource(R.string.cancel)) } },
        )
    }
}

@Composable
private fun stateText(card: WalletCard): String = when {
    !card.onDevice -> stringResource(R.string.state_not_on_device)
    card.state == "ACTIVE" -> stringResource(R.string.state_active)
    card.state == "SUSPENDED" && card.suspendedBy == "BANK" -> stringResource(R.string.state_suspended_bank)
    card.state == "SUSPENDED" -> stringResource(R.string.state_suspended)
    else -> card.state
}

@Composable
fun Banner(icon: ImageVector, text: String, color: Color) {
    Row(
        Modifier.fillMaxWidth().padding(bottom = 12.dp).clip(RoundedCornerShape(12.dp)).background(color.copy(alpha = 0.12f))
            .border(1.dp, color.copy(alpha = 0.4f), RoundedCornerShape(12.dp)).padding(12.dp).testTag("banner"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, null, tint = color, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(10.dp))
        Text(text, style = MaterialTheme.typography.bodyMedium)
    }
}

@Composable
private fun ActionRow(icon: ImageVector, label: String, tag: String, danger: Boolean = false, onClick: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().padding(vertical = 4.dp).clip(RoundedCornerShape(14.dp)).background(MpayColors.Surface)
            .clickable(onClick = onClick).padding(16.dp).testTag(tag),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, null, tint = if (danger) MpayColors.Danger else MpayColors.Mint, modifier = Modifier.size(22.dp))
        Spacer(Modifier.width(14.dp))
        Text(label, style = MaterialTheme.typography.bodyLarge, color = if (danger) MpayColors.Danger else MpayColors.TextPrimary)
    }
}

// ------------------------------------------------------------ to'lov

/**
 * To'lov: karta tanlanadi, biometriya (CDCVM) bilan tasdiqlanadi, so'ng 60 s ichida telefon terminalga
 * yaqinlashtiriladi. Natija emitent tarixidan olinadi.
 */
@Composable
fun PayScreen(
    vm: WalletViewModel,
    lang: Lang,
    biometricAvailable: Boolean,
    secondsLeft: () -> Int,
    selected: String?,
    onSelect: (String) -> Unit,
    onAuthenticate: () -> Unit,
    tappedToken: String?,
) {
    val payable = vm.cards.filter { it.payable }
    val card = payable.firstOrNull { it.tokenId == selected } ?: payable.firstOrNull { it.isDefault } ?: payable.firstOrNull()
    var seconds by remember { mutableIntStateOf(0) }
    LaunchedEffect(Unit) { while (true) { seconds = secondsLeft(); delay(300) } }
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.pay), onBack = { vm.clearPayment(); vm.back() })
        if (card == null) {
            EmptyState(MpayIcons.Card, stringResource(R.string.no_payable_title), stringResource(R.string.no_payable_body))
            return
        }
        Column(Modifier.fillMaxSize().padding(horizontal = 20.dp).verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
            CardVisual(card)
            if (payable.size > 1) {
                Spacer(Modifier.height(10.dp))
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    items(payable, key = { it.tokenId }) { c ->
                        val sel = c.tokenId == card.tokenId
                        Text(
                            Format.last4(c.dpanMasked),
                            color = if (sel) MpayColors.Background else MpayColors.TextPrimary,
                            modifier = Modifier.clip(RoundedCornerShape(50)).background(if (sel) MpayColors.Mint else MpayColors.Surface)
                                .clickable { onSelect(c.tokenId) }.padding(horizontal = 14.dp, vertical = 8.dp).testTag("pick_${c.dpanMasked.takeLast(4)}"),
                        )
                    }
                }
            }
            Spacer(Modifier.height(28.dp))
            val result = vm.lastPayment
            when {
                result != null -> PayResult(result, lang) { vm.clearPayment() }
                tappedToken != null -> {
                    CircularProgressIndicator(Modifier.size(48.dp))
                    Spacer(Modifier.height(12.dp))
                    Text(stringResource(R.string.pay_sent), style = MaterialTheme.typography.titleMedium, modifier = Modifier.testTag("pay_sent"))
                }
                seconds > 0 -> {
                    Box(Modifier.size(140.dp).clip(CircleShape).background(MpayColors.Mint.copy(alpha = 0.12f)).border(2.dp, MpayColors.Mint, CircleShape), contentAlignment = Alignment.Center) {
                        Icon(MpayIcons.Contactless, null, tint = MpayColors.Mint, modifier = Modifier.size(64.dp))
                    }
                    Spacer(Modifier.height(16.dp))
                    Text(stringResource(R.string.pay_ready), style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center, modifier = Modifier.testTag("pay_ready"))
                    Text(stringResource(R.string.pay_seconds, seconds), color = MpayColors.TextSecondary)
                }
                else -> {
                    Text(stringResource(R.string.pay_hint), style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center, color = MpayColors.TextSecondary)
                    Spacer(Modifier.height(20.dp))
                    if (biometricAvailable) {
                        Button(onAuthenticate, Modifier.fillMaxWidth().height(56.dp).testTag("pay_auth"), shape = RoundedCornerShape(16.dp)) {
                            Icon(MpayIcons.Fingerprint, null)
                            Spacer(Modifier.width(10.dp))
                            Text(stringResource(R.string.pay_auth))
                        }
                    } else {
                        Banner(Icons.Filled.Warning, stringResource(R.string.pay_no_biometric), MpayColors.Warning)
                    }
                }
            }
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun PayResult(t: uz.mpay.core.Txn, lang: Lang, onDone: () -> Unit) {
    val ok = t.status == "APPROVED"
    val color = if (ok) MpayColors.Success else MpayColors.Danger
    Icon(if (ok) Icons.Filled.CheckCircle else Icons.Filled.Warning, null, tint = color, modifier = Modifier.size(72.dp))
    Spacer(Modifier.height(12.dp))
    Text(
        if (ok) stringResource(R.string.pay_approved) else stringResource(R.string.pay_declined, t.responseCode),
        style = MaterialTheme.typography.titleLarge, color = color, modifier = Modifier.testTag("pay_result"),
    )
    Text(Format.money(t.amountMinor, t.currency, lang), style = MaterialTheme.typography.headlineMedium)
    Text(t.merchantId, color = MpayColors.TextSecondary)
    Spacer(Modifier.height(20.dp))
    OutlinedButton(onDone, Modifier.testTag("pay_done")) { Text(stringResource(R.string.done)) }
}

// ------------------------------------------------------------ tarix

@Composable
fun HistoryScreen(vm: WalletViewModel, lang: Lang, initial: String?) {
    val local = vm.cards.filter { it.onDevice }
    var tokenId by remember { mutableStateOf(initial?.takeIf { id -> local.any { it.tokenId == id } } ?: local.firstOrNull()?.tokenId) }
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.history), onBack = { vm.back() })
        val id = tokenId
        if (id == null) {
            EmptyState(MpayIcons.History, stringResource(R.string.no_txns), "")
            return
        }
        if (local.size > 1) {
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.padding(horizontal = 20.dp, vertical = 4.dp)) {
                items(local, key = { it.tokenId }) { c ->
                    val sel = c.tokenId == id
                    Text(
                        Format.last4(c.dpanMasked),
                        color = if (sel) MpayColors.Background else MpayColors.TextPrimary,
                        modifier = Modifier.clip(RoundedCornerShape(50)).background(if (sel) MpayColors.Mint else MpayColors.Surface)
                            .clickable { tokenId = c.tokenId }.padding(horizontal = 14.dp, vertical = 8.dp).testTag("hist_${c.dpanMasked.takeLast(4)}"),
                    )
                }
            }
        }
        LaunchedEffect(id) { if (vm.history[id] == null) vm.loadHistory(id, reset = true) }
        val h = vm.history[id]
        val list = rememberLazyListState()
        // Oxiriga yaqinlashganda keyingi sahifa.
        LaunchedEffect(list, id) {
            snapshotFlow { list.layoutInfo.visibleItemsInfo.lastOrNull()?.index to list.layoutInfo.totalItemsCount }
                .collect { (last, total) -> if (last != null && total > 0 && last >= total - 3) vm.loadHistory(id) }
        }
        val items = h?.items.orEmpty()
        LazyColumn(state = list, modifier = Modifier.fillMaxSize().padding(horizontal = 20.dp).testTag("history_list")) {
            var lastDay: String? = null
            items.forEach { t ->
                val day = Format.day(t.at)
                if (day != lastDay) {
                    lastDay = day
                    item(key = "d_$day") { SectionTitle(day) }
                }
                item(key = t.id) { TxnRow(t, lang) }
            }
            item(key = "footer") {
                Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                    when {
                        h == null || h.loading -> CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
                        h.error != null -> TextButton({ vm.loadHistory(id, reset = items.isEmpty()) }) { Text(stringResource(R.string.retry)) }
                        items.isEmpty() -> Text(stringResource(R.string.no_txns), color = MpayColors.TextSecondary, modifier = Modifier.testTag("no_txns"))
                        h.end -> Text(stringResource(R.string.history_end), color = MpayColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
                    }
                }
            }
        }
    }
}
