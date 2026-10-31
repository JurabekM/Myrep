package uz.qarzsiz.app.ui

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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.role
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Pin

/** Raqamli klaviatura: PIN tizim klaviaturasiga (va uning lug'atiga) tushmaydi. */
@Composable
fun PinPad(
    entered: String,
    maxLength: Int,
    enabled: Boolean,
    onChange: (String) -> Unit,
    dotsCount: Int = maxLength,
) {
    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
        val dotsLabel = t("Kiritilgan raqamlar") + ": ${entered.length}"
        Row(
            horizontalArrangement = Arrangement.spacedBy(14.dp),
            modifier = Modifier.semantics { contentDescription = dotsLabel },
        ) {
            repeat(dotsCount) { i ->
                Box(
                    Modifier.size(14.dp).clip(CircleShape)
                        .background(if (i < entered.length) Tok.accent else Tok.paper)
                        .border(1.5.dp, if (i < entered.length) Tok.accent else Tok.fieldLine, CircleShape),
                )
            }
        }
        val rows = listOf(listOf("1", "2", "3"), listOf("4", "5", "6"), listOf("7", "8", "9"), listOf("", "0", "⌫"))
        val eraseLabel = t("O'chirish")
        rows.forEach { row ->
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                row.forEach { key ->
                    if (key.isEmpty()) {
                        Spacer(Modifier.size(72.dp))
                    } else {
                        val erase = key == "⌫"
                        Box(
                            Modifier.size(72.dp).clip(CircleShape).background(Tok.surface)
                                .border(1.dp, Tok.line, CircleShape)
                                .clickable(enabled = enabled) {
                                    if (erase) onChange(entered.dropLast(1))
                                    else if (entered.length < maxLength) onChange(entered + key)
                                }
                                .semantics {
                                    role = Role.Button
                                    if (erase) contentDescription = eraseLabel
                                },
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(key, style = MaterialTheme.typography.headlineSmall, color = Tok.ink, raw = true)
                        }
                    }
                }
            }
        }
    }
}

/** Ilova qulflanganda: faqat shu ekran. Ma'lumot ko'rinmaydi. */
@Composable
fun LockScreen(vm: AppViewModel) {
    val state by vm.state.collectAsStateWithLifecycle()
    val lock = state.pin ?: return
    val scope = rememberCoroutineScope()
    var entered by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var message by remember { mutableStateOf<String?>(null) }
    var now by remember { mutableLongStateOf(System.currentTimeMillis()) }
    var forgot by remember { mutableStateOf(0) }

    val waitMs = Pin.remainingLockMs(lock, now)
    LaunchedEffect(lock.lockedUntil) {
        while (Pin.remainingLockMs(lock, System.currentTimeMillis()) > 0) {
            now = System.currentTimeMillis()
            delay(1_000)
        }
        now = System.currentTimeMillis()
    }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("Qarzsiz", style = MaterialTheme.typography.headlineMedium, color = Tok.ink)
        Text("PIN-kodni kiriting", style = MaterialTheme.typography.bodyLarge, color = Tok.inkMuted)
        Spacer(Modifier.height(8.dp))
        PinPad(entered, lock.length, enabled = !busy && waitMs == 0L, onChange = { value ->
            entered = value
            message = null
            if (value.length == lock.length) {
                busy = true
                scope.launch {
                    when (val r = vm.unlock(value)) {
                        AppViewModel.PinCheck.Ok -> Unit
                        is AppViewModel.PinCheck.Wrong -> message = "Noto'g'ri PIN. Yana ${r.attemptsLeft} ta urinish, keyin kutish."
                        is AppViewModel.PinCheck.Wait -> message = null
                    }
                    now = System.currentTimeMillis()
                    entered = ""
                    busy = false
                }
            }
        })
        Box(Modifier.height(48.dp), contentAlignment = Alignment.Center) {
            when {
                busy -> CircularProgressIndicator(color = Tok.accent, modifier = Modifier.size(28.dp))
                waitMs > 0 -> Text(
                    "Ko'p xato urinish. ${(waitMs + 999) / 1000} soniyadan keyin qayta urinib ko'ring.",
                    style = MaterialTheme.typography.bodyMedium, color = Tok.warn,
                )
                message != null -> Text(message!!, style = MaterialTheme.typography.bodyMedium, color = Tok.danger)
            }
        }

        when (forgot) {
            0 -> androidx.compose.material3.TextButton(onClick = { forgot = 1 }) {
                Text("PIN-kodni unutdingizmi?", color = Tok.accentText)
            }
            1 -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Notice(
                    "PIN-kodni tiklab bo'lmaydi — u hech qayerda saqlanmaydi. Yagona yo'l: ilovadagi barcha " +
                        "ma'lumotni o'chirish, keyin zaxira nusxadan tiklash (agar bo'lsa).",
                    Tok.warn,
                )
                SecondaryButton("Ma'lumotni o'chirish", color = Tok.danger) { forgot = 2 }
                SecondaryButton("Bekor qilish") { forgot = 0 }
            }
            else -> Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Notice("Barcha qarz, to'lov va sozlamalar butunlay o'chadi. Ishonchingiz komilmi?", Tok.danger)
                PrimaryButton("Ha, hammasini o'chirish") { vm.wipeAll() }
                SecondaryButton("Bekor qilish") { forgot = 0 }
            }
        }
    }
}

