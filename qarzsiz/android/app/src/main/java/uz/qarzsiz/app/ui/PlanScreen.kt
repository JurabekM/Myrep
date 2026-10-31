package uz.qarzsiz.app.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Slider
import androidx.compose.material3.SliderDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Budget
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.Strategy
import uz.qarzsiz.core.UzDates
import java.time.YearMonth

@Composable
fun PlanScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val o by vm.overview.collectAsStateWithLifecycle()
    val s = state.settings
    val now = YearMonth.from(vm.today())

    LaunchedEffect(o.activeCount) { if (o.activeCount > 0) vm.markAnalysisSeen() }

    var income by rememberSaveable { mutableStateOf(s.monthlyIncome.takeIf { it > 0 }?.let(::plain) ?: "") }
    var living by rememberSaveable { mutableStateOf(s.livingMinimum.takeIf { it > 0 }?.let(::plain) ?: "") }

    fun uzs(v: Long) = MoneyFormat.withCurrency(v, Currency.UZS)

    ScreenScaffold("Reja 70/30") {
        Panel {
            Text("Daromad va yashash", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
            MoneyInput(income, {
                income = it
                MoneyFormat.parse(it)?.let { v -> vm.updateSettings(vm.state.value.settings.copy(monthlyIncome = v)) }
                if (it.isBlank()) vm.updateSettings(vm.state.value.settings.copy(monthlyIncome = 0))
            }, "Oylik daromad", hint = "Barcha manbalardan, qo'lga tegadigan")
            MoneyInput(living, {
                living = it
                MoneyFormat.parse(it)?.let { v -> vm.updateSettings(vm.state.value.settings.copy(livingMinimum = v)) }
                if (it.isBlank()) vm.updateSettings(vm.state.value.settings.copy(livingMinimum = 0))
            }, "Minimal yashash xarajati", hint = "Ovqat, kommunal, yo'l, dori")

            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Text("Qarzga ulush", style = MaterialTheme.typography.bodyMedium, color = Tok.ink, modifier = Modifier.weight(1f))
                Text(MoneyFormat.percent(s.debtShareBp), style = MaterialTheme.typography.titleMedium, color = Tok.accentText)
            }
            Slider(
                value = s.debtShareBp / 100f,
                onValueChange = { v ->
                    val bp = (Math.round(v / 5f) * 5 * 100).coerceIn(Budget.MIN_SHARE_BP, Budget.MAX_SHARE_BP)
                    if (bp != vm.state.value.settings.debtShareBp) vm.updateSettings(vm.state.value.settings.copy(debtShareBp = bp))
                },
                valueRange = (Budget.MIN_SHARE_BP / 100f)..(Budget.MAX_SHARE_BP / 100f),
                steps = (Budget.MAX_SHARE_BP - Budget.MIN_SHARE_BP) / 500 - 1,
                colors = SliderDefaults.colors(thumbColor = Tok.accent, activeTrackColor = Tok.accent, inactiveTrackColor = Tok.line),
                modifier = Modifier.semantics { contentDescription = "Qarzga ulush, foizda" },
            )
            Muted("Standart — 70%. 100% emas: ovqat, yo'l va daromad manbasi uchun pul qolishi shart.")
            if (s.monthlyIncome > 0) {
                KeyValue("Oyiga qarzga", uzs(o.budgetUzs), Tok.accentText)
                KeyValue("Yashash va ishga", uzs(s.monthlyIncome - o.budgetUzs))
            }
        }

        if (o.livingAtRisk) {
            Notice(
                "Bu ulushda yashash xarajatiga yetmaydi. Xavfsiz ulush — ${MoneyFormat.percent(o.safeShareBp)}. " +
                    "Och qolgan oila bir oydan keyin yana qarz oladi.",
                Tok.warn, "Ehtiyot bo'ling",
            )
            if (o.safeShareBp >= Budget.MIN_SHARE_BP) {
                SecondaryButton("Xavfsiz ulushni qo'yish (${MoneyFormat.percent(o.safeShareBp - o.safeShareBp % 500)})") {
                    vm.updateSettings(s.copy(debtShareBp = (o.safeShareBp - o.safeShareBp % 500).coerceAtLeast(Budget.MIN_SHARE_BP)))
                }
            }
        }

        Panel {
            Text("Ortgan pul qayerga?", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
            Muted("Avval hamma qarzning majburiy to'lovi — to'xtatmasdan. Keyin ortgan pul:")
            val choices = listOf(Strategy.AVALANCHE, Strategy.SNOWBALL, Strategy.PRO_RATA)
            ChoiceRow(choices, s.strategy, { it.label }) { vm.updateSettings(s.copy(strategy = it)) }
            Muted(s.strategy.hint)
        }

        if (o.activeCount == 0) {
            Muted("Qarz yozilmagan. Avval «Qarzlar» bo'limida ro'yxat tuzing.")
            PrimaryButton("Qarz qo'shish") { nav.go(Route.DebtEdit(null)) }
            return@ScreenScaffold
        }
        if (s.monthlyIncome <= 0) {
            Notice("Oylik daromadni kiriting — shunda shu oy kimga qancha berish va qarzsiz kun hisoblanadi.")
            return@ScreenScaffold
        }

        val r = o.results.getValue(s.strategy)
        if (o.missingRates.isNotEmpty()) {
            Notice("${o.missingRates.joinToString { it.code }} kursi kiritilmagan — bu qarzlar rejada yo'q.", Tok.warn)
        }
        if (r.shortfall) {
            Notice(
                "Majburiy to'lovlar jami ${uzs(o.monthlyMinimumUzs)}, qarzga ajratilgan pul — ${uzs(o.budgetUzs)}. " +
                    "Farq: ${uzs(o.monthlyMinimumUzs - o.budgetUzs)}. Pul hamma qarzga mutanosib bo'lindi.\n\n" +
                    "Nima qilish mumkin: B qarz egalari bilan oylik summani kamaytirib kelishing; bankka muddatni " +
                    "uzaytirish arizasini bering (qarz kartochkasida namuna bor); qo'shimcha daromad va keraksiz " +
                    "buyumni sotishni o'ylang.",
                Tok.danger, "Byudjet majburiy to'lovlarga yetmaydi",
            )
        }

        SectionTitle("Shu oy kimga qancha")
        Panel {
            o.lines.forEach { l ->
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
                        Text(l.debt.creditor, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
                        val extra = l.thisMonthUzs - minOf(l.minPaymentUzs, l.thisMonthUzs)
                        Muted(
                            buildString {
                                append(if (l.debt.category == uz.qarzsiz.core.DebtCategory.A) "A" else "B")
                                if (l.debt.annualRateBp > 0) append(" · ${MoneyFormat.percent(l.debt.annualRateBp)}")
                                if (extra > 0) append(" · +${MoneyFormat.compact(extra)} qo'shimcha")
                            },
                        )
                    }
                    Text(
                        if (l.thisMonthUzs == 0L) "keyinroq" else uzs(l.thisMonthUzs),
                        style = MaterialTheme.typography.titleSmall,
                        color = if (l.thisMonthUzs > l.minPaymentUzs) Tok.accentText else Tok.ink,
                    )
                }
            }
            if (o.lines.any { it.thisMonthUzs == 0L }) {
                Muted("«keyinroq» — oylik to'lovi kelishilmagan qarz: unga navbat oldingi qarzlar yopilgach keladi. Egasi bilan shu tartibni kelishing.")
            }
            Muted("Bank to'lov jadvalidan kam to'lamang: bu yerda ko'rsatilgan summa majburiy to'lovdan kam bo'lsa, byudjet yetmayapti.")
        }

        SectionTitle("Qarzsiz kun")
        Panel(border = if (r.finished) Tok.accent else Tok.warn) {
            if (r.finished) {
                BigNumber(UzDates.yearMonth(UzDates.monthOf(r.months, now)))
                Muted("${UzDates.duration(r.months)} · jami foiz taxminan ${uzs(r.totalInterest)}")
            } else {
                Text("Bu byudjet bilan qarz yopilmaydi", style = MaterialTheme.typography.titleSmall, color = Tok.warn)
                Muted(
                    "Foiz har oy to'lovdan tezroq o'smoqda yoki ba'zi qarzlarga hech pul yetmayapti. " +
                        "Ulushni oshiring, daromadni ko'paytiring yoki kreditorlar bilan qayta kelishing.",
                )
            }
        }

        SectionTitle("Usullarni taqqoslash")
        Panel {
            val best = o.results.filterValues { it.finished }.minByOrNull { it.value.totalInterest }?.key
            Strategy.entries.forEach { st ->
                val res = o.results.getValue(st)
                androidx.compose.foundation.layout.Column {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text(
                            st.label + if (st == best) " ★" else "",
                            style = MaterialTheme.typography.titleSmall,
                            color = if (st == s.strategy) Tok.accentText else Tok.ink,
                            modifier = Modifier.weight(1f),
                        )
                        Text(
                            if (res.finished) UzDates.yearMonth(UzDates.monthOf(res.months, now)) else "yopilmaydi",
                            style = MaterialTheme.typography.bodyMedium,
                            color = if (res.finished) Tok.ink else Tok.warn,
                        )
                    }
                    Muted(
                        if (res.finished) "${UzDates.duration(res.months)} · foiz ${uzs(res.totalInterest)}"
                        else "${UzDates.duration(res.months)} dan keyin ham qarz qoladi",
                    )
                }
            }
            Muted(
                "★ — eng kam foiz. «Teng ulush» — pulni hamma qarzga bo'lib berish; tushunarli, lekin foizli qarz sekin " +
                    "yopilgani uchun odatda qimmatroq. «Faqat majburiy» — hech narsa o'zgartirmasangiz nima bo'lishi.",
            )
        }
        Disclaimer()
    }
}

private fun plain(minor: Long): String = MoneyFormat.amount(minor).replace(' ', ' ')
