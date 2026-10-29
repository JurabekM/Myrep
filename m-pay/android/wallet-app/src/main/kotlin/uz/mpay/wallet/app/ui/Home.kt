package uz.mpay.wallet.app.ui

import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.OffsetMapping
import androidx.compose.ui.text.input.TransformedText
import androidx.compose.ui.text.input.VisualTransformation
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import uz.mpay.wallet.app.Format
import uz.mpay.wallet.app.Lang
import uz.mpay.wallet.app.R
import uz.mpay.wallet.app.Screen
import uz.mpay.wallet.app.WalletViewModel

@OptIn(ExperimentalFoundationApi::class)
@Composable
fun HomeScreen(vm: WalletViewModel, lang: Lang) {
    val cards = vm.cards
    Column(Modifier.fillMaxSize()) {
        Row(Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 8.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("M-Pay", style = MaterialTheme.typography.headlineMedium, color = MpayColors.Mint)
                if (vm.offline) Text(stringResource(R.string.offline), style = MaterialTheme.typography.labelMedium, color = MpayColors.Warning)
            }
            if (vm.syncing) {
                CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                Spacer(Modifier.width(12.dp))
            } else {
                IconButton({ vm.refresh() }, Modifier.testTag("refresh")) { Icon(Icons.Filled.Refresh, stringResource(R.string.refresh)) }
            }
            IconButton({ vm.go(Screen.Settings) }, Modifier.testTag("settings")) { Icon(Icons.Filled.Settings, stringResource(R.string.settings)) }
        }
        if (cards.isEmpty()) {
            Column(Modifier.fillMaxSize().padding(24.dp), verticalArrangement = Arrangement.Center) {
                EmptyState(MpayIcons.Card, stringResource(R.string.no_cards_title), stringResource(R.string.no_cards_body))
                Spacer(Modifier.height(16.dp))
                Button({ vm.go(Screen.AddCard) }, Modifier.fillMaxWidth().height(52.dp).testTag("add_first")) {
                    Icon(Icons.Filled.Add, null)
                    Spacer(Modifier.width(8.dp))
                    Text(stringResource(R.string.add_card))
                }
            }
            return
        }
        val pager = rememberPagerState(initialPage = cards.indexOfFirst { it.isDefault }.coerceAtLeast(0)) { cards.size }
        val current = cards.getOrNull(pager.currentPage) ?: cards.first()
        Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState())) {
            HorizontalPager(
                pager,
                contentPadding = PaddingValues(horizontal = 28.dp),
                pageSpacing = 12.dp,
                modifier = Modifier.padding(top = 12.dp).testTag("cards_pager"),
            ) { i ->
                CardVisual(cards[i], Modifier.clickable { vm.go(Screen.Card(cards[i].tokenId)) }.testTag("card_$i"))
            }
            if (cards.size > 1) {
                Row(Modifier.fillMaxWidth().padding(top = 10.dp), horizontalArrangement = Arrangement.Center) {
                    repeat(cards.size) { i ->
                        Box(Modifier.padding(3.dp).size(if (i == pager.currentPage) 8.dp else 6.dp).clip(CircleShape)
                            .background(if (i == pager.currentPage) MpayColors.Mint else MpayColors.Outline))
                    }
                }
            }
            Spacer(Modifier.height(18.dp))
            Button(
                { vm.go(Screen.Pay) },
                enabled = cards.any { it.payable },
                modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp).height(56.dp).testTag("pay"),
                shape = RoundedCornerShape(16.dp),
            ) {
                Icon(MpayIcons.Contactless, null)
                Spacer(Modifier.width(10.dp))
                Text(stringResource(R.string.pay), style = MaterialTheme.typography.titleMedium)
            }
            Spacer(Modifier.height(14.dp))
            Row(Modifier.fillMaxWidth().padding(horizontal = 20.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ActionTile(Icons.Filled.Add, stringResource(R.string.add_card), Modifier.weight(1f).testTag("add_card")) { vm.go(Screen.AddCard) }
                ActionTile(MpayIcons.History, stringResource(R.string.history), Modifier.weight(1f).testTag("history")) { vm.go(Screen.History(current.tokenId)) }
                ActionTile(MpayIcons.Card, stringResource(R.string.card_manage), Modifier.weight(1f).testTag("manage")) { vm.go(Screen.Card(current.tokenId)) }
            }
            if (current.onDevice) RecentTxns(vm, current.tokenId, lang)
            Spacer(Modifier.height(24.dp))
        }
    }
}

@Composable
private fun RecentTxns(vm: WalletViewModel, tokenId: String, lang: Lang) {
    LaunchedEffect(tokenId) { if (vm.history[tokenId] == null) vm.loadHistory(tokenId, reset = true) }
    val h = vm.history[tokenId]
    Column(Modifier.padding(horizontal = 20.dp, vertical = 8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            SectionTitle(stringResource(R.string.recent), Modifier.weight(1f))
            TextButton({ vm.go(Screen.History(tokenId)) }) { Text(stringResource(R.string.see_all)) }
        }
        when {
            h == null || (h.loading && h.items.isEmpty()) -> Box(Modifier.fillMaxWidth().padding(16.dp), contentAlignment = Alignment.Center) {
                CircularProgressIndicator(Modifier.size(24.dp), strokeWidth = 2.dp)
            }
            h.items.isEmpty() && h.error != null -> Text(stringResource(h.error), color = MpayColors.TextSecondary)
            h.items.isEmpty() -> Text(stringResource(R.string.no_txns), color = MpayColors.TextSecondary, modifier = Modifier.testTag("no_txns"))
            else -> h.items.take(5).forEach { TxnRow(it, lang) }
        }
    }
}

