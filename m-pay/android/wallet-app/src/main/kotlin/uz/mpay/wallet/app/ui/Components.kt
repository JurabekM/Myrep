package uz.mpay.wallet.app.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.Star
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import uz.mpay.core.Txn
import uz.mpay.core.WalletCard
import uz.mpay.wallet.app.Format
import uz.mpay.wallet.app.Lang
import uz.mpay.wallet.app.PinPolicy
import uz.mpay.wallet.app.R

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MpayTopBar(title: String, onBack: (() -> Unit)?, actions: @Composable () -> Unit = {}) {
    TopAppBar(
        title = { Text(title, style = MaterialTheme.typography.titleLarge, maxLines = 1, overflow = TextOverflow.Ellipsis) },
        navigationIcon = {
            if (onBack != null) {
                IconButton(onBack, modifier = Modifier.testTag("back")) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, stringResource(R.string.back))
                }
            }
        },
        actions = { actions() },
        colors = TopAppBarDefaults.topAppBarColors(containerColor = MpayColors.Background),
    )
}

/** Karta tasviri: maskalangan DPAN, muddat, holat; to'xtatilgan — kulrang. */
@Composable
fun CardVisual(card: WalletCard, modifier: Modifier = Modifier) {
    val active = card.state == "ACTIVE" && card.onDevice
    Box(
        modifier
            .fillMaxWidth()
            .aspectRatio(1.586f)
            .clip(RoundedCornerShape(20.dp))
            .background(MpayColors.cardBrush(active))
            .padding(20.dp),
    ) {
        Column(Modifier.align(Alignment.TopStart)) {
            Text("M-PAY", color = Color.White, fontWeight = FontWeight.Bold, fontSize = 18.sp, letterSpacing = 2.sp)
            Text(stringResource(R.string.card_brand_sub), color = Color.White.copy(alpha = 0.7f), fontSize = 11.sp)
        }
        Icon(MpayIcons.Contactless, null, tint = Color.White.copy(alpha = 0.85f), modifier = Modifier.align(Alignment.TopEnd).size(28.dp))
        if (card.isDefault) {
            Row(
                Modifier.align(Alignment.CenterEnd).clip(RoundedCornerShape(50)).background(Color.White.copy(alpha = 0.16f)).padding(horizontal = 10.dp, vertical = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Filled.Star, null, tint = Color.White, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(4.dp))
                Text(stringResource(R.string.card_default), color = Color.White, fontSize = 11.sp)
            }
        }
        Column(Modifier.align(Alignment.BottomStart)) {
            Text(
                "•••• •••• •••• " + card.dpanMasked.takeLast(4),
                color = Color.White, fontSize = 20.sp, fontFamily = FontFamily.Monospace, letterSpacing = 1.sp,
                modifier = Modifier.testTag("card_number"),
            )
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(16.dp)) {
                Text(Format.expiry(card.expiryYymm), color = Color.White.copy(alpha = 0.85f), fontSize = 13.sp)
                card.fpanMasked?.let { Text(stringResource(R.string.card_bank_last4, it.takeLast(4)), color = Color.White.copy(alpha = 0.85f), fontSize = 13.sp) }
            }
        }
        val badge = when {
            card.state == "PENDING_IDV" -> stringResource(R.string.state_pending)
            !card.onDevice -> stringResource(R.string.state_not_on_device)
            card.state == "SUSPENDED" && card.suspendedBy == "BANK" -> stringResource(R.string.state_suspended_bank)
            card.state == "SUSPENDED" -> stringResource(R.string.state_suspended)
            card.state != "ACTIVE" -> card.state
            else -> null
        }
        if (badge != null) {
            Text(
                badge,
                color = Color.Black,
                fontSize = 12.sp,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.align(Alignment.BottomEnd).clip(RoundedCornerShape(50)).background(MpayColors.Warning).padding(horizontal = 10.dp, vertical = 4.dp)
                    .testTag("card_badge"),
            )
        }
    }
}

/** Katta amal plitkasi (bosh ekran). */
@Composable
fun ActionTile(icon: ImageVector, label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier.clip(RoundedCornerShape(16.dp)).background(MpayColors.Surface).clickable(onClick = onClick).padding(vertical = 14.dp, horizontal = 8.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(MpayColors.SurfaceHigh), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = MpayColors.Mint, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.height(8.dp))
        Text(label, style = MaterialTheme.typography.labelMedium, textAlign = TextAlign.Center, maxLines = 2, color = MpayColors.TextPrimary)
    }
}

@Composable
fun SectionTitle(text: String, modifier: Modifier = Modifier) {
    Text(text.uppercase(), style = MaterialTheme.typography.labelMedium, color = MpayColors.TextSecondary, letterSpacing = 1.sp, modifier = modifier.padding(top = 8.dp, bottom = 4.dp))
}

