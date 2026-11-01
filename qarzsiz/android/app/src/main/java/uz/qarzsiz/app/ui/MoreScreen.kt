package uz.qarzsiz.app.ui

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CheckboxDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.AppViewModel
import uz.qarzsiz.core.Currency
import uz.qarzsiz.core.FxRates
import uz.qarzsiz.core.Habits
import uz.qarzsiz.core.MoneyFormat
import uz.qarzsiz.core.UzDates

@Composable
fun MoreScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    var confirmWipe by rememberSaveable { mutableStateOf(false) }
    ScreenScaffold("Yana") {
        MenuItem("Yo'l xaritasi", "Metod: 3 qadam, 70/30 va to'g'ri tartib") { nav.go(Route.Guide) }
        MenuItem(
            "To'lov eslatmalari",
            if (state.reminders.enabled) "Yoqilgan · ${state.reminders.daysBefore} kun oldin, ${state.reminders.hour}:00" else "O'chiq",
        ) { nav.go(Route.Reminders) }
        MenuItem("Kun tartibi", "Erta turish, harakat, o'qish — kichik odatlar") { nav.go(Route.Habits) }
        MenuItem("Yordam va huquqlar", "Stress, kollektor bosimi, firibgarlik, yangi qarzdan saqlanish") { nav.go(Route.Help) }
        MenuItem("Valyuta kurslari", "Dollar, rubl, tenge qarzlar uchun") { nav.go(Route.Rates) }
        MenuItem("Zaxira nusxa", "Telefon almashtirganda ma'lumotni ko'chirish") { nav.go(Route.Backup) }
        MenuItem("Ilova haqida", "Maxfiylik, litsenziya") { nav.go(Route.About) }

        SectionTitle("Yozuv")
        Panel {
            ScriptChoice(state.script) { vm.setScript(it) }
            Muted("Interfeys matnlari tanlangan yozuvda. Siz kiritgan izohlar o'zgarmaydi.")
        }

        SectionTitle("Maxfiylik")
        MenuItem(
            "PIN-kod",
            state.pin?.let { "Yoqilgan" } ?: "O'chiq — ilovani begona ko'zdan himoya qilish",
        ) { nav.go(Route.PinSettings) }
        Panel {
            SwitchRow("Ekran suratini taqiqlash", state.secureScreen) { vm.setSecureScreen(it) }
            Muted("Yoqilganda ekran suratga olinmaydi va «so'nggi ilovalar»da qarzlaringiz ko'rinmaydi.")
        }

        SectionTitle("Hammasini o'chirish")
        if (!confirmWipe) {
            SecondaryButton("Barcha ma'lumotni o'chirish", color = Tok.danger) { confirmWipe = true }
        } else {
            Notice("Barcha qarz, to'lov va sozlamalar butunlay o'chadi. Zaxira nusxangiz bormi?", Tok.danger)
            PrimaryButton("Ha, hammasini o'chirish") {
                confirmWipe = false
                vm.wipeAll()
            }
            SecondaryButton("Bekor qilish") { confirmWipe = false }
        }
    }
}

@Composable
private fun MenuItem(title: String, subtitle: String, onClick: () -> Unit) {
    Panel(onClick = onClick) {
        Text(title, style = MaterialTheme.typography.titleSmall, color = Tok.ink)
        Muted(subtitle)
    }
}

