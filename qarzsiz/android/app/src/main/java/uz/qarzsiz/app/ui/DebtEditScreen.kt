package uz.qarzsiz.app.ui

import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.selection.toggleable
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.unit.dp
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.DebtKind
import uz.qarzsiz.core.MoneyFormat

@Composable
fun DebtEditScreen(vm: AppViewModel, nav: Nav, id: String?) {
    val existing = id?.let { did -> vm.state.value.debts.firstOrNull { it.id == did } }
    val key = id ?: "new"
    var creditor by rememberSaveable(key) { mutableStateOf(existing?.creditor ?: "") }
    var kind by rememberSaveable(key) { mutableStateOf(existing?.kind ?: DebtKind.BANK_CREDIT) }
    var currency by rememberSaveable(key) { mutableStateOf(existing?.currency ?: Currency.UZS) }
    var balance by rememberSaveable(key) { mutableStateOf(existing?.balance?.let(MoneyFormat::amount)?.replace(' ', ' ') ?: "") }
    var monthlyRate by rememberSaveable(key) { mutableStateOf(false) }
    var rate by rememberSaveable(key) {
        mutableStateOf(existing?.annualRateBp?.takeIf { it > 0 }?.let { MoneyFormat.percent(it).removeSuffix("%") } ?: "")
    }
    var payment by rememberSaveable(key) {
        mutableStateOf(existing?.monthlyPayment?.takeIf { it > 0 }?.let(MoneyFormat::amount)?.replace(' ', ' ') ?: "")
    }
    var dueDay by rememberSaveable(key) { mutableStateOf(existing?.dueDay?.toString() ?: "") }
    var penalty by rememberSaveable(key) { mutableStateOf(existing?.hasPenalty ?: false) }
    var overdue by rememberSaveable(key) { mutableStateOf(existing?.overdue ?: false) }
    var note by rememberSaveable(key) { mutableStateOf(existing?.note ?: "") }
    var confirmDelete by rememberSaveable(key) { mutableStateOf(false) }
    var tried by rememberSaveable(key) { mutableStateOf(false) }

    val balanceMinor = MoneyFormat.parse(balance)
    val rateInput = if (rate.isBlank()) 0 else MoneyFormat.parsePercentBp(rate)
    val rateBp = rateInput?.let { if (monthlyRate) it * 12 else it }
    val paymentMinor = if (payment.isBlank()) 0L else MoneyFormat.parse(payment)
    val dueDayValue = dueDay.trim().takeIf { it.isNotEmpty() }?.toIntOrNull()
    val dueDayOk = dueDay.isBlank() || (dueDayValue != null && dueDayValue in 1..31)
    val valid = creditor.isNotBlank() && balanceMinor != null && rateBp != null && paymentMinor != null && dueDayOk

    ScreenScaffold(if (existing == null) "Yangi qarz" else "Qarzni tahrirlash", onBack = { nav.back() }) {
        TextInput(
            creditor, { creditor = it }, "Kimdan yoki qayerdan",
            hint = "Masalan: Aziz aka, Xalq banki, Uzum Nasiya",
            error = if (tried && creditor.isBlank()) "Nomini yozing" else null,
        )
        Muted("Turi")
        ChoiceRow(DebtKind.entries, kind, { it.label }) { kind = it }
        Muted("Valyuta")
        // To'lovlar qarz valyutasida yozilgan: valyutani almashtirish tarixni buzadi.
        val hasPayments = existing != null && vm.state.value.payments.any { it.debtId == existing.id }
        if (hasPayments) {
            Text(currency.code, color = Tok.ink)
            Muted("To'lovlar yozilgani uchun valyutani o'zgartirib bo'lmaydi.")
        } else {
            ChoiceRow(Currency.entries, currency, { it.code }) { currency = it }
        }
        MoneyInput(balance, { balance = it }, "Hozirgi qoldiq", suffix = currency.symbol, required = tried,
            hint = "Bankdan bo'lsa — ilova yoki chekdagi qolgan asosiy qarz")

        Muted("Foiz yoki ustama")
        ChoiceRow(listOf(false, true), monthlyRate, { if (it) "Oyiga %" else "Yiliga %" }) { monthlyRate = it }
        TextInput(
            rate, { rate = it.filter { ch -> ch.isDigit() || ch == ',' || ch == '.' } },
            if (monthlyRate) "Oylik foiz, %" else "Yillik foiz, %",
            hint = when {
                rateBp != null && monthlyRate && rateBp > 0 -> "= yiliga ${MoneyFormat.percent(rateBp)}"
                else -> "Foizsiz bo'lsa — bo'sh qoldiring"
            },
            error = if (rate.isNotBlank() && rateInput == null) "Masalan: 24 yoki 24,5" else null,
        )
        if (kind.usuallyInterest && (rateBp ?: 0) == 0 && !penalty) {
            Notice(
                "Bu turdagi qarz odatda foizli yoki ustamali bo'ladi. Shartnomadagi yillik foizni kiriting. " +
                    "Bilmasangiz: «Nasiya» bo'limida naqd narx va oylik to'lovdan yashirin foizni hisoblang.",
            )
        }
        MoneyInput(payment, { payment = it }, "Oylik to'lov (majburiy yoki kelishilgan)", suffix = currency.symbol,
            hint = "Tanishdan bo'lsa va hali kelishilmagan — bo'sh qoldiring")
        TextInput(
            dueDay, { dueDay = it.filter(Char::isDigit).take(2) }, "To'lov kuni (oyning 1–31 kuni)",
            error = if (!dueDayOk) "1 dan 31 gacha" else null,
        )
        SwitchRow("Kechiksa jarima (penya) bor", penalty) { penalty = it }
        SwitchRow("Hozir muddati o'tgan to'lov bor", overdue) { overdue = it }
        TextInput(note, { note = it }, "Izoh", singleLine = false, minLines = 2,
            hint = "Shartnoma raqami, kelishuv, kimning nomida va h.k.")

        PrimaryButton("Saqlash") {
            tried = true
            if (!valid) return@PrimaryButton
            val bal = balanceMinor!!
            val today = vm.today().toString()
            val debt = Debt(
                id = existing?.id ?: vm.newId(),
                creditor = creditor.trim(),
                kind = kind,
                currency = currency,
                balance = bal,
                startBalance = maxOf(existing?.startBalance ?: bal, bal),
                annualRateBp = rateBp!!,
                monthlyPayment = paymentMinor!!,
                dueDay = dueDayValue,
                hasPenalty = penalty,
                overdue = overdue,
                talkStatus = existing?.talkStatus ?: uz.qarzsiz.core.TalkStatus.NOT_TALKED,
                note = note.trim(),
                createdOn = existing?.createdOn ?: today,
                closedOn = if (bal == 0L) existing?.closedOn ?: today else null,
            )
            vm.upsertDebt(debt)
            if (existing == null) nav.replace(Route.DebtDetail(debt.id)) else nav.back()
        }
        if (tried && !valid) Notice("Qizil belgilangan maydonlarni to'g'rilang.", Tok.danger)

        if (existing != null) {
            if (!confirmDelete) {
                SecondaryButton("Qarzni o'chirish", color = Tok.danger) { confirmDelete = true }
            } else {
                Notice(
                    "«${existing.creditor}» va uning barcha to'lov yozuvlari o'chadi. Qarz yopilgan bo'lsa, " +
                        "o'chirmang — yopilganlar ro'yxatida qolgani yaxshi: bu sizning yutug'ingiz.",
                    Tok.danger,
                )
                PrimaryButton("Ha, o'chirish") {
                    vm.deleteDebt(existing.id)
                    nav.tab(Route.Debts)
                }
                SecondaryButton("Bekor qilish") { confirmDelete = false }
            }
        }
    }
}

@Composable
fun SwitchRow(label: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    // Butun qator bosiladi (katta nishon, ekran o'quvchi uchun bitta «kalit» elementi).
    Row(
        Modifier.fillMaxWidth()
            .toggleable(value = checked, role = Role.Switch, onValueChange = onChange)
            .padding(vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text(label, style = MaterialTheme.typography.bodyMedium, color = Tok.ink, modifier = Modifier.weight(1f))
        Switch(
            checked = checked,
            onCheckedChange = null,
            colors = SwitchDefaults.colors(
                checkedThumbColor = Tok.accentInk,
                checkedTrackColor = Tok.accent,
                uncheckedThumbColor = Tok.inkMuted,
                uncheckedTrackColor = Tok.surface,
                uncheckedBorderColor = Tok.fieldLine,
            ),
        )
    }
}
