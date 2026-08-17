package com.agrovision.app.data.local

import android.content.Context
import androidx.room.withTransaction
import com.agrovision.app.config.Constants
import com.agrovision.app.core.Security
import com.agrovision.app.core.round1
import com.agrovision.app.core.round2
import java.time.LocalDate
import kotlin.math.PI
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max
import kotlin.math.roundToLong
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random

/**
 * Installer — desktop `database/seed.py` faylining to'liq porti.
 *
 * Ikki bosqichli:
 *  1. [bootstrap]  — har doim: 3 boshlang'ich hisob, 13 viloyat + 26 tuman,
 *     23 ekin ma'lumotnomasi, standart sozlamalar.
 *  2. [seedDemoBusinessData] — IXTIYORIY: desktop versiyasidagi kabi to'liq
 *     namuna ma'lumotlar to'plami (60 fermer, 75 xo'jalik, 140 dala,
 *     5 yillik hosildorlik + kunlik ob-havo + haftalik narx + moliya + NDVI).
 *     Foydalanuvchi birinchi ishga tushirishda tanlaydi; keyin Administrator
 *     bo'limidan qo'shish yoki tozalash mumkin.
 *
 * Barcha tasodifiylik sobit urug' (42) bilan — har bir o'rnatishda bir xil,
 * tekshiriladigan natija. Ob-havo/hosildorlik/narx/moliya/NDVI formulalari
 * desktop bilan AYNAN bir xil.
 */
object DemoSeeder {

    data class Progress(val step: String, val percent: Int)

    private const val FARMER_COUNT = 60
    private const val FIELD_COUNT = 140

    // -----------------------------------------------------------------------
    // 1-bosqich: ma'lumotnoma
    // -----------------------------------------------------------------------
    suspend fun bootstrap(db: AppDatabase, context: Context): Boolean {
        val fresh = db.userDao().count() == 0
        if (fresh) {
            db.userDao().insertAll(
                listOf(
                    UserEntity(username = "admin", fullName = "Bosh administrator", passwordHash = Security.hashPassword("admin123"), role = "admin"),
                    UserEntity(username = "menejer", fullName = "Hudud menejeri", passwordHash = Security.hashPassword("manager123"), role = "manager"),
                    UserEntity(username = "kuzatuvchi", fullName = "Tahlilchi-kuzatuvchi", passwordHash = Security.hashPassword("viewer123"), role = "viewer"),
                ),
            )
            db.cropDao().insertAll(ReferenceData.CROPS)
            Constants.DEFAULT_SETTINGS.forEach { (k, v) -> db.settingDao().upsert(SettingEntity(k, v)) }
        }
        ensureGeoReference(db, context)
        return fresh
    }

    /**
     * Hudud va tuman ma'lumotnomasini `assets` bilan moslashtiradi.
     *
     * Idempotent: yangi o'rnatishda hammasini yaratadi, eski o'rnatishda esa
     * yetishmayotgan hudud/tumanlarni qo'shadi (ilova yangilanganda foydalanuvchi
     * ma'lumotini yo'qotmasdan to'liq 199 tumanga o'tadi).
     */
    suspend fun ensureGeoReference(db: AppDatabase, context: Context) {
        val shapes = GeoAssets.regions(context)
        val refs = GeoAssets.districts(context)
        db.withTransaction {
            val existingRegions = db.geoDao().regions().associateBy { it.name }
            val missingRegions = shapes.filter { it.name !in existingRegions }
            if (missingRegions.isNotEmpty()) {
                db.geoDao().insertRegions(
                    missingRegions.map {
                        RegionEntity(
                            name = it.name, lat = it.lat, lon = it.lon,
                            fertility = ReferenceData.fertility(it.name),
                        )
                    },
                )
            }
            val regionIdByName = db.geoDao().regions().associate { it.name to it.id }
            val existingDistricts = db.geoDao().districts().map { it.regionId to it.name }.toHashSet()
            val newDistricts = refs.mapNotNull { ref ->
                val regionId = regionIdByName[ref.region] ?: return@mapNotNull null
                if (regionId to ref.name in existingDistricts) return@mapNotNull null
                DistrictEntity(regionId = regionId, name = ref.name, lat = ref.lat, lon = ref.lon)
            }
            if (newDistricts.isNotEmpty()) db.geoDao().insertDistricts(newDistricts)
        }
    }

    suspend fun hasDemoBusinessData(db: AppDatabase): Boolean = db.yieldDao().count() > 0

