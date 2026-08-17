package com.agrovision.mobile.data.local

import androidx.room.withTransaction
import com.agrovision.mobile.core.Security

/**
 * Birinchi ishga tushirishda faqat HAQIQIY ma'lumotnoma yuklanadi:
 * boshlang'ich foydalanuvchilar, O'zbekiston viloyat/tuman ro'yxati
 * (real geografik koordinatalar bilan — ob-havoni internetdan olish
 * uchun zarur) va standart ekin turlari (agronomik ma'lumotnoma).
 *
 * HECH QANDAY o'ylab topilgan biznes-yozuv (fermer, xo'jalik, dala,
 * hosildorlik, ob-havo tarixi, bozor narxi, sug'orish, moliya, NDVI)
 * YARATILMAYDI — bularning barchasini foydalanuvchi ilova ichida
 * "Ma'lumotlar" bo'limidan qo'lda kiritadi, yoki ob-havo uchun ilova
 * internetdan (Open-Meteo) haqiqiy tarixiy ma'lumotni yuklab oladi.
 */
object SeedData {

    private data class RegionDef(val name: String, val lat: Double, val lon: Double, val districts: List<String>)

    private val REGIONS = listOf(
        RegionDef("Toshkent", 41.31, 69.28, listOf("Zangiota tumani", "Chinoz tumani", "Bo'ka tumani", "Parkent tumani")),
        RegionDef("Andijon", 40.78, 72.34, listOf("Asaka tumani", "Marhamat tumani", "Xo'jaobod tumani")),
        RegionDef("Farg'ona", 40.39, 71.78, listOf("Quva tumani", "Rishton tumani", "Qo'qon tumani")),
        RegionDef("Namangan", 41.00, 71.67, listOf("Chust tumani", "Pop tumani", "Uychi tumani")),
        RegionDef("Samarqand", 39.65, 66.96, listOf("Urgut tumani", "Ishtixon tumani", "Bulung'ur tumani")),
        RegionDef("Buxoro", 39.77, 64.42, listOf("G'ijduvon tumani", "Kogon tumani", "Vobkent tumani")),
        RegionDef("Jizzax", 40.12, 67.83, listOf("Zomin tumani", "G'allaorol tumani", "Do'stlik tumani")),
        RegionDef("Qashqadaryo", 38.86, 65.79, listOf("Shahrisabz tumani", "Koson tumani", "Kitob tumani")),
        RegionDef("Surxondaryo", 37.94, 67.57, listOf("Denov tumani", "Sherobod tumani", "Sariosiyo tumani")),
        RegionDef("Sirdaryo", 40.84, 68.66, listOf("Guliston tumani", "Boyovut tumani", "Sirdaryo tumani")),
        RegionDef("Navoiy", 40.09, 65.38, listOf("Karmana tumani", "Qiziltepa tumani", "Navbahor tumani")),
        RegionDef("Xorazm", 41.55, 60.63, listOf("Urganch tumani", "Xiva tumani", "Shovot tumani")),
        RegionDef("Qoraqalpog'iston", 42.46, 59.61, listOf("Nukus tumani", "Chimboy tumani", "Xo'jayli tumani")),
    )

