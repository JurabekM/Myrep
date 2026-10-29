package uz.mpay.wallet.app

import uz.mpay.core.Txn

/**
 * Fon sinxronlashida yangi tranzaksiyalarni aniqlaydi (bildirishnoma uchun). Har karta uchun oxirgi
 * ko'rilgan yozuv ID'si saqlanadi; sahifa yangilari birinchi keladi.
 *
 * * birinchi marta (belgi yo'q) — bildirishnoma yo'q, faqat belgi qo'yiladi (eski tarix bilan to'ldirmaslik);
 * * belgi sahifada topilmasa (juda ko'p yangi yozuv) — sahifadagi hammasi yangi, eng ko'pi [MAX].
 */
object TxnWatcher {
    const val MAX = 5

    data class Result(val fresh: List<Txn>, val marker: String?)

    fun diff(page: List<Txn>, marker: String?): Result {
        val newest = page.firstOrNull()?.id ?: marker
        if (marker == null) return Result(emptyList(), newest)
        val idx = page.indexOfFirst { it.id == marker }
        val fresh = if (idx >= 0) page.take(idx) else page
        return Result(fresh.take(MAX), newest)
    }
}