    // -----------------------------------------------------------------------
    // 2-bosqich: to'liq namuna ma'lumotlar (desktop analogi)
    // -----------------------------------------------------------------------
    suspend fun seedDemoBusinessData(db: AppDatabase, onProgress: (Progress) -> Unit = {}) {
        if (hasDemoBusinessData(db)) return
        val rng = Random(42)

        onProgress(Progress("Fermer va xo'jaliklar", 5))
        val allDistricts = db.geoDao().districts()
        val regions = db.geoDao().regions().associateBy { it.id }
        if (allDistricts.isEmpty()) return

        // ---- Fermerlar ----
        val farmerRows = (0 until FARMER_COUNT).map {
            val district = allDistricts[rng.nextInt(allDistricts.size)]
            FarmerEntity(
                name = "${ReferenceData.FIRST_NAMES.random(rng)} ${ReferenceData.LAST_NAMES.random(rng)}",
                phone = "+9989${rng.nextInt(0, 10)}${rng.nextInt(1_000_000, 9_999_999)}",
                districtId = district.id,
            )
        }
        val farmerIds = db.geoDao().insertFarmers(farmerRows)

        // ---- Xo'jaliklar: har fermerda 1 ta, 25% holatda 2 ta (desktop mantig'i) ----
        val farmRows = mutableListOf<FarmEntity>()
        farmerIds.forEachIndexed { index, farmerId ->
            val repeats = 1 + (if (rng.nextDouble() < 0.25) 1 else 0)
            repeat(repeats) {
                val surname = farmerRows[index].name.substringAfterLast(' ')
                farmRows += FarmEntity(
                    name = "$surname fermer xo'jaligi №${farmRows.size + 1}",
                    farmerId = farmerId,
                    districtId = farmerRows[index].districtId,
                    areaHa = 0.0,
                )
            }
        }
        val farmIds = db.geoDao().insertFarms(farmRows)
        val farmDistrict = farmIds.indices.associate { farmIds[it] to farmRows[it].districtId }

        // ---- Dalalar (poligon bilan) ----
        onProgress(Progress("Dalalar va poligonlar", 12))
        val districtById = allDistricts.associateBy { it.id }
        val fieldRows = mutableListOf<FieldEntity>()
        for (i in 0 until FIELD_COUNT) {
            val farmIndex = rng.nextInt(farmIds.size)
            val farmId = farmIds[farmIndex]
            val district = districtById.getValue(farmDistrict.getValue(farmId))
            val area = rng.nextDouble(5.0, 120.0).round1()
            val lat = district.lat + rng.nextDouble(-0.12, 0.12)
            val lon = district.lon + rng.nextDouble(-0.12, 0.12)
            fieldRows += FieldEntity(
                farmId = farmId,
                name = "Kontur-${i + 1}",
                areaHa = area,
                soilType = Constants.SOIL_TYPES.random(rng),
                lat = lat, lon = lon,
                polygon = buildPolygon(lat, lon, area, rng),
            )
        }
        val fieldIds = db.geoDao().insertFields(fieldRows)

        // Xo'jalik maydonini dalalar yig'indisiga tenglash
        val areaByFarm = mutableMapOf<Long, Double>()
        fieldRows.forEach { areaByFarm[it.farmId] = (areaByFarm[it.farmId] ?: 0.0) + it.areaHa }
        db.geoDao().updateFarms(
            farmIds.indices.map { i ->
                farmRows[i].copy(id = farmIds[i], areaHa = (areaByFarm[farmIds[i]] ?: 0.0).round1())
            },
        )

        // ---- Kunlik ob-havo (desktop `_seed_weather` formulalari) ----
        //
        // O'zbekistonda 199 tuman bor; hammasi uchun 5 yillik KUNLIK ob-havo
        // ~400 000 qator bo'ladi va telefonda seed'ni sekinlashtiradi. Namuna
        // to'plamiga faqat KERAKLI tumanlar kiradi: xo'jaliklar joylashgan
        // tumanlar + har viloyatdan bittadan (viloyat kesimidagi tahlil uchun).
        // Qolgan tumanlar ob-havosi Ob-havo ekranida internetdan olinadi.
        val usedDistrictIds = farmRows.map { it.districtId }.toHashSet()
        allDistricts.groupBy { it.regionId }.forEach { (_, group) ->
            if (group.none { it.id in usedDistrictIds }) usedDistrictIds += group.first().id
        }
        val districts = allDistricts.filter { it.id in usedDistrictIds }
        onProgress(Progress("Ob-havo tarixi (kunlik)", 20))
        val start = LocalDate.of(Constants.HISTORY_START_YEAR, 1, 1)
        val end = LocalDate.now()
        val totalDays = (end.toEpochDay() - start.toEpochDay()).toInt() + 1
        // (districtId, year) -> mavsumiy statistika
        val seasonStats = HashMap<Pair<Long, Int>, Triple<Double, Double, Double>>()

        districts.forEachIndexed { districtIndex, district ->
            val regionName = regions[district.regionId]?.name ?: ""
            val south = ReferenceData.south(regionName)
            val isJizzax = regionName == "Jizzax"
            val rows = ArrayList<WeatherRecordEntity>(totalDays)
            val seasonAcc = HashMap<Int, MutableList<Triple<Double, Double, Double>>>()

            for (offset in 0 until totalDays) {
                val date = start.plusDays(offset.toLong())
                val doy = date.dayOfYear.toDouble()
                val month = date.monthValue
                val seasonal = 14.0 + 14.5 * sin((doy - 105) / 365.0 * 2 * PI)
                val tMax = seasonal + 6 + south * 3 + rng.gaussian(0.0, 2.5)
                val tMin = seasonal - 5 + south * 2 + rng.gaussian(0.0, 2.0)
                val rainProb = 0.22 + 0.16 * cos((doy - 60) / 365.0 * 2 * PI)
                var rain = if (rng.nextDouble() < rainProb) rng.exponential(4.5) else 0.0
                if (month in 6..8) rain *= 0.25
                if (isJizzax && date.year == 2024) rain *= 0.45   // 2024 qurg'oqchilik stsenariysi
                val humidity = (78 - (tMax - 10) * 1.3 + rng.gaussian(0.0, 6.0)).coerceIn(15.0, 98.0)

                rows += WeatherRecordEntity(
                    districtId = district.id, epochDay = date.toEpochDay(),
                    tMin = tMin.round1(), tMax = tMax.round1(),
                    precipitationMm = rain.round1(), humidity = humidity.round1(),
                    source = "demo",
                )
                if (month in Constants.SEASON_MONTHS) {
                    seasonAcc.getOrPut(date.year) { mutableListOf() } += Triple(rain, (tMax + tMin) / 2, humidity)
                }
            }
            rows.chunked(4000).forEach { db.weatherDao().insertAll(it) }
            seasonAcc.forEach { (year, values) ->
                seasonStats[district.id to year] = Triple(
                    values.sumOf { it.first },
                    values.sumOf { it.second } / values.size,
                    values.sumOf { it.third } / values.size,
                )
            }
            if (districtIndex % 5 == 0) {
                onProgress(Progress("Ob-havo tarixi (kunlik)", 20 + districtIndex * 25 / districts.size))
            }
        }

        // ---- Hosildorlik + sug'orish (desktop `_seed_yields_and_irrigation`) ----
        onProgress(Progress("Hosildorlik va sug'orish", 50))
        val crops = db.cropDao().all()
        val wheatIndex = crops.indexOfFirst { it.name == "Bug'doy" }.let { if (it >= 0) it else 0 }
        val cottonIndex = crops.indexOfFirst { it.name == "Paxta" }.let { if (it >= 0) it else minOf(1, crops.size - 1) }
        val yieldRows = mutableListOf<YieldRecordEntity>()
        val irrigationRows = mutableListOf<IrrigationRecordEntity>()
        // fieldId -> year -> ratio (NDVI generatori uchun)
        val ratios = HashMap<Pair<Long, Int>, Double>()
        // farmId -> year -> [(cropId, productionT, areaHa)] (moliya uchun)
        val farmYearProduction = HashMap<Pair<Long, Int>, MutableList<Triple<Long, Double, Double>>>()

        fieldRows.forEachIndexed { index, field ->
            val fieldId = fieldIds[index]
            val districtId = farmDistrict.getValue(field.farmId)
            val regionName = regions[districtById.getValue(districtId).regionId]?.name ?: ""
            val fertility = regions[districtById.getValue(districtId).regionId]?.fertility ?: 1.0
            val isJizzax = regionName == "Jizzax"

            // Rotatsiya: bittasi strategik ekin (bug'doy yoki paxta) + 2 tasodifiy.
            // MUHIM: `crops` alifbo tartibida keladi, shuning uchun strategik ekin
            // indeks bo'yicha emas, NOMI bo'yicha tanlanadi (desktop bilan bir xil natija).
            val strategic = if (rng.nextInt(0, 2) == 0) wheatIndex else cottonIndex
            val pool = mutableListOf(strategic)
            pool += crops.indices.filter { it != wheatIndex && it != cottonIndex }
                .shuffled(rng).take(2)
            val rotationOffset = rng.nextInt(0, 3)

            Constants.HISTORY_YEARS.forEach { year ->
                val crop = crops[pool[(year + rotationOffset) % 3]]
                val season = seasonStats[districtId to year] ?: Triple(120.0, 24.0, 50.0)
                var coverage = rng.nextDouble(0.45, 0.85)
                if (year == 2024 && isJizzax) coverage *= 0.65   // kanal cheklovlari
                val irrigationMm = crop.waterNeedMm * coverage
                val supply = season.first + irrigationMm
                val ratio = (supply / crop.waterNeedMm).coerceIn(0.35, 1.15)
                val heatPenalty = 1.0 - max(0.0, season.second - 27.0) * 0.03
                val yieldT = max(
                    0.2,
                    crop.baseYieldTHa * ratio * fertility * heatPenalty * (1 + rng.gaussian(0.0, 0.08)),
                )
                val production = (yieldT * field.areaHa).round1()
                ratios[fieldId to year] = ratio
                yieldRows += YieldRecordEntity(
                    fieldId = fieldId, cropId = crop.id, year = year,
                    areaHa = field.areaHa, yieldTHa = yieldT.round2(), productionT = production,
                )
                farmYearProduction.getOrPut(field.farmId to year) { mutableListOf() } +=
                    Triple(crop.id, production, field.areaHa)

                // 1 mm/ga = 10 m³; mavsum 5 oyga taqsimlanadi
                val totalM3 = irrigationMm * 10 * field.areaHa
                val method = Constants.IRRIGATION_METHODS.random(rng)
                for (month in 4..8) {
                    irrigationRows += IrrigationRecordEntity(
                        fieldId = fieldId,
                        epochDay = LocalDate.of(year, month, rng.nextInt(1, 28)).toEpochDay(),
                        waterM3 = totalM3.div(5).roundToLong().toDouble(),
                        method = method,
                    )
                }
            }
        }
        yieldRows.chunked(2000).forEach { db.yieldDao().insertAll(it) }
        irrigationRows.chunked(2000).forEach { db.irrigationDao().insertAll(it) }

        // ---- Bozor narxlari (haftalik, inflyatsiya + mavsumiylik) ----
        onProgress(Progress("Bozor narxlari", 68))
        val priceRows = mutableListOf<MarketPriceEntity>()
        val yearlyPriceAcc = HashMap<Pair<Long, Int>, MutableList<Double>>()
        crops.forEach { crop ->
            val phase = rng.nextDouble(0.0, 2 * PI)
            var day = LocalDate.of(Constants.HISTORY_START_YEAR, 1, 4)
            while (!day.isAfter(end)) {
                val yearsPassed = day.year - Constants.HISTORY_START_YEAR
                val seasonal = 1 + 0.13 * sin(2 * PI * day.dayOfYear / 365.0 + phase)
                var price = crop.basePricePerKg * (1 + 0.09 * yearsPassed) * seasonal
                price *= (1 + rng.gaussian(0.0, 0.04))
                priceRows += MarketPriceEntity(
                    cropId = crop.id, epochDay = day.toEpochDay(),
                    pricePerKg = price.roundToLong().toDouble(),
                    marketName = "Milliy bozor", source = "demo",
                )
                yearlyPriceAcc.getOrPut(crop.id to day.year) { mutableListOf() } += price
                day = day.plusDays(7)
            }
        }
        priceRows.chunked(3000).forEach { db.marketDao().insertAll(it) }
        val priceIndex = yearlyPriceAcc.mapValues { (_, values) -> values.sum() / values.size }

        // ---- Moliya (daromad/xarajat/kredit/subsidiya) ----
        onProgress(Progress("Moliyaviy yozuvlar", 80))
        val cropById = crops.associateBy { it.id }
        val financeRows = mutableListOf<FinanceRecordEntity>()
        farmIds.forEach { farmId ->
            Constants.HISTORY_YEARS.forEach { year ->
                val items = farmYearProduction[farmId to year] ?: return@forEach
                val expense = items.sumOf { (cropId, _, areaHa) ->
                    areaHa * (cropById[cropId]?.costPerHa ?: 0.0)
                } * rng.nextDouble(Constants.EXPENSE_FACTOR_MIN, Constants.EXPENSE_FACTOR_MAX)
                val income = items.sumOf { (cropId, production, _) ->
                    val price = priceIndex[cropId to year] ?: (cropById[cropId]?.basePricePerKg ?: 0.0)
                    production * 1000 * price
                } * Constants.WHOLESALE_FACTOR * rng.nextDouble(0.93, 1.05)

                financeRows += FinanceRecordEntity(
                    farmId = farmId, year = year, category = "expense",
                    amount = expense.roundToLong().toDouble(), note = "Yillik ishlab chiqarish xarajatlari",
                )
                financeRows += FinanceRecordEntity(
                    farmId = farmId, year = year, category = "income",
                    amount = income.roundToLong().toDouble(), note = "Mahsulot sotuvidan tushum",
                )
                if (rng.nextDouble() < 0.35) {
                    financeRows += FinanceRecordEntity(
                        farmId = farmId, year = year, category = "credit",
                        amount = (expense * 0.3).roundToLong().toDouble(), note = "Agrobank imtiyozli krediti",
                    )
                }
                if (rng.nextDouble() < 0.4) {
                    financeRows += FinanceRecordEntity(
                        farmId = farmId, year = year, category = "subsidy",
                        amount = (expense * 0.1).roundToLong().toDouble(), note = "Davlat subsidiyasi",
                    )
                }
            }
        }
        financeRows.chunked(2000).forEach { db.financeDao().insertAll(it) }

        // ---- NDVI/EVI (ikki haftalik, so'nggi ~30 oy) ----
        onProgress(Progress("Vegetatsiya indekslari (NDVI)", 90))
        val ndviRows = mutableListOf<SatelliteIndexEntity>()
        val lastHistoryYear = Constants.HISTORY_YEARS.last()
        fieldIds.forEach { fieldId ->
            var day = end.minusDays(900)
            while (!day.isAfter(end)) {
                val doy = day.dayOfYear.toDouble()
                val yearRatio = ratios[fieldId to minOf(day.year, lastHistoryYear)] ?: 0.8
                val peak = 0.30 + 0.42 * yearRatio
                val bell = exp(-((doy - 165) / 72.0) * ((doy - 165) / 72.0))
                val ndvi = (0.14 + peak * bell + rng.gaussian(0.0, 0.03)).coerceIn(0.05, 0.95)
                val evi = (ndvi * 0.85 + rng.gaussian(0.0, 0.02)).coerceIn(0.03, 0.90)
                ndviRows += SatelliteIndexEntity(
                    fieldId = fieldId, epochDay = day.toEpochDay(),
                    ndvi = ndvi.round3v(), evi = evi.round3v(), source = "demo",
                )
                day = day.plusDays(14)
            }
        }
        ndviRows.chunked(3000).forEach { db.satelliteDao().insertAll(it) }

        onProgress(Progress("Tayyor", 100))
    }

