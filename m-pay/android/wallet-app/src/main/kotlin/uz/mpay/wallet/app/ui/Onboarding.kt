package uz.mpay.wallet.app.ui

import androidx.compose.foundation.background
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import uz.mpay.wallet.app.Lang
import uz.mpay.wallet.app.PinPolicy
import uz.mpay.wallet.app.R

private enum class Step { WELCOME, LANG, PIN, CONFIRM, BIOMETRIC, NOTIFY }

/**
 * Birinchi ishga tushirish: tanishuv → til → PIN (ikki marta) → biometriya → bildirishnomalar.
 * `onLang` — til tanlandi (Activity qayta yaratiladi, qadam saqlanadi).
 */
@Composable
fun Onboarding(
    langChosen: Boolean,
    currentLang: Lang,
    biometricAvailable: Boolean,
    pinPolicy: PinPolicy,
    onLang: (Lang) -> Unit,
    onPin: (String) -> Unit,
    onBiometric: (Boolean) -> Unit,
    onNotifications: (onResult: () -> Unit) -> Unit,
    onFinish: () -> Unit,
) {
    var step by rememberSaveable { mutableStateOf(if (langChosen) Step.PIN else Step.WELCOME) }
    var first by rememberSaveable { mutableStateOf("") }
    Box(Modifier.fillMaxSize().background(MpayColors.Background).padding(24.dp)) {
        when (step) {
            Step.WELCOME -> Welcome { step = Step.LANG }
            Step.LANG -> LangStep(currentLang) { l -> onLang(l); step = Step.PIN }
            Step.PIN -> PinEntry(
                title = stringResource(R.string.pin_create_title),
                subtitle = stringResource(R.string.pin_create_sub),
                validate = { if (pinPolicy.valid(it)) null else R.string.pin_too_simple },
            ) { first = it; step = Step.CONFIRM }
            Step.CONFIRM -> PinEntry(
                title = stringResource(R.string.pin_confirm_title),
                subtitle = stringResource(R.string.pin_confirm_sub),
                validate = { if (it == first) null else R.string.pin_mismatch },
                onMismatchReset = { first = ""; step = Step.PIN },
            ) {
                onPin(it)
                first = ""
                step = if (biometricAvailable) Step.BIOMETRIC else Step.NOTIFY
            }
            Step.BIOMETRIC -> Choice(
                icon = MpayIcons.Fingerprint,
                title = stringResource(R.string.bio_title),
                body = stringResource(R.string.bio_body),
                yes = stringResource(R.string.bio_enable),
                no = stringResource(R.string.not_now),
                onYes = { onBiometric(true); step = Step.NOTIFY },
                onNo = { onBiometric(false); step = Step.NOTIFY },
            )
            Step.NOTIFY -> Choice(
                icon = Icons.Filled.Notifications,
                title = stringResource(R.string.notify_title),
                body = stringResource(R.string.notify_body),
                yes = stringResource(R.string.notify_enable),
                no = stringResource(R.string.not_now),
                onYes = { onNotifications { onFinish() } },
                onNo = onFinish,
            )
        }
    }
}

@Composable
private fun Welcome(onNext: () -> Unit) {
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()), horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(Modifier.height(48.dp))
        Box(Modifier.size(96.dp).clip(RoundedCornerShape(28.dp)).background(MpayColors.CardTop), contentAlignment = Alignment.Center) {
            Icon(MpayIcons.Contactless, null, tint = MpayColors.TextPrimary, modifier = Modifier.size(52.dp))
        }
        Spacer(Modifier.height(20.dp))
        Text("M-Pay", style = MaterialTheme.typography.headlineMedium, color = MpayColors.Mint)
        Text(stringResource(R.string.welcome_tagline), style = MaterialTheme.typography.bodyLarge, color = MpayColors.TextSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(32.dp))
        Feature(MpayIcons.Contactless, stringResource(R.string.welcome_f1_title), stringResource(R.string.welcome_f1_body))
        Feature(MpayIcons.Shield, stringResource(R.string.welcome_f2_title), stringResource(R.string.welcome_f2_body))
        Feature(MpayIcons.Card, stringResource(R.string.welcome_f3_title), stringResource(R.string.welcome_f3_body))
        Spacer(Modifier.height(32.dp))
        Button(onNext, Modifier.fillMaxWidth().height(52.dp).testTag("welcome_next")) { Text(stringResource(R.string.start)) }
        Spacer(Modifier.height(8.dp))
        Text(stringResource(R.string.sandbox_note), style = MaterialTheme.typography.labelMedium, color = MpayColors.TextSecondary, textAlign = TextAlign.Center)
    }
}