// ------------------------------------------------------------ karta qo'shish

/** Karta raqami ko'rinishi: 4 tadan guruh (kursor to'g'ri siljiydi). */
private object PanTransformation : VisualTransformation {
    override fun filter(text: AnnotatedString): TransformedText {
        val out = Format.groupPan(text.text)
        return TransformedText(AnnotatedString(out), object : OffsetMapping {
            override fun originalToTransformed(offset: Int) = offset + (offset - 1).coerceAtLeast(0) / 4
            override fun transformedToOriginal(offset: Int) = offset - offset / 5
        })
    }
}

/** Muddat ko'rinishi: `MM/YY`. */
private object ExpiryTransformation : VisualTransformation {
    override fun filter(text: AnnotatedString): TransformedText {
        val t = text.text
        val out = if (t.length > 2) t.take(2) + "/" + t.drop(2) else t
        return TransformedText(AnnotatedString(out), object : OffsetMapping {
            override fun originalToTransformed(offset: Int) = if (offset > 2) offset + 1 else offset
            override fun transformedToOriginal(offset: Int) = if (offset > 2) offset - 1 else offset
        })
    }
}

@Composable
fun AddCardScreen(vm: WalletViewModel) {
    var pan by remember { mutableStateOf("") }
    var exp by remember { mutableStateOf("") }
    val panOk = Format.luhnOk(pan) && pan.length == 16
    val expOk = Format.mmyyToYymm(exp) != null
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.add_card), onBack = { vm.back() })
        Column(Modifier.fillMaxSize().padding(20.dp).verticalScroll(rememberScrollState())) {
            Text(stringResource(R.string.add_card_hint), style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary)
            Spacer(Modifier.height(16.dp))
            OutlinedTextField(
                pan, { pan = it.filter(Char::isDigit).take(16) },
                label = { Text(stringResource(R.string.card_number)) },
                singleLine = true,
                isError = pan.length == 16 && !panOk,
                supportingText = { if (pan.length == 16 && !panOk) Text(stringResource(R.string.err_card_number)) },
                visualTransformation = PanTransformation,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth().testTag("pan"),
            )
            OutlinedTextField(
                exp, { exp = it.filter(Char::isDigit).take(4) },
                label = { Text(stringResource(R.string.card_expiry)) },
                placeholder = { Text("MM/YY") },
                singleLine = true,
                isError = exp.length == 4 && !expOk,
                visualTransformation = ExpiryTransformation,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth().testTag("expiry"),
            )
            Spacer(Modifier.height(12.dp))
            Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).background(MpayColors.Surface).padding(12.dp)) {
                Icon(MpayIcons.Shield, null, tint = MpayColors.Mint, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(10.dp))
                Text(stringResource(R.string.add_card_security), style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary)
            }
            Spacer(Modifier.height(24.dp))
            Button(
                // FPAN ekranda qolmasin: server javob bergach maydonlar tozalanadi.
                { vm.addCard(pan, exp) { pan = ""; exp = "" } },
                enabled = panOk && expOk && !vm.busy,
                modifier = Modifier.fillMaxWidth().height(52.dp).testTag("add_submit"),
            ) {
                if (vm.busy) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) else Text(stringResource(R.string.add_card_submit))
            }
        }
    }
}

@Composable
fun OtpScreen(vm: WalletViewModel, s: Screen.Otp) {
    var code by remember { mutableStateOf("") }
    var wait by remember { mutableIntStateOf(60) }
    LaunchedEffect(wait) { if (wait > 0) { delay(1000); wait-- } }
    Column(Modifier.fillMaxSize()) {
        MpayTopBar(stringResource(R.string.otp_title), onBack = { vm.back() })
        Column(Modifier.fillMaxSize().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(MpayIcons.Shield, null, tint = MpayColors.Mint, modifier = Modifier.size(44.dp))
            Spacer(Modifier.height(12.dp))
            Text(
                s.sentTo?.let { stringResource(R.string.otp_sent_to, it) } ?: stringResource(R.string.otp_sent),
                style = MaterialTheme.typography.bodyLarge, textAlign = TextAlign.Center, modifier = Modifier.testTag("otp_hint"),
            )
            Spacer(Modifier.height(20.dp))
            OutlinedTextField(
                code, { code = it.filter(Char::isDigit).take(6) },
                label = { Text(stringResource(R.string.otp_code)) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth().testTag("otp"),
            )
            Spacer(Modifier.height(16.dp))
            Button({ vm.verifyOtp(s, code) }, enabled = code.length == 6 && !vm.busy, modifier = Modifier.fillMaxWidth().height(52.dp).testTag("otp_verify")) {
                if (vm.busy) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) else Text(stringResource(R.string.confirm))
            }
            TextButton({ vm.resendOtp(s); wait = 60 }, enabled = wait == 0 && !vm.busy, modifier = Modifier.testTag("otp_resend")) {
                Text(if (wait > 0) stringResource(R.string.otp_resend_in, wait) else stringResource(R.string.otp_resend))
            }
        }
    }
}
