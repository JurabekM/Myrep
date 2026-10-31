package uz.qarzsiz.core

import kotlinx.serialization.Serializable

/** Interfeys yozuvi. Ma'lumot (summa, sana) yozuvga bog'liq emas — faqat ko'rsatish. */
@Serializable
enum class Script(val label: String) {
    LATIN("Lotin"),
    CYRILLIC("Кирилл"),
}

/**
 * O'zbek lotin yozuvidan kirill yozuviga o'girish (1995-yilgi alifbo moslik jadvali asosida).
 * Ilovadagi matnlar uchun mo'ljallangan: so'zlar ro'yxati (oylar, rus tilidan o'zlashgan so'zlar)
 * va o'zgarmaydigan atamalar (valyuta kodlari, brendlar) alohida ko'rib chiqiladi.
 * Kirill harflari, raqamlar va belgilar o'zgarmaydi — qayta o'girish xavfsiz.
 */
object Translit {
    private val apostrophes = setOf('\'', '’', 'ʻ', '‘', 'ʼ', '`')

    /** Butun so'z almashinuvi (kichik harfda). Rus tilidan o'zlashgan so'zlarda yumshatish belgisi bor. */
    private val words = mapOf(
        "yanvar" to "январь", "fevral" to "февраль", "aprel" to "апрель", "iyun" to "июнь",
        "iyul" to "июль", "sentabr" to "сентябрь", "oktabr" to "октябрь", "noyabr" to "ноябрь",
        "dekabr" to "декабрь", "rubl" to "рубль", "aqsh" to "АҚШ", "kalkulyator" to "калькулятор",
        "overdraft" to "овердрафт", "penya" to "пеня",
    )

    /** O'zgarmaydigan atamalar (aynan shu ko'rinishda). */
    private val keep = setOf(
        "USD", "UZS", "EUR", "RUB", "KZT", "Android", "Keystore", "AES", "GCM", "Noto", "Sans",
        "SIL", "Open", "Font", "License", "SAF", "JSON",
    )

    private val single = mapOf(
        'a' to "а", 'b' to "б", 'd' to "д", 'e' to "е", 'f' to "ф", 'g' to "г", 'h' to "ҳ", 'i' to "и",
        'j' to "ж", 'k' to "к", 'l' to "л", 'm' to "м", 'n' to "н", 'o' to "о", 'p' to "п", 'q' to "қ",
        'r' to "р", 's' to "с", 't' to "т", 'u' to "у", 'v' to "в", 'x' to "х", 'y' to "й", 'z' to "з",
        'c' to "к", 'w' to "в",
    )

    private val cyrVowels = setOf('а', 'е', 'ё', 'и', 'о', 'у', 'ў', 'э', 'ю', 'я')

    fun apply(text: String, script: Script): String = if (script == Script.CYRILLIC) toCyrillic(text) else text

    fun toCyrillic(text: String): String {
        val out = StringBuilder(text.length)
        var i = 0
        while (i < text.length) {
            val c = text[i]
            if (c.isLatinLetter()) {
                var j = i
                // So'z: lotin harflari va ichidagi tutuq belgilari (oxiridagi tutuq — so'zga kirmaydi).
                while (j < text.length && (text[j].isLatinLetter() ||
                        (text[j] in apostrophes && j + 1 < text.length && text[j + 1].isLatinLetter()))
                ) j++
                out.append(word(text.substring(i, j)))
                i = j
            } else {
                out.append(c)
                i++
            }
        }
        return out.toString()
    }

    private fun Char.isLatinLetter() = this in 'a'..'z' || this in 'A'..'Z'

    private fun word(w: String): String {
        if (w in keep) return w
        val lower = w.lowercase()
        if (words[lower]?.any { it.isUpperCase() } == true) return words.getValue(lower)
        val body = words[lower] ?: withSuffix(lower) ?: letters(lower)
        val letterCount = w.count { it.isLetter() }
        return when {
            letterCount > 1 && w.filter { it.isLetter() }.all { it.isUpperCase() } -> body.uppercase()
            w.first().isUpperCase() -> body.replaceFirstChar { it.uppercase() }
            else -> body
        }
    }

    /** Lug'atdagi o'zak + qo'shimcha: «dekabrdan» → «декабрдан» (qo'shimcha oldidan «ь» tushadi). */
    private fun withSuffix(lower: String): String? {
        val stem = words.keys.filter { lower.startsWith(it) && lower.length > it.length }.maxByOrNull { it.length }
            ?: return null
        val stemCyr = words.getValue(stem)
        if (stemCyr.any { it.isUpperCase() }) return null
        return stemCyr.removeSuffix("ь") + letters(lower.substring(stem.length))
    }

    private fun letters(w: String): String {
        val out = StringBuilder(w.length)
        var i = 0
        fun at(k: Int) = w.getOrNull(k)
        fun apo(k: Int) = at(k) in apostrophes
        while (i < w.length) {
            val c = w[i]
            when {
                // o' → ў, g' → ғ (tutuq belgisining barcha shakllari)
                c == 'o' && apo(i + 1) -> { out.append('ў'); i += 2 }
                c == 'g' && apo(i + 1) -> { out.append('ғ'); i += 2 }
                c in apostrophes -> { out.append('ъ'); i++ }
                c == 's' && at(i + 1) == 'h' -> { out.append('ш'); i += 2 }
                c == 'c' && at(i + 1) == 'h' -> { out.append('ч'); i += 2 }
                // -tsiya, -tsion → -ция, -цион (o'zlashgan so'zlar)
                c == 't' && at(i + 1) == 's' && at(i + 2) == 'i' && (at(i + 3) == 'y' || at(i + 3) == 'o') -> {
                    out.append('ц'); i += 2
                }
                c == 'y' && at(i + 1) == 'o' && !apo(i + 2) -> { out.append('ё'); i += 2 }
                c == 'y' && at(i + 1) == 'u' -> { out.append('ю'); i += 2 }
                c == 'y' && at(i + 1) == 'a' -> { out.append('я'); i += 2 }
                c == 'y' && at(i + 1) == 'e' -> { out.append('е'); i += 2 }
                // e: so'z boshida va unlidan keyin — э
                c == 'e' && (out.isEmpty() || out.last() in cyrVowels) -> { out.append('э'); i++ }
                else -> { out.append(single[c] ?: c.toString()); i++ }
            }
        }
        return out.toString()
    }
}