/** Tranzaksiya qatori: savdo nuqtasi, vaqt, holat, summa. */
@Composable
fun TxnRow(t: Txn, lang: Lang, modifier: Modifier = Modifier) {
    val (label, color) = when (t.status) {
        "APPROVED" -> stringResource(R.string.txn_approved) to MpayColors.Success
        "REVERSED" -> stringResource(R.string.txn_reversed) to MpayColors.Warning
        else -> stringResource(R.string.txn_declined_code, t.responseCode) to MpayColors.Danger
    }
    Row(modifier.fillMaxWidth().padding(vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(MpayColors.SurfaceHigh), contentAlignment = Alignment.Center) {
            Icon(MpayIcons.Contactless, null, tint = color, modifier = Modifier.size(20.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f)) {
            Text(t.merchantId, style = MaterialTheme.typography.bodyLarge, maxLines = 1, overflow = TextOverflow.Ellipsis)
            Text("${Format.time(t.at, lang)} · $label", style = MaterialTheme.typography.labelMedium, color = color)
        }
        Text(
            (if (t.status == "APPROVED") "−" else "") + Format.money(t.amountMinor, t.currency, lang),
            style = MaterialTheme.typography.titleMedium,
            color = if (t.status == "APPROVED") MpayColors.TextPrimary else MpayColors.TextSecondary,
            textDecoration = if (t.status == "APPROVED") null else TextDecoration.LineThrough,
        )
    }
}

/** Bo'sh holat: belgi, sarlavha, izoh. */
@Composable
fun EmptyState(icon: ImageVector, title: String, body: String, modifier: Modifier = Modifier) {
    Column(modifier.fillMaxWidth().padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Box(Modifier.size(72.dp).clip(CircleShape).background(MpayColors.Surface), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = MpayColors.Mint, modifier = Modifier.size(36.dp))
        }
        Spacer(Modifier.height(12.dp))
        Text(title, style = MaterialTheme.typography.titleMedium, textAlign = TextAlign.Center)
        Spacer(Modifier.height(4.dp))
        Text(body, style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary, textAlign = TextAlign.Center)
    }
}

/** PIN nuqtalari. */
@Composable
fun PinDots(filled: Int, error: Boolean = false) {
    Row(horizontalArrangement = Arrangement.spacedBy(14.dp), modifier = Modifier.testTag("pin_dots")) {
        repeat(PinPolicy.LENGTH) { i ->
            val c = when {
                error -> MpayColors.Danger
                i < filled -> MpayColors.Mint
                else -> Color.Transparent
            }
            Box(Modifier.size(14.dp).clip(CircleShape).background(c).border(1.5.dp, if (error) MpayColors.Danger else MpayColors.Mint, CircleShape))
        }
    }
}

/** Raqamli klaviatura (tizim klaviaturasisiz — PIN maydoni nusxalanmaydi). */
@Composable
fun PinPad(onDigit: (Char) -> Unit, onDelete: () -> Unit, extra: (@Composable () -> Unit)? = null) {
    val rows = listOf("123", "456", "789")
    Column(verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        rows.forEach { r ->
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) { r.forEach { d -> PinKey(d.toString(), Modifier.testTag("key_$d")) { onDigit(d) } } }
        }
        Row(horizontalArrangement = Arrangement.spacedBy(20.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(Modifier.size(72.dp), contentAlignment = Alignment.Center) { extra?.invoke() }
            PinKey("0", Modifier.testTag("key_0")) { onDigit('0') }
            Box(Modifier.size(72.dp).clip(CircleShape).clickable(onClick = onDelete).testTag("key_del"), contentAlignment = Alignment.Center) {
                Icon(Icons.Filled.Clear, stringResource(R.string.delete_digit), tint = MpayColors.TextSecondary)
            }
        }
    }
}

@Composable
private fun PinKey(label: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Box(modifier.size(72.dp).clip(CircleShape).background(MpayColors.Surface).clickable(onClick = onClick), contentAlignment = Alignment.Center) {
        Text(label, fontSize = 26.sp, fontWeight = FontWeight.Medium, color = MpayColors.TextPrimary)
    }
}

/** Ma'lumot qatori (nom — qiymat). */
@Composable
fun InfoRow(label: String, value: String, modifier: Modifier = Modifier) {
    Row(modifier.fillMaxWidth().padding(vertical = 8.dp), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MpayColors.TextSecondary, style = MaterialTheme.typography.bodyMedium)
        Spacer(Modifier.width(12.dp))
        Text(value, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.End)
    }
}
