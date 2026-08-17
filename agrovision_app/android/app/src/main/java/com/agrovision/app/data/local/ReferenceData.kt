package com.agrovision.app.data.local

/**
 * Statik ma'lumotnoma — desktop `database/seed.py` dagi REGIONS va CROPS
 * ro'yxatlarining aynan ko'chirmasi (13 viloyat × 2 tuman, 23 ekin).
 * Bu o'ylab topilgan ma'lumot emas: haqiqiy ma'muriy bo'linish va agronomik
 * ma'lumotnoma (o'rtacha suv ehtiyoji, hosildorlik, narx, tannarx).
 */
object ReferenceData {

    /**
     * Hudud xarakteristikasi. Koordinata va tumanlar ro'yxati endi
     * `assets/uz_basemap.json` + `assets/uz_districts.json` fayllaridan
     * (geoBoundaries ADM1/ADM2 asosida) olinadi — bu yerda faqat agronomik
     * koeffitsientlar saqlanadi.
     */
    data class RegionDef(
        val name: String,
        val fertility: Double,
        /** Janubiy koeffitsient — ob-havo generatorida harorat siljishi. */
        val south: Double,
    )

    val REGIONS = listOf(
        RegionDef("Toshkent", 1.05, 0.0),
        RegionDef("Toshkent shahri", 1.00, 0.0),
        RegionDef("Andijon", 1.12, 0.2),
        RegionDef("Farg'ona", 1.10, 0.2),
        RegionDef("Namangan", 1.08, 0.1),
        RegionDef("Samarqand", 1.06, 0.3),
        RegionDef("Buxoro", 0.95, 0.5),
        RegionDef("Jizzax", 0.98, 0.3),
        RegionDef("Qashqadaryo", 0.97, 0.6),
        RegionDef("Surxondaryo", 1.02, 0.9),
        RegionDef("Sirdaryo", 1.00, 0.1),
        RegionDef("Navoiy", 0.90, 0.4),
        RegionDef("Xorazm", 0.96, 0.2),
        RegionDef("Qoraqalpog'iston", 0.85, 0.0),
    )

    private val byName = REGIONS.associateBy { it.name }

    fun fertility(region: String): Double = byName[region]?.fertility ?: 1.0

    fun south(region: String): Double = byName[region]?.south ?: 0.0

