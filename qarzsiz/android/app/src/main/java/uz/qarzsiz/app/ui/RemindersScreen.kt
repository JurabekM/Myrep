package uz.qarzsiz.app.ui

import android.Manifest
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.app.reminders.ReminderNotifier

/** To'lov kuni eslatmalari: yoqish (bildirishnoma ruxsati bilan), necha kun oldin, soat, sinov. */
@Composable
fun RemindersScreen(vm: AppViewModel, nav: Nav) {
    val ctx = LocalContext.current
    val script = LocalScript.current
    val state by vm.state.collectAsStateWithLifecycle()
    val r = state.reminders
    var denied by remember { mutableStateOf(false) }

    val askPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        denied = !granted
        if (granted) vm.setReminders(vm.state.value.reminders.copy(enabled = true))
    }

    fun enable(on: Boolean) {
        if (!on) {
            vm.setReminders(r.copy(enabled = false))
        } else if (Build.VERSION.SDK_INT >= 33 && !ReminderNotifier.canPost(ctx)) {
            askPermission.launch(Manifest.permission.POST_NOTIFICATIONS)
        } else {
            denied = false
            vm.setReminders(r.copy(enabled = true))
        }
    }

    val withDay = state.debts.filter { !it.isClosed && it.dueDay != null }
    val withoutDay = state.debts.filter { !it.isClosed && it.dueDay == null }

    ScreenScaffold("To'lov eslatmalari", onBack = { nav.back() }) {
        Muted(
            "Muddatni o'tkazib yubormaslik — jarima va kredit tarixini saqlashning eng oson yo'li. " +
                "Eslatma telefonning o'zida hisoblanadi, internet kerak emas.",
        )
        Panel {
            SwitchRow("Eslatmalarni yoqish", r.enabled) { enable(it) }
            if (r.enabled) {
                Muted("Necha kun oldin eslatsin (to'lov kunining o'zida ham eslatiladi)")
                ChoiceRow(listOf(1, 2, 3, 5), r.daysBefore, { "$it kun" }) { vm.setReminders(r.copy(daysBefore = it)) }
                Muted("Soat nechada")
                ChoiceRow(listOf(8, 9, 12, 19), r.hour, { "$it:00" }) { vm.setReminders(r.copy(hour = it)) }
            }
        }
        if (denied) {
            Notice(
                "Bildirishnomaga ruxsat berilmadi. Telefon sozlamalari → Ilovalar → Qarzsiz → Bildirishnomalar " +
                    "bo'limidan yoqishingiz mumkin.",
                Tok.warn,
            )
        }
        if (r.enabled) {
            SecondaryButton("Sinab ko'rish") {
                val shown = ReminderNotifier.postDue(ctx, vm.state.value, vm.today(), force = true)
                if (shown == 0) denied = true else ctx.toast("Bildirishnoma yuborildi", script)
            }
        }

        SectionTitle("Qaysi qarzlar")
        if (withDay.isEmpty()) {
            Muted("To'lov kuni kiritilgan qarz yo'q. Qarzni tahrirlab, «To'lov kuni» maydonini to'ldiring.")
        } else {
            Panel {
                withDay.sortedBy { it.dueDay }.forEach { d ->
                    KeyValue(d.creditor, "har oy ${d.dueDay}-kuni")
                }
            }
        }
        if (withoutDay.isNotEmpty()) {
            Panel(onClick = { nav.tab(Route.Debts) }) {
                Text("To'lov kuni yo'q: ${withoutDay.size} ta", style = MaterialTheme.typography.titleSmall, color = Tok.warn)
                Muted(withoutDay.joinToString { it.creditor } + " — ularga eslatma chiqmaydi.")
            }
        }
        Muted("Qulflangan ekranda qarz tafsiloti ko'rinmaydi — faqat «To'lov eslatmasi».")
        Muted("Shu muddatga to'lov yozib qo'ysangiz, eslatma qayta chiqmaydi.")
    }
}
