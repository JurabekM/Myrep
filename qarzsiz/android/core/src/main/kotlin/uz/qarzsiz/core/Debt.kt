package uz.qarzsiz.core

import kotlinx.serialization.Serializable

/** Qarz turi. `usuallyInterest` — odatda foizli yoki ustamali bo'ladimi (forma uchun maslahat). */
@Serializable
enum class DebtKind(val label: String, val usuallyInterest: Boolean) {
    BANK_CREDIT("Bank krediti", true),
    MORTGAGE("Ipoteka", true),
    AUTO_LOAN("Avtokredit", true),
    MICROLOAN("Mikroqarz", true),
    INSTALLMENT("Nasiya / bo'lib to'lash", true),
    CARD("Karta (overdraft, kredit karta)", true),
    FOREIGN_BANK("Chet el banki", true),
    PRIVATE_INTEREST("Foizga olingan pul (shaxsdan)", true),
    PERSONAL("Qarindosh yoki tanish", false),
    SHOP("Do'kon daftari", false),
    OTHER("Boshqa", false),
}

/** 2-qadam: A — foizli yoki jarimali («issiq»), B — foizsiz (kelishsa bo'ladigan). */
@Serializable
enum class DebtCategory(val label: String, val hint: String) {
    A("A — issiq", "Foizi yoki jarimasi bor. Birinchi yopiladi."),
    B("B — foizsiz", "Kelishib, vaqt so'rasa bo'ladi."),
}

/** 3-qadam: B qarz egasi bilan kelishuv holati. */
@Serializable
enum class TalkStatus(val label: String) {
    NOT_TALKED("Hali gaplashilmagan"),
    TALKED("Gaplashildi, javob kutilmoqda"),
    AGREED("Kelishildi"),
}

@Serializable
data class Debt(
    val id: String,
    /** Kimdan yoki qayerdan: «Aziz aka», «Xalq banki», «Uzum Nasiya». */
    val creditor: String,
    val kind: DebtKind,
    val currency: Currency = Currency.UZS,
    /** Hozirgi qoldiq (kichik birlikda). */
    val balance: Long,
    /** Boshlang'ich qoldiq — progress uchun (ro'yxatga kiritilgandagi qoldiq). */
    val startBalance: Long = balance,
    /** Yillik foiz yoki ustama, bazis punkt (24% = 2400). Foizsiz — 0. */
    val annualRateBp: Int = 0,
    /** Oylik majburiy (yoki kelishilgan) to'lov, qarz valyutasida. */
    val monthlyPayment: Long = 0,
    /** Oyning to'lov kuni (1..31) yoki `null`. */
    val dueDay: Int? = null,
    /** Kechiksa jarima (penya) bormi. */
    val hasPenalty: Boolean = false,
    /** Hozir muddati o'tgan to'lov bormi. */
    val overdue: Boolean = false,
    val talkStatus: TalkStatus = TalkStatus.NOT_TALKED,
    /** Kelishuv yoki eslatma matni: «Yanvardan oyiga 1 mln, har oy 10-sanada». */
    val note: String = "",
    /** Kiritilgan sana, ISO (yyyy-MM-dd). */
    val createdOn: String,
    /** Yopilgan sana yoki `null`. */
    val closedOn: String? = null,
) {
    val isClosed: Boolean get() = closedOn != null || balance <= 0L

    val category: DebtCategory get() = Classifier.category(this)

    /** Yopilgan qismi, bazis punkt (0..10000). */
    val progressBp: Int
        get() {
            if (startBalance <= 0L) return if (balance <= 0L) 10_000 else 0
            val paid = (startBalance - balance).coerceIn(0L, startBalance)
            return MoneyMath.ratioBp(paid, startBalance)
        }
}

object Classifier {
    /** Foiz yoki jarima bor → A. Aks holda B. Turi emas, haqiqiy shart hal qiladi. */
    fun category(debt: Debt): DebtCategory =
        if (debt.annualRateBp > 0 || debt.hasPenalty) DebtCategory.A else DebtCategory.B

    /** Oylik foiz (taxminiy): `qoldiq × yillik foiz / 12`, yarmi yuqoriga. */
    fun monthlyInterest(balance: Long, annualRateBp: Int): Long =
        if (balance <= 0 || annualRateBp <= 0) 0
        else MoneyMath.mulDivHalfUp(balance, annualRateBp.toLong(), 12 * MoneyMath.BP_PER_UNIT)

    /**
     * Ro'yxat tartibi: avval A (yuqori foizdan pastga, keyin muddati o'tgan, keyin kichik qoldiq),
     * keyin B (muddati o'tgan, keyin kichik qoldiq). Yopilganlar oxirida.
     */
    val displayOrder: Comparator<Debt> = compareBy<Debt> { it.isClosed }
        .thenBy { it.category }
        .thenByDescending { it.annualRateBp }
        .thenByDescending { it.overdue }
        .thenBy { it.balance }
        .thenBy { it.id }
}

/**
 * Valyuta kurslari: 1 birlik valyuta necha so'm (so'mning kichik birligida, ya'ni tiyin).
 * Masalan, 1 USD = 12 650 so'm → `1_265_000`. Internet yo'q — kursni foydalanuvchi kiritadi.
 */
@Serializable
data class FxRates(val uzsMinorPerUnit: Map<Currency, Long> = emptyMap()) {
    fun rate(currency: Currency): Long? =
        if (currency == Currency.UZS) MoneyMath.MINOR_PER_UNIT else uzsMinorPerUnit[currency]?.takeIf { it > 0 }

    /** Summani so'mga o'tkazadi; kurs kiritilmagan bo'lsa `null`. */
    fun toUzs(amountMinor: Long, currency: Currency): Long? {
        if (currency == Currency.UZS) return amountMinor
        val r = rate(currency) ?: return null
        return MoneyMath.mulDivHalfUp(amountMinor, r, MoneyMath.MINOR_PER_UNIT)
    }
}