/** «Yana → PIN-kod»: o'rnatish, o'zgartirish, o'chirish va qachon so'rash. */
@Composable
fun PinSettingsScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val lock = state.pin
    val scope = rememberCoroutineScope()
    val ctx = androidx.compose.ui.platform.LocalContext.current
    val script = LocalScript.current

    // Bosqichlar: NONE → (VERIFY →) NEW → CONFIRM; VERIFY_REMOVE — o'chirish uchun tekshiruv.
    var step by remember { mutableStateOf(Step.NONE) }
    var entered by remember { mutableStateOf("") }
    var first by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }

    fun reset() { step = Step.NONE; entered = ""; first = ""; message = null; busy = false }

    ScreenScaffold("PIN-kod", onBack = { if (step != Step.NONE) reset() else nav.back() }) {
        if (step == Step.NONE) {
            Muted(
                "PIN-kod ilovani begona ko'zdan himoya qiladi: telefoningiz qo'lma-qo'l o'tganda ham qarzlaringiz " +
                    "ko'rinmaydi. PIN o'zi saqlanmaydi — faqat uning xeshi.",
            )
            if (lock == null) {
                Panel {
                    Text("PIN-kod o'rnatilmagan", style = MaterialTheme.typography.titleSmall, color = Tok.ink)
                    Muted("4–6 raqam. Tug'ilgan yil, 1234 yoki 0000 kabi oson kodni tanlamang.")
                }
                PrimaryButton("PIN-kod o'rnatish") { step = Step.NEW }
            } else {
                Panel {
                    Text("PIN-kod yoqilgan", style = MaterialTheme.typography.titleSmall, color = Tok.calm)
                    Muted("Ilova fonda shuncha vaqt tursa, qaytganda PIN so'raladi:")
                    ChoiceRow(
                        listOf(0, 30, 60, 300), lock.graceSeconds,
                        { when (it) { 0 -> "Darhol"; 30 -> "30 soniya"; 60 -> "1 daqiqa"; else -> "5 daqiqa" } },
                    ) { vm.setPinGrace(it) }
                    if (lock.graceSeconds == 0) {
                        Muted("«Darhol»: fayl tanlash yoki «Yuborish» oynasidan qaytganda ham PIN so'raladi.")
                    }
                }
                SecondaryButton("PIN-kodni o'zgartirish") { step = Step.VERIFY_CHANGE }
                SecondaryButton("PIN-kodni o'chirish", color = Tok.danger) { step = Step.VERIFY_REMOVE }
                Muted("PIN yoqilganda bildirishnomalarda ham qarz nomlari va summalar ko'rsatilmaydi.")
            }
            Notice(
                "PIN-kodni unutsangiz, uni tiklab bo'lmaydi: faqat ma'lumotni o'chirib, zaxira nusxadan tiklash mumkin. " +
                    "Zaxira nusxani vaqti-vaqti bilan saqlab turing.",
                Tok.calm,
            )
            return@ScreenScaffold
        }

        val title = when (step) {
            Step.VERIFY_CHANGE, Step.VERIFY_REMOVE -> "Hozirgi PIN-kodni kiriting"
            Step.NEW -> "Yangi PIN-kod (4–6 raqam)"
            Step.CONFIRM -> "Yangi PIN-kodni qayta kiriting"
            Step.NONE -> ""
        }
        Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(16.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, color = Tok.ink)
            val verifying = step == Step.VERIFY_CHANGE || step == Step.VERIFY_REMOVE
            val maxLen = when {
                verifying -> lock?.length ?: Pin.MAX_LENGTH
                step == Step.CONFIRM -> first.length
                else -> Pin.MAX_LENGTH
            }
            PinPad(entered, maxLen, enabled = !busy, dotsCount = maxLen, onChange = { value ->
                entered = value
                message = null
                if (verifying && lock != null && value.length == lock.length) {
                    busy = true
                    scope.launch {
                        when (val r = vm.checkPin(value)) {
                            AppViewModel.PinCheck.Ok -> {
                                if (step == Step.VERIFY_REMOVE) {
                                    vm.removePin()
                                    ctx.toast("PIN-kod o'chirildi", script)
                                    reset()
                                } else {
                                    step = Step.NEW
                                }
                            }
                            is AppViewModel.PinCheck.Wrong -> message = "Noto'g'ri PIN. Yana ${r.attemptsLeft} ta urinish."
                            is AppViewModel.PinCheck.Wait -> message = "Ko'p xato urinish. ${(r.ms + 999) / 1000} soniya kuting."
                        }
                        entered = ""
                        busy = false
                    }
                } else if (step == Step.CONFIRM && value.length == first.length) {
                    if (value != first) {
                        message = "PIN-kodlar mos kelmadi. Qaytadan boshlang."
                        step = Step.NEW
                        first = ""
                        entered = ""
                    } else {
                        busy = true
                        scope.launch {
                            vm.setPin(value)
                            ctx.toast("PIN-kod saqlandi", script)
                            reset()
                        }
                    }
                }
            })
            if (step == Step.NEW) {
                PrimaryButton("Davom etish", enabled = Pin.isValidFormat(entered)) {
                    if (Pin.isWeak(entered)) {
                        message = "Bu PIN-kod juda oson topiladi. Boshqasini tanlang."
                        entered = ""
                    } else {
                        first = entered
                        entered = ""
                        step = Step.CONFIRM
                    }
                }
            }
            if (busy) CircularProgressIndicator(color = Tok.accent, modifier = Modifier.size(28.dp))
            message?.let { Text(it, style = MaterialTheme.typography.bodyMedium, color = Tok.danger) }
            SecondaryButton("Bekor qilish") { reset() }
        }
    }
}

private enum class Step { NONE, VERIFY_CHANGE, VERIFY_REMOVE, NEW, CONFIRM }
