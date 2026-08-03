package uz.dehqonkomakchi.app.core.util

/** All Uzbekistan viloyats (+ Republic of Karakalpakstan and Tashkent city). */
object Regions {
    val ALL: List<String> = listOf(
        "Andijon viloyati",
        "Buxoro viloyati",
        "Farg'ona viloyati",
        "Jizzax viloyati",
        "Xorazm viloyati",
        "Namangan viloyati",
        "Navoiy viloyati",
        "Qashqadaryo viloyati",
        "Qoraqalpog'iston Respublikasi",
        "Samarqand viloyati",
        "Sirdaryo viloyati",
        "Surxondaryo viloyati",
        "Toshkent viloyati",
        "Toshkent shahri",
    )

    /** A few sample districts per region as a placeholder; extend with a full dataset later. */
    fun districtsFor(region: String): List<String> = when (region) {
        "Toshkent shahri" -> listOf("Chilonzor", "Yunusobod", "Mirzo Ulug'bek", "Sergeli", "Yashnobod")
        "Toshkent viloyati" -> listOf("Bekobod", "Qibray", "Piskent", "Zangiota", "O'rta Chirchiq")
        "Andijon viloyati" -> listOf("Andijon shahri", "Asaka", "Xo'jaobod", "Shahrixon", "Baliqchi")
        "Farg'ona viloyati" -> listOf("Farg'ona shahri", "Qo'qon", "Marg'ilon", "Rishton", "Quvasoy")
        "Namangan viloyati" -> listOf("Namangan shahri", "Chust", "Pop", "Uychi", "Kosonsoy")
        "Samarqand viloyati" -> listOf("Samarqand shahri", "Kattaqo'rg'on", "Urgut", "Bulung'ur", "Jomboy")
        "Buxoro viloyati" -> listOf("Buxoro shahri", "Kogon", "G'ijduvon", "Vobkent", "Peshku")
        "Qashqadaryo viloyati" -> listOf("Qarshi", "Shahrisabz", "Kitob", "Koson", "G'uzor")
        "Surxondaryo viloyati" -> listOf("Termiz", "Denov", "Sherobod", "Boysun", "Sariosiyo")
        "Jizzax viloyati" -> listOf("Jizzax shahri", "Zomin", "Do'stlik", "G'allaorol", "Paxtakor")
        "Sirdaryo viloyati" -> listOf("Guliston", "Yangiyer", "Sirdaryo", "Boyovut", "Mirzaobod")
        "Navoiy viloyati" -> listOf("Navoiy shahri", "Zarafshon", "Karmana", "Konimex", "Uchquduq")
        "Xorazm viloyati" -> listOf("Urganch", "Xiva", "Shovot", "Xonqa", "Bog'ot")
        "Qoraqalpog'iston Respublikasi" -> listOf("Nukus", "Beruniy", "Xo'jayli", "Taxtako'pir", "Chimboy")
        else -> emptyList()
    }
}
