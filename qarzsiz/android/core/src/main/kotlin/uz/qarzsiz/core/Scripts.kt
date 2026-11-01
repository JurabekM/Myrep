package uz.qarzsiz.core

/**
 * 3-qadam: kreditor bilan halol gaplashish matnlari.
 * Qoida: qarzni tan olish, vaziyatni ochiq aytish, aniq summa va sana taklif qilish.
 * Hissiy bosim («o'lib qolaman») va bajarib bo'lmaydigan va'dalar ishlatilmaydi.
 */
object Scripts {
    data class Proposal(
        val creditor: String,
        val amountText: String,
        val monthlyText: String,
        /** «2026-yil dekabr» kabi boshlanish vaqti, bo'sh bo'lsa — «keyingi oydan». */
        val startText: String,
        /** Necha oyda yopilishi (taxminiy), `null` bo'lsa aytilmaydi. */
        val months: Int?,
    )

    /** Foizsiz (B) qarz egasiga — qo'ng'iroq yoki xabar uchun. */
    fun personal(p: Proposal): String {
        val name = p.creditor.trim().ifEmpty { "aka" }
        val start = p.startText.trim().ifEmpty { "keyingi oydan" }
        val horizon = p.months?.let { " Shu tartibda taxminan $it oyda to'liq yopaman." } ?: ""
        return buildString {
            append("Assalomu alaykum, $name.\n\n")
            append("Sizdan ${p.amountText} qarz olganimni unutganim yo'q va albatta qaytaraman. ")
            append("Ochig'ini aytay: hozir bir nechta qarzim bor, ularni reja bilan yopishga kirishdim — ")
            append("hammasini ro'yxat qilib, oylik daromadimni taqsimlab chiqdim.\n\n")
            append("Taklifim: $start boshlab har oy ${p.monthlyText} qaytarib boraman.$horizon\n\n")
            append("Iltimos, shu tartibga rozi bo'lsangiz. Har oy to'lagan kunim sizga o'zim xabar beraman, ")
            append("vaziyat o'zgarsa — oldindan aytaman, yashirmayman.\n\n")
            append("Sabr qilganingiz uchun rahmat.")
        }
    }

    /** Bank yoki tashkilotga restrukturizatsiya (muddatni uzaytirish) so'rovi — ariza namunasi. */
    fun restructuring(
        bank: String,
        fullName: String,
        contractText: String,
        reason: String,
        monthlyText: String,
    ): String {
        val who = fullName.trim().ifEmpty { "[F.I.Sh.]" }
        val contract = contractText.trim().ifEmpty { "[shartnoma raqami va sanasi]" }
        val why = reason.trim().ifEmpty { "daromadim kamaygani" }
        return buildString {
            append("${bank.trim().ifEmpty { "[Bank nomi]" }} rahbariyatiga\n")
            append("mijoz $who dan\n\n")
            append("ARIZA\n\n")
            append("Men $contract asosida kredit olganman va shu kungacha to'lovlarni amalga oshirib kelganman. ")
            append("Hozirda $why sababli oylik to'lovni to'liq hajmda to'lash qiyinlashdi.\n\n")
            append("To'lovni to'xtatmaslik va muddatni o'tkazib yubormaslik uchun ")
            append("kreditni qayta ko'rib chiqishni (to'lov muddatini uzaytirish yoki imtiyozli davr berishni) so'rayman. ")
            append("Men har oy $monthlyText to'lay olaman.\n\n")
            append("Daromadimni tasdiqlovchi hujjatlarni taqdim etishga tayyorman.\n\n")
            append("Sana: ____________    Imzo: ____________")
        }
    }

    /** Gaplashishdan oldin eslatmalar. */
    val talkTips: List<String> = listOf(
        "Qarzni tan oling — kreditor eng avvalo shuni eshitmoqchi.",
        "Aniq summa va aniq sana ayting. «Topganimda beraman» — reja emas.",
        "Bajara olmaydigan va'da bermang. Kichik, lekin har oy — kattadan, lekin bir marta yaxshiroq.",
        "Kelishuvni yozib qo'ying (xabar, tilxat) va ilovadagi qarz kartochkasiga ham yozing.",
        "Har oy to'lagan kuni o'zingiz xabar bering — ishonch shu bilan tiklanadi.",
    )
}