@Composable
private fun Feature(icon: ImageVector, title: String, body: String) {
    Row(Modifier.fillMaxWidth().padding(vertical = 8.dp), verticalAlignment = Alignment.Top) {
        Box(Modifier.size(40.dp).clip(CircleShape).background(MpayColors.Surface), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = MpayColors.Mint, modifier = Modifier.size(22.dp))
        }
        Spacer(Modifier.width(14.dp))
        Column {
            Text(title, style = MaterialTheme.typography.titleMedium)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary)
        }
    }
}

/** Til tanlash (onboarding va sozlamalarda). */
@Composable
fun LangOptions(current: Lang, onPick: (Lang) -> Unit) {
    val names = mapOf(Lang.UZ to "O'zbekcha", Lang.RU to "Русский", Lang.EN to "English")
    Column {
        Lang.entries.forEach { l ->
            Row(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(12.dp)).clickable { onPick(l) }.padding(vertical = 6.dp).testTag("lang_${l.tag}"),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = l == current, onClick = { onPick(l) })
                Text(names.getValue(l), style = MaterialTheme.typography.bodyLarge)
            }
        }
    }
}

@Composable
private fun LangStep(current: Lang, onPick: (Lang) -> Unit) {
    var sel by remember { mutableStateOf(current) }
    Column(Modifier.fillMaxSize()) {
        Spacer(Modifier.height(48.dp))
        Icon(MpayIcons.Globe, null, tint = MpayColors.Mint, modifier = Modifier.size(40.dp))
        Spacer(Modifier.height(16.dp))
        Text(stringResource(R.string.lang_title), style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(16.dp))
        LangOptions(sel) { sel = it }
        Spacer(Modifier.weight(1f))
        Button({ onPick(sel) }, Modifier.fillMaxWidth().height(52.dp).testTag("lang_next")) { Text(stringResource(R.string.next)) }
    }
}

/**
 * PIN kiritish ekrani. `validate` — xato matni resursi yoki `null`. Xatoda nuqtalar qizaradi va tozalanadi.
 */
@Composable
fun PinEntry(
    title: String,
    subtitle: String,
    validate: (String) -> Int?,
    error: String? = null,
    enabled: Boolean = true,
    onMismatchReset: (() -> Unit)? = null,
    extra: (@Composable () -> Unit)? = null,
    onComplete: (String) -> Unit,
) {
    var pin by remember { mutableStateOf("") }
    var err by remember { mutableStateOf<Int?>(null) }
    var shake by remember { mutableStateOf(false) }
    LaunchedEffect(shake) {
        if (shake) {
            delay(700)
            pin = ""
            shake = false
            if (onMismatchReset != null && err == R.string.pin_mismatch) onMismatchReset()
        }
    }
    Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(Modifier.height(40.dp))
        Icon(MpayIcons.Shield, null, tint = MpayColors.Mint, modifier = Modifier.size(40.dp))
        Spacer(Modifier.height(16.dp))
        Text(title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center, modifier = Modifier.testTag("pin_title"))
        Spacer(Modifier.height(6.dp))
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(28.dp))
        PinDots(pin.length, error = shake)
        Spacer(Modifier.height(12.dp))
        val msg = error ?: err?.let { stringResource(it) }
        Text(msg ?: "", color = MpayColors.Danger, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center, modifier = Modifier.height(40.dp).testTag("pin_error"))
        Spacer(Modifier.weight(1f))
        PinPad(
            onDigit = { d ->
                if (!enabled || shake || pin.length >= PinPolicy.LENGTH) return@PinPad
                pin += d
                if (pin.length == PinPolicy.LENGTH) {
                    val e = validate(pin)
                    if (e == null) {
                        err = null
                        val p = pin
                        pin = ""
                        onComplete(p)
                    } else {
                        err = e
                        shake = true
                    }
                }
            },
            onDelete = { if (!shake) pin = pin.dropLast(1) },
            extra = extra,
        )
        Spacer(Modifier.height(16.dp))
    }
}

@Composable
private fun Choice(icon: ImageVector, title: String, body: String, yes: String, no: String, onYes: () -> Unit, onNo: () -> Unit) {
    Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
        Spacer(Modifier.height(72.dp))
        Box(Modifier.size(88.dp).clip(CircleShape).background(MpayColors.Surface), contentAlignment = Alignment.Center) {
            Icon(icon, null, tint = MpayColors.Mint, modifier = Modifier.size(44.dp))
        }
        Spacer(Modifier.height(24.dp))
        Text(title, style = MaterialTheme.typography.titleLarge, textAlign = TextAlign.Center)
        Spacer(Modifier.height(8.dp))
        Text(body, style = MaterialTheme.typography.bodyMedium, color = MpayColors.TextSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.weight(1f))
        Button(onYes, Modifier.fillMaxWidth().height(52.dp).testTag("choice_yes")) {
            Icon(Icons.Filled.CheckCircle, null, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(8.dp))
            Text(yes)
        }
        TextButton(onNo, Modifier.fillMaxWidth().testTag("choice_no")) { Text(no) }
    }
}
