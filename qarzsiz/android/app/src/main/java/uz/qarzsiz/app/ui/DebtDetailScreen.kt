package uz.qarzsiz.app.ui

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.widget.Toast
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.DebtCategory
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.Scripts
import uz.qarzsiz.core.TalkStatus
import uz.qarzsiz.core.UzDates
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.DateTimeParseException

@Composable
fun DebtDetailScreen(vm: AppViewModel, nav: Nav, id: String) {
    val state by vm.state.collectAsStateWithLifecycle()
    val o by vm.overview.collectAsStateWithLifecycle()
    val d = state.debts.firstOrNull { it.id == id }
    if (d == null) {
        ScreenScaffold("Qarz", onBack = { nav.back() }) { Muted("Qarz topilmadi (o'chirilgan bo'lishi mumkin).") }
        return
    }
    val line = o.lines.firstOrNull { it.debt.id == id }
    val payments = state.payments.filter { it.debtId == id }.sortedByDescending { it.date }
    val catColor = if (d.category == DebtCategory.A) Tok.danger else Tok.calm

    ScreenScaffold(
        d.creditor,
        onBack = { nav.back() },
        actions = {
            IconButton(onClick = { nav.go(Route.DebtEdit(d.id)) }) {
                Icon(Icons.Filled.Edit, contentDescription = "Tahrirlash")
            }
        },
    ) {
        Panel(border = catColor) {
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                Tag(d.category.label, catColor)
                Tag(d.kind.label, Tok.inkMuted)
            }
            Muted("Qoldiq")
            BigNumber(MoneyFormat.withCurrency(d.balance, d.currency), if (d.isClosed) Tok.calm else Tok.accent)
            if (d.startBalance > 0) {
                ProgressLine(d.progressBp, catColor)
                Muted("${MoneyFormat.withCurrency(d.startBalance - d.balance.coerceAtMost(d.startBalance), d.currency)} to'landi · ${MoneyFormat.percent(d.progressBp)}")
            }
            Muted(d.category.hint)
        }

        if (d.isClosed) {
            Notice(
                "Bu qarz yopildi${d.closedOn?.let { " (${it})" } ?: ""}. Uning oylik to'lovi endi bo'shadi — " +
                    "reja uni avtomatik ravishda keyingi qarzga yo'naltiradi.",
                Tok.calm, "Barakalla!",
            )
        }

        Panel {
            if (d.annualRateBp > 0) KeyValue("Yillik foiz", MoneyFormat.percent(d.annualRateBp), Tok.danger)
            KeyValue("Oylik to'lov", if (d.monthlyPayment > 0) MoneyFormat.withCurrency(d.monthlyPayment, d.currency) else "kelishilmagan")
            d.dueDay?.let { KeyValue("To'lov kuni", "har oy $it-kuni") }
            if (d.hasPenalty) KeyValue("Jarima", "kechiksa — bor", Tok.warn)
            if (d.overdue) KeyValue("Holat", "muddati o'tgan", Tok.warn)
            if (line != null) {
                if (line.monthlyInterestUzs > 0) {
                    KeyValue("Oyiga foizga ketadi (taxm.)", MoneyFormat.withCurrency(line.monthlyInterestUzs, Currency.UZS), Tok.danger)
                }
                if (state.settings.monthlyIncome > 0 && line.thisMonthUzs > 0) {
                    KeyValue("Rejaga ko'ra shu oy", MoneyFormat.withCurrency(line.thisMonthUzs, Currency.UZS), Tok.accentText)
                }
                line.payoffMonth?.takeIf { it > 0 }?.let {
                    KeyValue("Taxminiy yopilish", UzDates.yearMonth(UzDates.monthOf(it, YearMonth.from(vm.today()))))
                }
            } else if (!d.isClosed && d.currency != Currency.UZS) {
                Muted("${d.currency.code} kursi kiritilmagan — reja bu qarzni hisobga olmayapti. «Yana → Valyuta kurslari».")
            }
            if (d.note.isNotBlank()) {
                Muted("Izoh")
                Text(d.note, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
            }
        }

        if (!d.isClosed) PaymentForm(vm, d)

        if (d.category == DebtCategory.B && !d.isClosed) TalkSection(vm, d)
        if (d.category == DebtCategory.A && !d.isClosed) RestructureSection(d)

        if (payments.isNotEmpty()) {
            SectionTitle("To'lovlar tarixi")
            payments.forEach { p ->
                var confirm by rememberSaveable(p.id) { mutableStateOf(false) }
                Panel {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
                            Text(MoneyFormat.withCurrency(p.amount, d.currency), style = MaterialTheme.typography.titleSmall, color = Tok.ink)
                            Muted(runCatching { UzDates.date(LocalDate.parse(p.date)) }.getOrDefault(p.date) + (if (p.note.isNotBlank()) " · ${p.note}" else ""))
                        }
                        androidx.compose.material3.TextButton(onClick = { confirm = !confirm }) {
                            Text(if (confirm) "Yo'q" else "Bekor", color = Tok.inkMuted)
                        }
                    }
                    if (confirm) {
                        Muted("Bu to'lov xato yozilganmi? Bekor qilinsa, qoldiq ${MoneyFormat.withCurrency(p.amount, d.currency)} ga ortadi.")
                        SecondaryButton("Ha, to'lovni bekor qilish", color = Tok.danger) { vm.deletePayment(p.id) }
                    }
                }
            }
        }
        Disclaimer()
    }
}