@Composable
fun GuideScreen(vm: AppViewModel, nav: Nav) {
    ScreenScaffold("Yo'l xaritasi", onBack = { nav.back() }) {
        Muted("Qarzdan chiqish — bir kunlik ish emas, lekin aniq yo'li bor. Bu yo'l ko'p odam sinab ko'rgan oddiy qadamlardan iborat.")
        GuideBlock(
            "0. Avval o'zingizga ayting",
            "Qarzni yashirish va o'ylamaslik uni kichraytirmaydi. «Men chiqaman, reja bilan harakat qilaman» — " +
                "deb o'zingizga va'da bering. Tushkunlik emas, harakat kerak.",
        )
        GuideBlock(
            "1. To'liq ro'yxat",
            "Qog'ozga yoki ilovaga hammasini yozing: bank krediti, ipoteka, nasiya, karta, chet el banki, " +
                "qarindosh, tanish, do'kon daftari. Har biriga — qoldiq, foiz va oylik to'lov. Bitta ham qolmasin: " +
                "esdan chiqqan qarz eng yomon paytda chiqib keladi.",
        )
        GuideBlock(
            "2. Tahlil: A va B",
            "A — foizi yoki jarimasi borlar. Ularning foizi har kuni o'sadi, shuning uchun birinchi yopiladi, " +
                "eng yuqori foizlisidan. B — foizsizlar (qarindosh, tanish). Ular bilan kelishish mumkin. " +
                "Ilova bu tasnifni avtomatik qiladi va har oy foizga qancha ketayotganini ko'rsatadi.",
        )
        GuideBlock(
            "3. B qarz egalari bilan halol gaplashish",
            "Har biriga o'zingiz qo'ng'iroq qiling. Qarzni tan oling, vaziyatni ochiq ayting va ANIQ taklif bering: " +
                "«dekabrdan har oy 10-sanada 300 dollar». Qo'rqitish, ko'z yoshi yoki bajarib bo'lmaydigan va'da " +
                "ishonchni buzadi. Kelishuvni yozib qo'ying va har oy o'zingiz xabar bering.",
        )
        GuideBlock(
            "4. Reja 70/30",
            "Daromadning 70% i qarzga, 30% i yashash va ishga. 100% emas: oila och qolsa yoki ish uchun pul " +
                "qolmasa, bir oydan keyin yana qarz olasiz. Daromad kam bo'lsa — ulushni yashash minimumiga moslang.",
        )
        GuideBlock(
            "5. Ikki qavatli to'lov",
            "Birinchi qavat: HAMMA qarzning majburiy to'lovi — oz bo'lsa ham, to'xtatmasdan. Bu jarima va " +
                "nizolardan saqlaydi. Ikkinchi qavat: ortgan pul bitta qarzga — eng yuqori foizlisiga («Ko'chki»). " +
                "Pulni hammasiga teng bo'lish ham mumkin, lekin foizli qarz sekin yopiladi va qimmatga tushadi. " +
                "«Reja» bo'limida uchala usulni o'z raqamlaringizda taqqoslang.",
        )
        GuideBlock(
            "6. Yopilgan qarzning puli — keyingisiga",
            "Bitta qarz yopilsa, uning oylik to'lovi bo'shaydi. Uni sarflamang — keyingi qarzga qo'shing. " +
                "Shunda har yopilgan qarz bilan tezlik oshadi.",
        )
        GuideBlock(
            "7. Diqqat — daromadga",
            "Qarzdan chiqquncha dabdaba, restoran, ortiqcha kiyim va yangi nasiyani to'xtating. Erta turing, " +
                "harakat qiling, har kuni kasbingizni o'rganing. Katta qarzni faqat ko'proq ishlab emas, " +
                "malakani oshirib — qimmatroq mehnat qilib yopish osonroq. Yaxshi odamlar davrasida bo'ling: " +
                "muhit odatni o'zgartiradi.",
        )
        GuideBlock(
            "8. Yangi qarz — oxirgi chora",
            "Har xariddan oldin «Nasiya» kalkulyatorida haqiqiy narxini ko'ring. «Oyiga atigi …» degan gap " +
                "ko'pincha yiliga 40–60% li qarz degani.",
        )
        Notice(
            "Muntazam to'lab turish va kreditor bilan yozma aloqa vaziyatni yumshatadi, lekin bu qonuniy himoya " +
                "kafolati emas. Sud, garov yoki jinoyat ishi bo'lsa — yuristga murojaat qiling.",
            Tok.calm,
        )
        Disclaimer()
        PrimaryButton("Rejani tuzish") {
            vm.markAnalysisSeen()
            nav.tab(Route.Plan)
        }
    }
}

@Composable
private fun GuideBlock(title: String, text: String) {
    Panel {
        Text(title, style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
        Text(text, style = MaterialTheme.typography.bodyMedium, color = Tok.ink)
    }
}

@Composable
fun HabitsScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val today = vm.today()
    var newHabit by rememberSaveable { mutableStateOf("") }
    ScreenScaffold("Kun tartibi", onBack = { nav.back() }) {
        Muted("Bugun: ${UzDates.date(today)}. Belgilang — ketma-ket kunlar sanaladi.")
        state.habits.forEach { h ->
            val done = Habits.key(today, h.id) in state.habitDone
            val streak = Habits.streak(state.habitDone, h.id, today)
            Panel(border = if (done) Tok.calm else Tok.line, onClick = { vm.toggleHabit(h.id, today) }) {
                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(
                        checked = done,
                        // Butun qator bosiladi (katta nishon); belgi faqat holatni ko'rsatadi.
                        onCheckedChange = null,
                        colors = CheckboxDefaults.colors(checkedColor = Tok.calm, checkmarkColor = Tok.accentInk, uncheckedColor = Tok.fieldLine),
                    )
                    androidx.compose.foundation.layout.Column(Modifier.weight(1f)) {
                        // O'z odati — foydalanuvchi yozganidek; standart odatlar tanlangan yozuvda.
                        Text(h.title, style = MaterialTheme.typography.bodyMedium, color = Tok.ink, raw = h.id.startsWith("u-"))
                        if (streak > 0) Muted("$streak kun ketma-ket")
                    }
                    IconButton(onClick = { vm.removeHabit(h.id) }) {
                        Icon(Icons.Filled.Delete, contentDescription = t("Odatni o'chirish") + ": " + h.title, tint = Tok.inkMuted)
                    }
                }
            }
        }
        TextInput(newHabit, { newHabit = it }, "Yangi odat", hint = "Masalan: ibodat, kitob, ingliz tili, sport")
        SecondaryButton("Qo'shish") {
            vm.addHabit(newHabit)
            newHabit = ""
        }
        Muted("Kun tartibi sog'liq va daromad uchun. Bu majburiyat emas — o'zingizga yordam.")
    }
}