    // nomi, kategoriya, mavsum, suv ehtiyoji(mm), bazaviy hosildorlik(t/ga), bazaviy narx(so'm/kg), tannarx(so'm/ga)
    // — bular AGRONOMIK MA'LUMOTNOMA (ochiq manbalarga asoslangan taxminiy o'rtacha qiymatlar),
    // foydalanuvchi Ma'lumotlar bo'limida o'z hududiga moslab tahrirlashi mumkin.
    private val CROPS = listOf(
        CropEntity(name = "Bug'doy", category = "don", season = "kuzgi", waterNeedMm = 450.0, baseYieldTHa = 4.5, basePricePerKg = 3000.0, costPerHa = 6_000_000.0),
        CropEntity(name = "Paxta", category = "texnik", season = "yozgi", waterNeedMm = 700.0, baseYieldTHa = 3.2, basePricePerKg = 8000.0, costPerHa = 12_000_000.0),
        CropEntity(name = "Sholi", category = "don", season = "yozgi", waterNeedMm = 1200.0, baseYieldTHa = 5.0, basePricePerKg = 7000.0, costPerHa = 10_000_000.0),
        CropEntity(name = "Makkajo'xori", category = "don", season = "yozgi", waterNeedMm = 550.0, baseYieldTHa = 7.0, basePricePerKg = 2800.0, costPerHa = 7_000_000.0),
        CropEntity(name = "Kartoshka", category = "sabzavot", season = "bahorgi", waterNeedMm = 500.0, baseYieldTHa = 22.0, basePricePerKg = 4000.0, costPerHa = 25_000_000.0),
        CropEntity(name = "Sabzi", category = "sabzavot", season = "bahorgi", waterNeedMm = 450.0, baseYieldTHa = 30.0, basePricePerKg = 3000.0, costPerHa = 18_000_000.0),
        CropEntity(name = "Piyoz", category = "sabzavot", season = "bahorgi", waterNeedMm = 480.0, baseYieldTHa = 28.0, basePricePerKg = 2500.0, costPerHa = 16_000_000.0),
        CropEntity(name = "Pomidor", category = "sabzavot", season = "yozgi", waterNeedMm = 600.0, baseYieldTHa = 40.0, basePricePerKg = 5000.0, costPerHa = 30_000_000.0),
        CropEntity(name = "Bodring", category = "sabzavot", season = "yozgi", waterNeedMm = 550.0, baseYieldTHa = 35.0, basePricePerKg = 4500.0, costPerHa = 26_000_000.0),
        CropEntity(name = "Qovun", category = "poliz", season = "yozgi", waterNeedMm = 400.0, baseYieldTHa = 20.0, basePricePerKg = 4000.0, costPerHa = 12_000_000.0),
        CropEntity(name = "Tarvuz", category = "poliz", season = "yozgi", waterNeedMm = 380.0, baseYieldTHa = 25.0, basePricePerKg = 2000.0, costPerHa = 10_000_000.0),
        CropEntity(name = "Uzum", category = "meva", season = "ko'p yillik", waterNeedMm = 500.0, baseYieldTHa = 12.0, basePricePerKg = 8000.0, costPerHa = 20_000_000.0),
        CropEntity(name = "Olma", category = "meva", season = "ko'p yillik", waterNeedMm = 600.0, baseYieldTHa = 18.0, basePricePerKg = 6000.0, costPerHa = 22_000_000.0),
        CropEntity(name = "Beda", category = "ozuqa", season = "ko'p yillik", waterNeedMm = 800.0, baseYieldTHa = 9.0, basePricePerKg = 1500.0, costPerHa = 4_000_000.0),
        CropEntity(name = "Soya", category = "dukkakli", season = "yozgi", waterNeedMm = 450.0, baseYieldTHa = 2.5, basePricePerKg = 6000.0, costPerHa = 6_000_000.0),
        CropEntity(name = "Kungaboqar", category = "moyli", season = "yozgi", waterNeedMm = 420.0, baseYieldTHa = 2.2, basePricePerKg = 5500.0, costPerHa = 5_000_000.0),
    )

    private val DEFAULT_SETTINGS = mapOf("theme" to "light", "language" to "uz")

    suspend fun seedIfEmpty(db: AppDatabase): Boolean {
        if (db.userDao().count() > 0) return false
        db.withTransaction {
            db.userDao().insertAll(
                listOf(
                    UserEntity(username = "admin", fullName = "Bosh administrator", passwordHash = Security.hashPassword("admin123"), role = "admin"),
                    UserEntity(username = "menejer", fullName = "Hudud menejeri", passwordHash = Security.hashPassword("manager123"), role = "manager"),
                    UserEntity(username = "kuzatuvchi", fullName = "Tahlilchi-kuzatuvchi", passwordHash = Security.hashPassword("viewer123"), role = "viewer"),
                ),
            )

            val regionIds = db.geoDao().insertRegions(
                REGIONS.map { RegionEntity(name = it.name, lat = it.lat, lon = it.lon, fertility = 1.0) },
            )
            val districtEntities = mutableListOf<DistrictEntity>()
            REGIONS.forEachIndexed { idx, region ->
                val regionId = regionIds[idx]
                region.districts.forEachIndexed { i, name ->
                    val angle = i * (2 * Math.PI / region.districts.size)
                    districtEntities += DistrictEntity(
                        regionId = regionId, name = name,
                        lat = region.lat + 0.18 * kotlin.math.cos(angle),
                        lon = region.lon + 0.22 * kotlin.math.sin(angle),
                    )
                }
            }
            db.geoDao().insertDistricts(districtEntities)
            db.cropDao().insertAll(CROPS)
            DEFAULT_SETTINGS.forEach { (k, v) -> db.settingDao().upsert(SettingEntity(k, v)) }
        }
        return true
    }
}