    /** Poligon: maydon o'lchamiga mos to'rtburchak, kichik tebranish bilan. */
    private fun buildPolygon(lat: Double, lon: Double, areaHa: Double, rng: Random): String {
        val half = max(0.0012, sqrt(areaHa) * 0.00045)
        fun jitter() = rng.gaussian(0.0, half * 0.15)
        val points = listOf(
            (lon - half + jitter()) to (lat - half + jitter()),
            (lon + half + jitter()) to (lat - half + jitter()),
            (lon + half + jitter()) to (lat + half + jitter()),
            (lon - half + jitter()) to (lat + half + jitter()),
        )
        return points.joinToString(";") { (x, y) ->
            "${(x * 1e6).roundToLong() / 1e6},${(y * 1e6).roundToLong() / 1e6}"
        }
    }

    // ---- numpy generatorlarining ekvivalentlari ----
    private fun Random.gaussian(mean: Double = 0.0, std: Double = 1.0): Double {
        val u1 = nextDouble().coerceAtLeast(1e-12)
        val u2 = nextDouble()
        return mean + std * sqrt(-2.0 * ln(u1)) * cos(2.0 * PI * u2)
    }

    private fun Random.exponential(scale: Double): Double =
        -ln(1.0 - nextDouble().coerceAtMost(0.999999)) * scale

    private fun <T> List<T>.random(rng: Random): T = this[rng.nextInt(size)]

    private fun Double.round3v(): Double = (this * 1000).roundToLong() / 1000.0
}
