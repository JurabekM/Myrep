package uz.qarzsiz.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Classifier
import uz.qarzsiz.core.Debt
import uz.qarzsiz.core.DebtCategory
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.TalkStatus

@Composable
fun DebtsScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val sorted = state.debts.sortedWith(Classifier.displayOrder)
    val a = sorted.filter { !it.isClosed && it.category == DebtCategory.A }
    val b = sorted.filter { !it.isClosed && it.category == DebtCategory.B }
    val closed = sorted.filter { it.isClosed }

    ScreenScaffold(
        "Qarzlar",
        actions = {
            IconButton(onClick = { nav.go(Route.DebtEdit(null)) }) {
                Icon(Icons.Filled.Add, contentDescription = "Qarz qo'shish")
            }
        },
    ) {
        PrimaryButton("+ Qarz qo'shish") { nav.go(Route.DebtEdit(null)) }
        if (sorted.isEmpty()) {
            Muted("Hali qarz yozilmagan. Eng kichigidan boshlab hammasini yozing: bank, nasiya, karta, qarindosh, do'kon daftari.")
        }
        if (a.isNotEmpty()) {
            SectionTitle("A — issiq qarzlar")
            Muted("Foizi yoki jarimasi bor. Foizi har kuni o'sadi — birinchi shular yopiladi, eng yuqori foizlisidan.")
            a.forEach { DebtCard(it) { nav.go(Route.DebtDetail(it.id)) } }
        }
        if (b.isNotEmpty()) {
            SectionTitle("B — foizsiz qarzlar")
            Muted("Qarindosh, tanish, do'kon. Ular bilan gaplashib, vaqt va aniq tartib kelishib olinadi.")
            b.forEach { DebtCard(it) { nav.go(Route.DebtDetail(it.id)) } }
        }
        if (closed.isNotEmpty()) {
            SectionTitle("Yopilgan")
            closed.forEach { DebtCard(it) { nav.go(Route.DebtDetail(it.id)) } }
        }
        Disclaimer()
    }
}

@Composable
fun DebtCard(d: Debt, onClick: () -> Unit) {
    val catColor = if (d.category == DebtCategory.A) Tok.danger else Tok.calm
    Panel(onClick = onClick, border = if (d.overdue && !d.isClosed) Tok.warn else Tok.line) {
        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
                Text(d.creditor, style = MaterialTheme.typography.titleSmall, color = Tok.ink)
                Muted(d.kind.label)
            }
            Text(
                MoneyFormat.withCurrency(d.balance, d.currency),
                style = MaterialTheme.typography.titleSmall,
                color = if (d.isClosed) Tok.inkMuted else Tok.ink,
            )
        }
        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            if (d.isClosed) {
                Tag("Yopildi", Tok.calm)
            } else {
                if (d.annualRateBp > 0) Tag("${MoneyFormat.percent(d.annualRateBp)} yillik", catColor)
                if (d.hasPenalty) Tag("jarima", Tok.danger)
                if (d.overdue) Tag("muddati o'tgan", Tok.warn)
                if (d.category == DebtCategory.B) {
                    Tag(
                        when (d.talkStatus) {
                            TalkStatus.NOT_TALKED -> "gaplashilmagan"
                            TalkStatus.TALKED -> "javob kutilmoqda"
                            TalkStatus.AGREED -> "kelishildi"
                        },
                        if (d.talkStatus == TalkStatus.AGREED) Tok.calm else Tok.inkMuted,
                    )
                }
            }
        }
        if (d.startBalance > 0) ProgressLine(d.progressBp, catColor)
    }
}
