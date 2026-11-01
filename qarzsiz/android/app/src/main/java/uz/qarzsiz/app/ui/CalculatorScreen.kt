package uz.qarzsiz.app.ui

import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.Installment
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.SaveInstead
import uz.qarzsiz.core.UzDates

/** «To'xta va hisobla»: bo'lib to'lashning haqiqiy narxi va yashirin yillik foizi. */
@Composable
fun CalculatorScreen() {
    var cash by rememberSaveable { mutableStateOf("") }
    var down by rememberSaveable { mutableStateOf("") }
    var monthly by rememberSaveable { mutableStateOf("") }
    var months by rememberSaveable { mutableStateOf("") }

    val c = MoneyFormat.parse(cash)
    val dp = if (down.isBlank()) 0L else MoneyFormat.parse(down)
    val m = MoneyFormat.parse(monthly)
    val n = months.toIntOrNull()?.takeIf { it in 1..600 }
    // Yashirin foiz — 50 xonali ikkiga bo'lish usuli: og'ir hisob, UI oqimidan tashqarida.
    val result by produceState<uz.qarzsiz.core.InstallmentResult?>(null, c, dp, m, n) {
        value = if (c != null && c > 0 && dp != null && dp < c && m != null && m > 0 && n != null) {
            withContext(Dispatchers.Default) { Installment.analyze(c, dp, m, n) }
        } else {
            null
        }
    }
    fun uzs(v: Long) = MoneyFormat.withCurrency(v, Currency.UZS)

    ScreenScaffold("Nasiya kalkulyatori") {
        Muted(
            "Do'kon «oyiga atigi …» deydi. Naqd narx va oylik to'lovni yozing — ilova ortiqcha to'lovni va " +
                "bu aslida necha foizli qarz ekanini ko'rsatadi.",
        )
        MoneyInput(cash, { cash = it }, "Naqd narxi")
        MoneyInput(down, { down = it }, "Boshlang'ich to'lov", hint = "Bo'lmasa — bo'sh qoldiring")
        MoneyInput(monthly, { monthly = it }, "Oylik to'lov")
        TextInput(
            months, { months = it.filter(Char::isDigit).take(3) }, "Necha oy",
            error = if (months.isNotBlank() && n == null) "1 dan 600 gacha" else null,
        )
        if (dp != null && c != null && dp >= c) Notice("Boshlang'ich to'lov narxdan kam bo'lishi kerak.", Tok.danger)

        val r = result
        if (r != null && c != null && m != null && n != null) {
            val result = r
            Panel(border = if (result.overpay > 0) Tok.danger else Tok.calm) {
                KeyValue("Jami to'laysiz", uzs(result.totalPaid))
                KeyValue(
                    "Ortiqcha to'lov",
                    "${uzs(result.overpay)} (${MoneyFormat.percent(result.overpayBp)})",
                    if (result.overpay > 0) Tok.danger else Tok.calm,
                )
                if (result.nominalAnnualBp > 0) {
                    Muted("Bu aslida qancha foizli qarz")
                    BigNumber("yiliga ~${MoneyFormat.percent(result.nominalAnnualBp)}", Tok.danger)
                    Muted("Murakkab foiz bilan (samarali): yiliga ~${MoneyFormat.percent(result.effectiveAnnualBp)}")
                } else if (result.overpay <= 0) {
                    Text("Ustamasiz — naqd narx bilan bir xil.", style = MaterialTheme.typography.titleSmall, color = Tok.calm)
                }
            }
            if (result.overpay > 0) {
                val wait = SaveInstead.months(c, dp ?: 0, m)
                SectionTitle("To'xta va o'yla")
                Panel {
                    Bullets(
                        listOf(
                            "Bu narsa zaruratmi yoki havasmi? Zarurat bo'lmasa — qarzdan chiqquncha kuting.",
                            "Har oy shu ${uzs(m)} ni chetga qo'ysangiz, ${UzDates.duration(wait)} da naqd olasiz " +
                                "va ${uzs(result.overpay)} tejaysiz.",
                            "Arzonroq yoki ishlatilgan varianti bormi? Uyda sotsa bo'ladigan buyum bormi?",
                            "Yangi oylik to'lov qarz yukingizni oshiradi — «Reja» bo'limida ta'sirini ko'ring.",
                        ),
                    )
                }
            }
        }
        Disclaimer()
    }
}