@Composable
private fun PaymentForm(vm: AppViewModel, d: Debt) {
    var open by rememberSaveable(d.id) { mutableStateOf(false) }
    var amount by rememberSaveable(d.id) { mutableStateOf("") }
    var date by rememberSaveable(d.id) { mutableStateOf(vm.today().toString()) }
    var note by rememberSaveable(d.id) { mutableStateOf("") }
    if (!open) {
        PrimaryButton("To'lov yozish") {
            amount = if (d.monthlyPayment > 0) MoneyFormat.amount(minOf(d.monthlyPayment, d.balance)).replace(' ', ' ') else ""
            date = vm.today().toString()
            open = true
        }
        return
    }
    Panel(border = Tok.accent) {
        Text("To'lov yozish", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
        Muted("«To'xtatmang, kam bo'lsa ham bering» — har bir to'lov hisobga olinadi.")
        MoneyInput(amount, { amount = it }, "Summa", suffix = d.currency.symbol)
        val parsedDate = try { LocalDate.parse(date.trim()) } catch (e: DateTimeParseException) { null }
        TextInput(date, { date = it }, "Sana (yyyy-oo-kk)", error = if (parsedDate == null) "Masalan: ${vm.today()}" else null)
        TextInput(note, { note = it }, "Izoh (ixtiyoriy)")
        val minor = MoneyFormat.parse(amount)
        if (minor != null && minor > d.balance) {
            Muted("Qoldiqdan ko'p: faqat ${MoneyFormat.withCurrency(d.balance, d.currency)} yoziladi va qarz yopiladi.")
        }
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            SecondaryButton("Bekor", Modifier.weight(1f)) { open = false }
            PrimaryButton("Yozish", Modifier.weight(1f), enabled = minor != null && minor > 0 && parsedDate != null) {
                vm.addPayment(d.id, minor!!, parsedDate!!, note)
                amount = ""
                note = ""
                open = false
            }
        }
    }
}

