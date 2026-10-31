package uz.qarzsiz.app.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.MoneyFormat

/** Birinchi ochilish: 3 sahifa — ishonch, yo'l, daromad. */
@Composable
fun OnboardingScreen(vm: AppViewModel) {
    var page by rememberSaveable { mutableIntStateOf(0) }
    var income by rememberSaveable { mutableStateOf("") }
    var living by rememberSaveable { mutableStateOf("") }

    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 16.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Text("${page + 1} / 3", style = MaterialTheme.typography.labelMedium, color = Tok.inkMuted)
        if (page == 0) {
            // Yozuvni birinchi ekrandayoq tanlash: kirillda o'qiydiganlar uchun.
            ScriptChoice(vm.state.value.script) { vm.setScript(it) }
        }
        when (page) {
            0 -> {
                Text("Qarzdan chiqish mumkin", style = MaterialTheme.typography.headlineMedium, color = Tok.ink)
                Text(
                    "Kredit, nasiya, tanishlardan olingan pul — hammasi bir boshda bo'lsa, odam uxlay olmaydi, " +
                        "oilada ham, ishda ham kayfiyat qolmaydi. Bu ilova shu og'irlikni raqam va rejaga aylantiradi.",
                    style = MaterialTheme.typography.bodyLarge, color = Tok.ink,
                )
                Panel {
                    Text("Ma'lumotingiz faqat shu telefonda", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
                    Bullets(
                        listOf(
                            "Ilova internetga umuman ulanmaydi — unda internet ruxsati yo'q.",
                            "Qarzlar ro'yxati telefonda shifrlangan holda saqlanadi.",
                            "Ekran suratga olinmaydi va «so'nggi ilovalar»da ko'rinmaydi.",
                            "Ro'yxatdan o'tish, telefon raqami, reklama — yo'q.",
                        ),
                    )
                }
            }
            1 -> {
                Text("Yo'l: 3 qadam va reja", style = MaterialTheme.typography.headlineMedium, color = Tok.ink)
                Step("1", "Ro'yxat", "Hamma qarzni yozing: kimdan, qancha, necha foiz. Hech birini yashirmang — ro'yxat hukm emas, xarita.")
                Step("2", "Tahlil: A va B", "A — foizi yoki jarimasi borlar («issiq»), birinchi yopiladi. B — foizsiz, tanish-bilishdan.")
                Step("3", "Kelishish", "B qarz egalari bilan halol gaplashing: aniq summa va sana taklif qiling, vaqt so'rang.")
                Step("4", "Reja 70/30", "Daromadning 70% i qarzga, 30% i yashash va ishga. Hamma qarzga majburiy to'lov, ortgani — eng qimmat qarzga.")
                Disclaimer()
            }
            else -> {
                Text("Oylik daromadingiz", style = MaterialTheme.typography.headlineMedium, color = Tok.ink)
                Muted("Reja shu raqamlarga tayanadi. Hozir bilmasangiz, keyin «Reja» bo'limida kiritasiz.")
                MoneyInput(income, { income = it }, "Oylik daromad (o'rtacha, qo'lga tegadigan)")
                MoneyInput(
                    living, { living = it }, "Minimal yashash xarajati",
                    hint = "Ovqat, kommunal, yo'l, dori — eng zarur narsalar",
                )
                val inc = MoneyFormat.parse(income) ?: 0
                val liv = MoneyFormat.parse(living) ?: 0
                if (inc > 0 && liv > 0) {
                    val share = vm.state.value.settings.debtShareBp
                    val suggested = uz.qarzsiz.core.Budget.suggestedShareBp(inc, liv, share)
                    if (suggested != share) {
                        Notice(
                            "Daromadning ${MoneyFormat.percent(share)} ini qarzga bersangiz, yashashga yetmaydi. " +
                                "Reja ${MoneyFormat.percent(suggested)} dan boshlanadi.",
                        )
                    }
                }
            }
        }
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            if (page > 0) SecondaryButton("Orqaga", Modifier.weight(1f)) { page-- }
            PrimaryButton(if (page < 2) "Davom etish" else "Boshlash", Modifier.weight(1f)) {
                if (page < 2) {
                    page++
                } else {
                    val inc = MoneyFormat.parse(income) ?: 0
                    val liv = MoneyFormat.parse(living) ?: 0
                    val s = vm.state.value.settings
                    val share = uz.qarzsiz.core.Budget.suggestedShareBp(inc, liv, s.debtShareBp)
                    vm.updateSettings(s.copy(monthlyIncome = inc, livingMinimum = liv, debtShareBp = share))
                    vm.finishOnboarding()
                }
            }
        }
    }
}

@Composable
private fun Step(n: String, title: String, text: String) {
    Panel {
        Text("$n. $title", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
    }
}