@Composable
fun HelpScreen(nav: Nav) {
    ScreenScaffold("Yordam va huquqlar", onBack = { nav.back() }) {
        GuideBlock(
            "Siz yolg'iz emassiz",
            "Qarz — hayotning bir davri, sizning qadringiz emas. Og'irlikni yolg'iz ko'tarmang: turmush " +
                "o'rtog'ingizga yoki ishonchli odamga ayting. Uyqu, ovqat va oila bilan suhbat — qarz rejasining bir qismi.",
        )
        Notice(
            "Agar o'zingizga zarar yetkazish fikri kelsa — hoziroq yaqiningizga ayting yoki 103 (tez yordam) ga " +
                "qo'ng'iroq qiling. Hech qanday qarz hayotdan qimmat emas.",
            Tok.danger, "Juda og'ir bo'lsa",
        )
        GuideBlock(
            "Bosim va tahdid",
            "Qarzni talab qilish mumkin, lekin haqorat, tahdid, oilangizni qo'rqitish, tunda bezovta qilish — " +
                "mumkin emas. Qo'ng'iroq va xabarlarni saqlang. Bank xodimi bo'lsa — bankning o'ziga yozma shikoyat, " +
                "javob bo'lmasa Markaziy bankning murojaatlar xizmatiga. Shaxs tahdid qilsa — 102.",
        )
        GuideBlock(
            "To'lay olmasangiz",
            "Jimgina to'xtatmang. Muddat kelmasdan kreditorga yozma murojaat qiling, oz bo'lsa ham to'lab turing. " +
                "Bank uchun ariza namunasi — A qarz kartochkasida. Sudga chaqiruv kelsa, e'tiborsiz qoldirmang va " +
                "yuristdan maslahat oling.",
        )
        GuideBlock(
            "Yangi kreditdan o'zingizni himoya qiling",
            "O'zbekistonda fuqaro o'z nomiga kredit olinishini ixtiyoriy cheklash imkoniyati joriy qilingan. " +
                "Amaldagi tartibni davlat xizmatlari portali yoki bankingizdan aniqlang. Kredit tarixingizni ham " +
                "vaqti-vaqti bilan tekshirib turing — nomingizga siz bilmagan qarz yozilmaganmi.",
        )
        GuideBlock(
            "Firibgarlik belgilari",
            "«Qarzingizni yopib beramiz», «kredit tarixini tozalaymiz», «kafilsiz tez pul» — va oldindan to'lov " +
                "so'rashsa, bu firibgarlik. Karta ma'lumoti va SMS kodni hech kimga aytmang.",
        )
        GuideBlock(
            "Qarz bilan qarz yopish",
            "Bir qarzni yopish uchun qimmatroq yangi qarz olish — chuqurroq botish. Birovga kafil bo'lmang: " +
                "uning qarzi sizning qarzingizga aylanishi mumkin.",
        )
        Disclaimer()
    }
}

@Composable
fun RatesScreen(vm: AppViewModel, nav: Nav) {
    val state by vm.state.collectAsStateWithLifecycle()
    val others = Currency.entries.filter { it != Currency.UZS }
    ScreenScaffold("Valyuta kurslari", onBack = { nav.back() }) {
        Muted(
            "Ilova internetga ulanmaydi, shuning uchun kursni o'zingiz yozasiz (bank yoki Markaziy bank kursi). " +
                "Kurs faqat jami summani so'mda ko'rsatish va rejalash uchun kerak.",
        )
        others.forEach { c ->
            val current = state.settings.rates.uzsMinorPerUnit[c]
            var text by rememberSaveable(c.name) {
                mutableStateOf(current?.let { MoneyFormat.amount(it).replace(' ', ' ') } ?: "")
            }
            MoneyInput(
                text,
                { v ->
                    text = v
                    val parsed = MoneyFormat.parse(v)
                    val s = vm.state.value.settings
                    val map = s.rates.uzsMinorPerUnit.toMutableMap()
                    // Bo'sh yoki 0 — kurs o'chiriladi (eski kurs jimgina qolib ketmasin).
                    if (v.isBlank() || parsed == 0L) map.remove(c) else if (parsed != null) map[c] = parsed
                    vm.updateSettings(s.copy(rates = FxRates(map)))
                },
                "1 ${c.code} = ? so'm",
            )
        }
    }
}

