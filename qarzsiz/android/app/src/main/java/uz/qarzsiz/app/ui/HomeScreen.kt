package uz.qarzsiz.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.DueDates
import uz.qarzsiz.core.Habits
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.UzDates
import java.time.YearMonth
import java.time.temporal.ChronoUnit

@Composable
fun HomeScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val o by vm.overview.collectAsStateWithLifecycle()
    val today = vm.today()

    ScreenScaffold("Qarzsiz") {
        if (o.activeCount == 0 && o.closedCount == 0) {
            Panel(border = Tok.accent) {
                Text("1-qadam: ro'yxat", style = MaterialTheme.typography.titleMedium, color = Tok.accentText)
                Text(
                    "Hamma qarzingizni yozing — bankdan, nasiyadan, qarindosh va tanishlardan. " +
                        "Ro'yxat qo'rqinchli tuyuladi, lekin aniq raqam noaniqlikdan yengil.",
                    style = MaterialTheme.typography.bodyMedium, color = Tok.ink,
                )
                PrimaryButton("Birinchi qarzni yozish") { nav.go(Route.DebtEdit(null)) }
            }
            SecondaryButton("Yo'l xaritasini o'qish") { nav.go(Route.Guide) }
            Disclaimer()
            return@ScreenScaffold
        }

        if (o.activeCount == 0) {
            Panel(border = Tok.accent) {
                Text("Barcha qarzlar yopildi!", style = MaterialTheme.typography.headlineSmall, color = Tok.accentText)
                Text(
                    "Endi har oy qarzga ketgan pulni zaxira jamg'armaga yo'naltiring: 3–6 oylik xarajat " +
                        "yig'ilsa, keyingi tashvishda qarz olishga hojat qolmaydi.",
                    style = MaterialTheme.typography.bodyMedium, color = Tok.ink,
                )
            }
        } else {
            Panel {
                Muted("Jami qarz (so'mda)")
                BigNumber(MoneyFormat.withCurrency(o.totalUzs, uz.qarzsiz.core.Currency.UZS))
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Tag("A: ${o.countA} ta · ${MoneyFormat.compact(o.categoryATotalUzs)}", Tok.danger)
                    Tag("B: ${o.countB} ta · ${MoneyFormat.compact(o.categoryBTotalUzs)}", Tok.calm)
                }
                ProgressLine(o.overallProgressBp)
                Muted("Ro'yxatga kiritilgandan beri ${MoneyFormat.percent(o.overallProgressBp)} yopildi")
            }
            if (o.monthlyInterestUzs > 0) {
                Panel(border = Tok.danger) {
                    Text("Har oy foizga ketmoqda", style = MaterialTheme.typography.titleSmall, color = Tok.danger)
                    BigNumber(MoneyFormat.withCurrency(o.monthlyInterestUzs, uz.qarzsiz.core.Currency.UZS), Tok.danger)
                    Muted(
                        "Kuniga taxminan ${MoneyFormat.withCurrency(o.dailyInterestUzs, uz.qarzsiz.core.Currency.UZS)}. " +
                            "Shuning uchun A qarzlar birinchi yopiladi.",
                    )
                }
            }
            if (o.missingRates.isNotEmpty()) {
                Panel(border = Tok.warn, onClick = { nav.go(Route.Rates) }) {
                    Text("Valyuta kursi kerak", style = MaterialTheme.typography.titleSmall, color = Tok.warn)
                    Text(
                        "${o.missingRates.joinToString { it.code }} dagi qarzlar jamiga qo'shilmadi. " +
                            "Kursni kiritish uchun bosing.",
                        style = MaterialTheme.typography.bodyMedium, color = Tok.ink,
                    )
                }
            }
        }

        SectionTitle("Yo'l")
        val agreedAll = o.countB == 0 || o.agreedB == o.countB
        StepRow("1. Ro'yxat", "${o.activeCount + o.closedCount} ta qarz yozilgan", true) { nav.tab(Route.Debts) }
        StepRow("2. Tahlil: A va B", "A — ${o.countA}, B — ${o.countB}", state.analysisSeen) { nav.tab(Route.Plan) }
        StepRow(
            "3. B bilan kelishish",
            if (o.countB == 0) "Foizsiz qarz yo'q" else "${o.agreedB} / ${o.countB} kelishildi",
            agreedAll,
        ) { nav.tab(Route.Debts) }
        StepRow(
            "4. Reja 70/30",
            if (state.settings.monthlyIncome > 0) "Oyiga qarzga: ${MoneyFormat.compact(o.budgetUzs)} so'm" else "Daromad kiritilmagan",
            state.settings.monthlyIncome > 0,
        ) { nav.tab(Route.Plan) }

        if (o.activeCount > 0) {
            val r = o.results[state.settings.strategy]
            SectionTitle("Qarzsiz kun")
            Panel(onClick = { nav.tab(Route.Plan) }) {
                when {
                    state.settings.monthlyIncome <= 0 ->
                        Muted("Daromadni kiriting — ilova qarzsiz kun sanasini hisoblaydi.")
                    r == null || !r.finished -> {
                        Text("Hozirgi byudjet bilan qarz yopilmaydi", style = MaterialTheme.typography.titleSmall, color = Tok.warn)
                        Muted("Reja bo'limida sababini va nima qilish mumkinligini ko'ring.")
                    }
                    else -> {
                        BigNumber(UzDates.yearMonth(UzDates.monthOf(r.months, YearMonth.from(today))))
                        Muted("Taxminan ${UzDates.duration(r.months)} · «${state.settings.strategy.label}» usuli bilan")
                    }
                }
                o.debtLoadBp?.let { load ->
                    val c = if (load > 5_000) Tok.danger else Tok.inkMuted
                    Text(
                        "Qarz yuki: majburiy to'lovlar daromadning ${MoneyFormat.percent(load)} i",
                        style = MaterialTheme.typography.bodySmall, color = c,
                    )
                }
            }

            if (!state.reminders.enabled && o.lines.any { it.debt.dueDay != null }) {
                Panel(border = Tok.accent, onClick = { nav.go(Route.Reminders) }) {
                    Text("To'lov kunini eslatib turaymi?", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
                    Muted("To'lovdan bir necha kun oldin va o'sha kuni bildirishnoma. Internetsiz ishlaydi.")
                }
            }

            val upcoming = o.lines.mapNotNull { l ->
                l.debt.dueDay?.let { day -> l to DueDates.next(day, today) }
            }.sortedBy { it.second }.take(3)
            if (upcoming.isNotEmpty()) {
                SectionTitle("Yaqin to'lovlar")
                upcoming.forEach { (l, date) ->
                    val days = ChronoUnit.DAYS.between(today, date)
                    Panel(onClick = { nav.go(Route.DebtDetail(l.debt.id)) }) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text(l.debt.creditor, style = MaterialTheme.typography.titleSmall, color = Tok.ink, modifier = Modifier.weight(1f))
                            Text(
                                if (days == 0L) "bugun" else "$days kundan keyin",
                                style = MaterialTheme.typography.labelMedium,
                                color = if (days <= 3) Tok.warn else Tok.inkMuted,
                            )
                        }
                        Muted("${UzDates.date(date)} · ${MoneyFormat.withCurrency(l.debt.monthlyPayment, l.debt.currency)}")
                    }
                }
            }
        }

        val enabled = state.habits.filter { it.enabled }
        if (enabled.isNotEmpty()) {
            val done = enabled.count { Habits.key(today, it.id) in state.habitDone }
            SectionTitle("Bugungi kun tartibi")
            Panel(onClick = { nav.go(Route.Habits) }) {
                Text("$done / ${enabled.size} bajarildi", style = MaterialTheme.typography.titleSmall, color = Tok.ink)
                ProgressLine(if (enabled.isEmpty()) 0 else done * 10_000 / enabled.size, Tok.calm, "Bugungi odatlar")
                Muted("Diqqat — daromad va sog'liqda. Qarzdan chiqqan odam avval kun tartibini tiklaydi.")
            }
        }
        Disclaimer()
    }
}

@Composable
private fun StepRow(title: String, subtitle: String, done: Boolean, onClick: () -> Unit) {
    Panel(onClick = onClick, border = if (done) Tok.line else Tok.accent) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                if (done) "✓" else "○",
                style = MaterialTheme.typography.titleMedium,
                color = if (done) Tok.calm else Tok.accentText,
                modifier = Modifier.padding(end = 12.dp),
            )
            androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleSmall, color = Tok.ink)
                Muted(subtitle)
            }
        }
    }
}