@Composable
private fun TalkSection(vm: AppViewModel, d: Debt) {
    val ctx = LocalContext.current
    var status by rememberSaveable(d.id + "s") { mutableStateOf(d.talkStatus) }
    var agreement by rememberSaveable(d.id + "n") { mutableStateOf(d.note) }
    var monthly by rememberSaveable(d.id + "m") {
        mutableStateOf(if (d.monthlyPayment > 0) MoneyFormat.amount(d.monthlyPayment).replace(' ', ' ') else "")
    }
    var start by rememberSaveable(d.id + "st") { mutableStateOf("") }

    SectionTitle("3-qadam: kelishish")
    Panel {
        Muted(
            "Qarz egasiga qo'ng'iroq qiling yoki yozing. Maqsad — qochish emas, aniq tartib kelishish: " +
                "qancha, qachondan, har oy qaysi kuni.",
        )
        Bullets(Scripts.talkTips)
    }
    Panel {
        Text("Taklif matni", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
        MoneyInput(monthly, { monthly = it }, "Har oy qancha bera olasiz", suffix = d.currency.symbol)
        TextInput(start, { start = it }, "Qachondan", hint = "Masalan: dekabrdan. Bo'sh — «keyingi oydan»")
        val m = MoneyFormat.parse(monthly)
        val text = Scripts.personal(
            Scripts.Proposal(
                creditor = d.creditor,
                amountText = MoneyFormat.withCurrency(d.balance, d.currency),
                monthlyText = m?.let { MoneyFormat.withCurrency(it, d.currency) } ?: "[summa]",
                startText = start,
                months = m?.takeIf { it > 0 }?.let { uz.qarzsiz.core.SaveInstead.months(d.balance, 0, it) },
            ),
        )
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
        ShareButtons(ctx, text)
    }
    Panel {
        Text("Natija", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
        ChoiceRow(TalkStatus.entries, status, { it.label }) { status = it }
        TextInput(agreement, { agreement = it }, "Nima kelishildi", singleLine = false, minLines = 2,
            hint = "Masalan: dekabrdan har oy 10-sanada 300 \$")
        PrimaryButton("Saqlash") {
            vm.setTalkStatus(d.id, status, agreement.trim())
            Toast.makeText(ctx, "Saqlandi", Toast.LENGTH_SHORT).show()
        }
        if (status == TalkStatus.AGREED && (MoneyFormat.parse(monthly) ?: 0) > 0 && d.monthlyPayment == 0L) {
            Muted("Kelishilgan oylik summani qarzning «Oylik to'lov» maydoniga ham yozing — reja shunga tayanadi.")
        }
    }
}

@Composable
private fun RestructureSection(d: Debt) {
    val ctx = LocalContext.current
    var open by rememberSaveable(d.id + "r") { mutableStateOf(false) }
    var name by rememberSaveable(d.id + "rn") { mutableStateOf("") }
    var contract by rememberSaveable(d.id + "rc") { mutableStateOf("") }
    var reason by rememberSaveable(d.id + "rr") { mutableStateOf("") }
    var monthly by rememberSaveable(d.id + "rm") { mutableStateOf("") }

    SectionTitle("To'lay olmayapsizmi?")
    Panel {
        Muted(
            "To'lovni jimgina to'xtatmang — jarima va kredit tarixi buziladi. Muddat kelmasdan bankka yozma " +
                "murojaat qiling: ko'p banklar ariza asosida muddatni uzaytirish yoki imtiyozli davrni ko'rib chiqadi. " +
                "Bu kafolat emas, lekin urinib ko'rishga arziydi.",
        )
        if (!open) {
            SecondaryButton("Bank uchun ariza namunasi") { open = true }
        } else {
            TextInput(name, { name = it }, "F.I.Sh.")
            TextInput(contract, { contract = it }, "Shartnoma", hint = "Masalan: 2024-yil 12-martdagi 123-sonli kredit shartnomasi")
            TextInput(reason, { reason = it }, "Sabab", hint = "Masalan: ishdan bo'shaganim, kasallik")
            MoneyInput(monthly, { monthly = it }, "Oyiga qancha to'lay olasiz", suffix = d.currency.symbol)
            val m = MoneyFormat.parse(monthly)
            val text = Scripts.restructuring(
                bank = d.creditor,
                fullName = name,
                contractText = contract,
                reason = reason,
                monthlyText = m?.let { MoneyFormat.withCurrency(it, d.currency) } ?: "[summa]",
            )
            Text(text, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
            ShareButtons(ctx, text)
        }
    }
}

@Composable
fun ShareButtons(ctx: Context, text: String) {
    Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        SecondaryButton("Nusxa olish", Modifier.weight(1f)) {
            val cm = ctx.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            cm.setPrimaryClip(ClipData.newPlainText("Qarzsiz", text))
            Toast.makeText(ctx, "Nusxa olindi", Toast.LENGTH_SHORT).show()
        }
        SecondaryButton("Yuborish", Modifier.weight(1f)) {
            val send = Intent(Intent.ACTION_SEND).apply {
                type = "text/plain"
                putExtra(Intent.EXTRA_TEXT, text)
            }
            ctx.startActivity(Intent.createChooser(send, "Yuborish"))
        }
    }
}
