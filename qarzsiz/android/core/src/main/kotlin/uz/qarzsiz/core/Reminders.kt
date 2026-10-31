package uz.qarzsiz.core

import java.time.LocalDate
import java.time.temporal.ChronoUnit

/** Bitta to'lov eslatmasi. */
data class ReminderItem(
    val debtId: String,
    val creditor: String,
    val dueDate: LocalDate,
    /** 0 — bugun, 1 — ertaga, ... */
    val daysLeft: Int,
    /** Oylik to'lov (qarz valyutasida) yoki `null` — kelishilmagan. */
    val amountText: String?,
)

/**
 * To'lov kuni eslatmalari: qaysi qarzga, qachon. Har kuni bir marta tekshiriladi;
 * eslatma `daysBefore` kun oldin va to'lov kunining o'zida chiqadi.
 * Shu muddatga to'lov allaqachon yozilgan bo'lsa — eslatma chiqmaydi.
 */
object Reminders {
    const val DEFAULT_DAYS_BEFORE = 2
    const val DEFAULT_HOUR = 9

    /** To'lov kunidan oldingi shu oraliqdagi to'lov shu oy uchun to'langan deb hisoblanadi. */
    private const val PAID_WINDOW_DAYS = 20L

    fun due(
        debts: List<Debt>,
        /** (qarz id, to'lov sanasi). */
        payments: List<Pair<String, LocalDate>>,
        today: LocalDate,
        daysBefore: Int,
    ): List<ReminderItem> = debts.asSequence()
        .filter { !it.isClosed && it.dueDay != null }
        .mapNotNull { d ->
            val dueDate = DueDates.next(d.dueDay!!, today)
            val days = ChronoUnit.DAYS.between(today, dueDate).toInt()
            if (days != 0 && days != daysBefore) return@mapNotNull null
            val windowStart = dueDate.minusDays(PAID_WINDOW_DAYS)
            val paid = payments.any { (id, date) -> id == d.id && !date.isBefore(windowStart) && !date.isAfter(today) }
            if (paid) return@mapNotNull null
            ReminderItem(
                debtId = d.id,
                creditor = d.creditor,
                dueDate = dueDate,
                daysLeft = days,
                amountText = d.monthlyPayment.takeIf { it > 0 }?.let { MoneyFormat.withCurrency(it, d.currency) },
            )
        }
        .sortedWith(compareBy<ReminderItem> { it.daysLeft }.thenBy { it.creditor })
        .toList()

    /** Bildirishnoma sarlavhasi va matni (lotinda; ko'rsatishda tanlangan yozuvga o'giriladi). */
    fun message(items: List<ReminderItem>): Pair<String, String> {
        require(items.isNotEmpty())
        val title = if (items.size == 1) {
            "${items[0].creditor}: ${whenText(items[0].daysLeft)} to'lov kuni"
        } else {
            "${items.size} ta to'lov yaqin"
        }
        val body = items.joinToString("\n") { i ->
            val amount = i.amountText?.let { " — $it" } ?: ""
            if (items.size == 1) {
                "${UzDates.date(i.dueDate)}$amount. Kam bo'lsa ham to'lang — to'xtatmang."
            } else {
                "${i.creditor}: ${whenText(i.daysLeft)}$amount"
            }
        }
        return title to body
    }

    private fun whenText(days: Int): String = when (days) {
        0 -> "bugun"
        1 -> "ertaga"
        else -> "$days kundan keyin"
    }
}
