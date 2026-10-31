package uz.qarzsiz.core

import java.math.BigInteger
import java.math.RoundingMode

/**
 * Pul doim butun son: valyutaning kichik birligida (so'm uchun tiyin, dollar uchun sent).
 * `Double`/`Float` pul uchun ishlatilmaydi. Foizlar — bazis punktda (1% = 100 bp).
 */
enum class Currency(val code: String, val label: String, val symbol: String) {
    UZS("UZS", "So'm", "so'm"),
    USD("USD", "AQSh dollari", "$"),
    EUR("EUR", "Yevro", "€"),
    RUB("RUB", "Rubl", "₽"),
    KZT("KZT", "Tenge", "₸"),
}

object MoneyMath {
    const val MINOR_PER_UNIT = 100L
    const val BP_PER_UNIT = 10_000L

    /** `a * b / c`, yarmi yuqoriga yaxlitlanadi (manfiy natija uchun — noldan uzoqqa). Toshib ketmaydi. */
    fun mulDivHalfUp(a: Long, b: Long, c: Long): Long {
        require(c != 0L) { "c = 0" }
        val r = BigInteger.valueOf(a).multiply(BigInteger.valueOf(b))
            .toBigDecimal()
            .divide(BigInteger.valueOf(c).toBigDecimal(), 0, RoundingMode.HALF_UP)
        return r.longValueExact()
    }

    /** `a * b / c`, pastga (nolga qarab) yaxlitlanadi. Faqat manfiy bo'lmagan qiymatlar uchun. */
    fun mulDivFloor(a: Long, b: Long, c: Long): Long {
        require(a >= 0 && b >= 0 && c > 0) { "manfiy bo'lmagan qiymatlar kutilgan" }
        return BigInteger.valueOf(a).multiply(BigInteger.valueOf(b))
            .divide(BigInteger.valueOf(c)).longValueExact()
    }

    /** Summaning ulushi: `amount * bp / 10000`, yarmi yuqoriga. */
    fun share(amount: Long, bp: Int): Long = mulDivHalfUp(amount, bp.toLong(), BP_PER_UNIT)

    /** `part / whole` nisbati bazis punktda (yarmi yuqoriga). `whole <= 0` bo'lsa — 0. */
    fun ratioBp(part: Long, whole: Long): Int =
        if (whole <= 0) 0 else mulDivHalfUp(part, BP_PER_UNIT, whole).toInt()
}

/** Matnni pulga aylantirish va pulni o'zbekcha ko'rinishda chiqarish. */
object MoneyFormat {
    private const val NBSP = '\u00A0'

    /**
     * «1 500 000», «1500000,50», «12 650.5» → kichik birlikdagi butun son.
     * Bo'sh yoki noto'g'ri matn → `null`. Manfiy qiymat qabul qilinmaydi.
     */
    fun parse(text: String): Long? {
        val cleaned = text.trim().replace(" ", "").replace(NBSP.toString(), "").replace("'", "")
        if (cleaned.isEmpty()) return null
        val normalized = cleaned.replace(',', '.')
        if (normalized.count { it == '.' } > 1) return null
        val parts = normalized.split('.')
        val whole = parts[0]
        val frac = if (parts.size == 2) parts[1] else ""
        if (whole.isEmpty() && frac.isEmpty()) return null
        if (!whole.all { it.isDigit() } || !frac.all { it.isDigit() }) return null
        if (frac.length > 2) return null
        if (whole.length > 15) return null
        val w = if (whole.isEmpty()) 0L else whole.toLong()
        val f = frac.padEnd(2, '0').ifEmpty { "00" }.toLong()
        return w * MoneyMath.MINOR_PER_UNIT + f
    }

    /** Foiz matni: «24», «24,5», «0.75» → bazis punkt. 0..1000% oralig'ida. */
    fun parsePercentBp(text: String): Int? {
        val minor = parse(text) ?: return null
        if (minor > 100_000L) return null
        return minor.toInt()
    }

    /** Kichik birlikdagi summa → «1 500 000» yoki «12 650,50». Kasr qismi 0 bo'lsa ko'rsatilmaydi. */
    fun amount(minor: Long): String {
        val negative = minor < 0
        val abs = if (negative) -minor else minor
        val whole = abs / MoneyMath.MINOR_PER_UNIT
        val frac = abs % MoneyMath.MINOR_PER_UNIT
        val grouped = whole.toString().reversed().chunked(3).joinToString(NBSP.toString()).reversed()
        val sign = if (negative) "−" else ""
        return if (frac == 0L) "$sign$grouped" else "$sign$grouped,${frac.toString().padStart(2, '0')}"
    }

    /**
     * Summa va valyuta belgisi: «1 500 000 so'm», «3 000 $». So'm butun so'mgacha yaxlitlanadi
     * (tiyin amalda ishlatilmaydi) — faqat ko'rsatish uchun, hisob o'zgarmaydi.
     */
    fun withCurrency(minor: Long, currency: Currency): String = when (currency) {
        Currency.UZS -> "${amount(MoneyMath.mulDivHalfUp(minor, 1, MoneyMath.MINOR_PER_UNIT) * MoneyMath.MINOR_PER_UNIT)}${NBSP}so'm"
        else -> "${amount(minor)}$NBSP${currency.symbol}"
    }

    /** Bazis punkt → «24,5%». */
    fun percent(bp: Int): String {
        val whole = bp / 100
        val frac = bp % 100
        return when {
            frac == 0 -> "$whole%"
            frac % 10 == 0 -> "$whole,${frac / 10}%"
            else -> "$whole,${frac.toString().padStart(2, '0')}%"
        }
    }

    /** Katta summani qisqa ko'rinishda: «12,5 mln», «1,2 mlrd». Dashboard uchun. */
    fun compact(minor: Long): String {
        val units = minor / MoneyMath.MINOR_PER_UNIT
        return when {
            units >= 1_000_000_000L -> tenths(units, 1_000_000_000L) + " mlrd"
            units >= 1_000_000L -> tenths(units, 1_000_000L) + " mln"
            units >= 10_000L -> tenths(units, 1_000L) + " ming"
            else -> amount(minor)
        }
    }

    private fun tenths(units: Long, base: Long): String {
        val t = MoneyMath.mulDivHalfUp(units, 10, base)
        return if (t % 10 == 0L) "${t / 10}" else "${t / 10},${t % 10}"
    }
}