@Composable
fun BackupScreen(vm: AppViewModel, nav: Nav) {
    val ctx = LocalContext.current
    val script = LocalScript.current
    var pending by remember { mutableStateOf<String?>(null) }
    var error by rememberSaveable { mutableStateOf<String?>(null) }

    val exporter = rememberLauncherForActivityResult(ActivityResultContracts.CreateDocument("application/json")) { uri: Uri? ->
        if (uri != null) {
            val ok = runCatching {
                ctx.contentResolver.openOutputStream(uri, "wt")!!.use { it.write(vm.exportText().encodeToByteArray()) }
            }.isSuccess
            ctx.toast(if (ok) "Saqlandi" else "Saqlab bo'lmadi", script)
        }
    }
    val importer = rememberLauncherForActivityResult(ActivityResultContracts.OpenDocument()) { uri: Uri? ->
        if (uri != null) {
            val text = runCatching {
                ctx.contentResolver.openInputStream(uri)!!.use { s ->
                    val bytes = s.readBytes()
                    require(bytes.size < 5_000_000) { "katta" }
                    bytes.decodeToString()
                }
            }.getOrNull()
            if (text == null) error = "Faylni o'qib bo'lmadi." else { pending = text; error = null }
        }
    }

    ScreenScaffold("Zaxira nusxa", onBack = { nav.back() }) {
        Notice(
            "Zaxira fayli SHIFRLANMAGAN: unda barcha qarzlaringiz ochiq ko'rinadi. Uni faqat o'zingizga " +
                "tegishli joyda saqlang va begonaga yubormang.",
            Tok.warn,
        )
        PrimaryButton("Zaxira faylini saqlash") { exporter.launch("qarzsiz-zaxira-${vm.today()}.json") }
        SecondaryButton("Zaxiradan tiklash") { importer.launch(arrayOf("application/json", "text/plain", "application/octet-stream")) }
        error?.let { Notice(it, Tok.danger) }
        if (pending != null) {
            Notice("Hozirgi barcha ma'lumot fayldagisi bilan ALMASHTIRILADI. Davom etasizmi?", Tok.danger)
            PrimaryButton("Ha, tiklash") {
                val err = vm.importText(pending!!)
                pending = null
                if (err != null) error = err else ctx.toast("Tiklandi", script)
            }
            SecondaryButton("Bekor qilish") { pending = null }
        }
    }
}

@Composable
fun AboutScreen(nav: Nav) {
    val ctx = LocalContext.current
    val version = runCatching { ctx.packageManager.getPackageInfo(ctx.packageName, 0).versionName }.getOrNull() ?: "?"
    ScreenScaffold("Ilova haqida", onBack = { nav.back() }) {
        Panel {
            Text("Qarzsiz $version", style = MaterialTheme.typography.titleMedium, color = Tok.ink)
            Muted("Kredit va qarzdan reja bilan chiqish uchun to'liq offlayn yordamchi.")
        }
        Panel {
            Text("Maxfiylik", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
            Bullets(
                listOf(
                    "Ilovada internet ruxsati yo'q — hech qanday ma'lumot hech qayerga yuborilmaydi.",
                    "Ma'lumot telefon xotirasida AES-256 bilan shifrlangan, kalit Android Keystore'da.",
                    "Bulutli zaxira o'chirilgan. Zaxira nusxani faqat siz o'zingiz yaratasiz.",
                    "Reklama, kuzatuv, ro'yxatdan o'tish yo'q.",
                ),
            )
        }
        Panel {
            Text("Mustaqillik", style = MaterialTheme.typography.titleSmall, color = Tok.accentText)
            Muted(
                "Ilova hech qanday bank, mikroqarz tashkiloti, kurs yoki muallif bilan bog'liq emas va hech narsani " +
                    "reklama qilmaydi. Qarzdan chiqish metodi umumiy moliyaviy tamoyillarga asoslangan.",
            )
        }
        Muted("© 2026 Joʻrabek Mashgʻulatov. Barcha huquqlar himoyalangan. Shrift: Noto Sans (SIL Open Font License 1.1).")
        Disclaimer()
    }
}