    /** nomi, kategoriya, mavsum, suv(mm), hosildorlik(t/ga), narx(so'm/kg), tannarx(so'm/ga) */
    val CROPS = listOf(
        CropEntity(name = "Bug'doy", category = "don", season = "kuzgi", waterNeedMm = 450.0, baseYieldTHa = 4.5, basePricePerKg = 3000.0, costPerHa = 6_000_000.0),
        CropEntity(name = "Paxta", category = "texnik", season = "yozgi", waterNeedMm = 700.0, baseYieldTHa = 3.2, basePricePerKg = 8000.0, costPerHa = 12_000_000.0),
        CropEntity(name = "Sholi", category = "don", season = "yozgi", waterNeedMm = 1200.0, baseYieldTHa = 5.0, basePricePerKg = 7000.0, costPerHa = 10_000_000.0),
        CropEntity(name = "Makkajo'xori", category = "don", season = "yozgi", waterNeedMm = 550.0, baseYieldTHa = 7.0, basePricePerKg = 2800.0, costPerHa = 7_000_000.0),
        CropEntity(name = "Arpa", category = "don", season = "kuzgi", waterNeedMm = 400.0, baseYieldTHa = 3.8, basePricePerKg = 2500.0, costPerHa = 5_000_000.0),
        CropEntity(name = "Kartoshka", category = "sabzavot", season = "bahorgi", waterNeedMm = 500.0, baseYieldTHa = 22.0, basePricePerKg = 4000.0, costPerHa = 25_000_000.0),
        CropEntity(name = "Sabzi", category = "sabzavot", season = "bahorgi", waterNeedMm = 450.0, baseYieldTHa = 30.0, basePricePerKg = 3000.0, costPerHa = 18_000_000.0),
        CropEntity(name = "Piyoz", category = "sabzavot", season = "bahorgi", waterNeedMm = 480.0, baseYieldTHa = 28.0, basePricePerKg = 2500.0, costPerHa = 16_000_000.0),
        CropEntity(name = "Pomidor", category = "sabzavot", season = "yozgi", waterNeedMm = 600.0, baseYieldTHa = 40.0, basePricePerKg = 5000.0, costPerHa = 30_000_000.0),
        CropEntity(name = "Bodring", category = "sabzavot", season = "yozgi", waterNeedMm = 550.0, baseYieldTHa = 35.0, basePricePerKg = 4500.0, costPerHa = 26_000_000.0),
        CropEntity(name = "Qovun", category = "poliz", season = "yozgi", waterNeedMm = 400.0, baseYieldTHa = 20.0, basePricePerKg = 4000.0, costPerHa = 12_000_000.0),
        CropEntity(name = "Tarvuz", category = "poliz", season = "yozgi", waterNeedMm = 380.0, baseYieldTHa = 25.0, basePricePerKg = 2000.0, costPerHa = 10_000_000.0),
        CropEntity(name = "Uzum", category = "meva", season = "ko'p yillik", waterNeedMm = 500.0, baseYieldTHa = 12.0, basePricePerKg = 8000.0, costPerHa = 20_000_000.0),
        CropEntity(name = "Olma", category = "meva", season = "ko'p yillik", waterNeedMm = 600.0, baseYieldTHa = 18.0, basePricePerKg = 6000.0, costPerHa = 22_000_000.0),
        CropEntity(name = "O'rik", category = "meva", season = "ko'p yillik", waterNeedMm = 500.0, baseYieldTHa = 10.0, basePricePerKg = 9000.0, costPerHa = 15_000_000.0),
        CropEntity(name = "Shaftoli", category = "meva", season = "ko'p yillik", waterNeedMm = 550.0, baseYieldTHa = 12.0, basePricePerKg = 8500.0, costPerHa = 18_000_000.0),
        CropEntity(name = "Anor", category = "meva", season = "ko'p yillik", waterNeedMm = 520.0, baseYieldTHa = 14.0, basePricePerKg = 12000.0, costPerHa = 20_000_000.0),
        CropEntity(name = "Yong'oq", category = "meva", season = "ko'p yillik", waterNeedMm = 480.0, baseYieldTHa = 3.0, basePricePerKg = 35000.0, costPerHa = 14_000_000.0),
        CropEntity(name = "Soya", category = "dukkakli", season = "yozgi", waterNeedMm = 450.0, baseYieldTHa = 2.5, basePricePerKg = 6000.0, costPerHa = 6_000_000.0),
        CropEntity(name = "Kungaboqar", category = "moyli", season = "yozgi", waterNeedMm = 420.0, baseYieldTHa = 2.2, basePricePerKg = 5500.0, costPerHa = 5_000_000.0),
        CropEntity(name = "Beda", category = "ozuqa", season = "ko'p yillik", waterNeedMm = 800.0, baseYieldTHa = 9.0, basePricePerKg = 1500.0, costPerHa = 4_000_000.0),
        CropEntity(name = "Qand lavlagi", category = "texnik", season = "yozgi", waterNeedMm = 600.0, baseYieldTHa = 35.0, basePricePerKg = 1200.0, costPerHa = 15_000_000.0),
        CropEntity(name = "Sarimsoq", category = "sabzavot", season = "kuzgi", waterNeedMm = 400.0, baseYieldTHa = 8.0, basePricePerKg = 15000.0, costPerHa = 20_000_000.0),
    )

    val FIRST_NAMES = listOf(
        "Akmal", "Bobur", "Davron", "Eldor", "Farrux", "G'ayrat", "Hasan", "Islom",
        "Jasur", "Kamol", "Laziz", "Muzaffar", "Nodir", "Otabek", "Po'lat", "Qudrat",
        "Rustam", "Sardor", "Temur", "Ulug'bek", "Vali", "Xurshid", "Yusuf", "Zafar",
        "Dilnoza", "Gulnora", "Malika", "Nilufar", "Sevara", "Zulfiya",
    )

    val LAST_NAMES = listOf(
        "Karimov", "Rahimov", "Toshmatov", "Yusupov", "Aliyev", "Islomov", "Saidov",
        "Nazarov", "Ergashev", "Qodirov", "Mirzayev", "Abdullayev", "Sultonov",
        "Xolmatov", "Bekmurodov", "Jo'rayev", "Olimov", "Sharipov", "Umarov", "Vohidov",
    )
}
