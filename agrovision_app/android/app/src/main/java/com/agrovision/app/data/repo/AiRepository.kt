package com.agrovision.app.data.repo

import com.agrovision.app.core.Fmt
import com.agrovision.app.core.math.Stats
import com.agrovision.app.data.local.CropDao
import com.agrovision.app.data.local.GeoDao
import com.agrovision.app.data.local.YearYieldRow
import java.time.LocalDate
import javax.inject.Inject
import javax.inject.Singleton

/** AI javobi: matn + ixtiyoriy jadval (sarlavhalar + qatorlar). */
data class AiAnswer(
    val text: String,
    val tableHeaders: List<String> = emptyList(),
    val tableRows: List<List<String>> = emptyList(),
)

private data class QueryContext(
    var intent: String = "stats",
    var region: String? = null,
    var regionId: Long? = null,
    var crop: String? = null,
    var cropId: Long? = null,
    var year: Int? = null,
)

/**
 * Offlayn tabiiy-til so'rov dvigateli — desktop `ai/engine.py` ning to'liq
 * porti: 8 niyat (why · forecast · price · recommend · weather · compare ·
 * finance · stats), viloyat/ekin/yil entity ekstraktsiyasi va dalillarga
 * asoslangan javob. Hech qanday tarmoq yoki LLM chaqiruvi yo'q.
 */
@Singleton
class AiRepository @Inject constructor(
    private val geoDao: GeoDao,
    private val cropDao: CropDao,
    private val kpiRepository: KpiRepository,
    private val weatherRepository: WeatherRepository,
    private val marketRepository: MarketRepository,
    private val financeRepository: FinanceRepository,
    private val irrigationRepository: IrrigationRepository,
    private val mlRepository: MlRepository,
) {
    companion object {
        val SAMPLE_QUESTIONS = listOf(
            "Jizzaxda bug'doy hosili nima uchun pasaydi?",
            "Kelgusi yil paxta hosildorligi prognozi qanday?",
            "Pomidor narxi qancha?",
            "Samarqand uchun qaysi ekin tavsiya etiladi?",
            "2024-yil Jizzax ob-havosi qanday bo'lgan?",
            "Viloyatlarni solishtirib bering",
            "Daromad va foyda qanday?",
        )

        private val INTENT_KEYWORDS = linkedMapOf(
            "why" to listOf("nega", "nima uchun", "sabab", "pasaydi", "kamaydi", "tushdi"),
            "forecast" to listOf("prognoz", "bashorat", "kelgusi", "keyingi yil", "qancha bo'ladi"),
            "price" to listOf("narx", "narxi", "qancha turadi", "bozor"),
            "recommend" to listOf("tavsiya", "qaysi ekin", "nima eksam", "eng foydali", "maslahat"),
            "weather" to listOf("ob-havo", "harorat", "yog'in", "yomg'ir", "namlik", "iqlim"),
            "compare" to listOf("solishtir", "taqqosla", "farqi", "qaysi yaxshi"),
            "finance" to listOf("daromad", "foyda", "zarar", "roi", "xarajat", "kredit", "subsidiya"),
        )
    }

    suspend fun ask(question: String): AiAnswer = try {
        val context = parse(normalize(question))
        when (context.intent) {
            "why" -> answerWhy(context)
            "forecast" -> answerForecast(context)
            "price" -> answerPrice(context)
            "recommend" -> answerRecommend(context)
            "weather" -> answerWeather(context)
            "compare" -> answerCompare(context)
            "finance" -> answerFinance(context)
            else -> answerStats(context)
        }
    } catch (e: Exception) {
        AiAnswer("So'rovni tahlil qilishda xatolik yuz berdi. Savolni boshqacha ifodalab ko'ring.")
    }

    private fun normalize(text: String): String {
        var result = text.lowercase()
        for (apostrophe in listOf('‘', '’', 'ʻ', 'ʼ', '`', '´')) {
            result = result.replace(apostrophe, '\'')
        }
        return result.replace(Regex("\\s+"), " ").trim()
    }

    private suspend fun parse(text: String): QueryContext {
        val context = QueryContext()
        for ((intent, keywords) in INTENT_KEYWORDS) {
            if (keywords.any { text.contains(it) }) {
                context.intent = intent
                break
            }
        }
        geoDao.regions().firstOrNull { text.contains(normalize(it.name).take(5)) }?.let {
            context.region = it.name
            context.regionId = it.id
        }
        cropDao.all().firstOrNull { text.contains(normalize(it.name).take(5)) }?.let {
            context.crop = it.name
            context.cropId = it.id
        }
        Regex("(20\\d{2})").find(text)?.groupValues?.getOrNull(1)?.toIntOrNull()?.let { context.year = it }
        return context
    }

    private suspend fun series(context: QueryContext): List<YearYieldRow> =
        kpiRepository.filteredTrend(context.regionId, context.cropId)

    private fun scopeLabel(context: QueryContext): String {
        val parts = listOfNotNull(context.region, context.crop?.lowercase())
        return if (parts.isEmpty()) "respublika bo'yicha" else parts.joinToString(" — ")
    }

    private fun yieldTable(rows: List<YearYieldRow>) =
        listOf("Yil", "t/ga", "Ishlab chiqarish (t)") to
            rows.map { listOf(it.year.toString(), Fmt.dec(it.avgYield, 2), Fmt.num(it.production, 0)) }

    // ---- 1) NEGA pasaydi (dalilli tahlil) ----
    private suspend fun answerWhy(context: QueryContext): AiAnswer {
        val rows = series(context)
        if (rows.size < 2) return AiAnswer("Tahlil uchun yetarli tarixiy ma'lumot topilmadi.")
        val targetYear = context.year ?: rows.last().year
        val current = rows.firstOrNull { it.year == targetYear }?.avgYield
        val previous = rows.firstOrNull { it.year == targetYear - 1 }?.avgYield
        if (current == null || previous == null) {
            val (headers, table) = yieldTable(rows)
            return AiAnswer("$targetYear-yil uchun ma'lumot topilmadi.", headers, table)
        }
        val change = Stats.percentChange(previous, current)
        val scope = scopeLabel(context).replaceFirstChar { it.uppercase() }
        val reasons = mutableListOf<String>()

        context.region?.let { region ->
            val thisSeason = weatherRepository.seasonSummary(region, targetYear)
            val history = (targetYear - 4 until targetYear).mapNotNull {
                weatherRepository.seasonSummary(region, it)
            }
            if (thisSeason != null && history.isNotEmpty()) {
                val meanPrecip = history.map { it.precip }.average()
                val precipChange = Stats.percentChange(meanPrecip, thisSeason.precip)
                if (precipChange < -15) {
                    reasons += "mavsumiy yog'ingarchilik o'rtachadan ${Fmt.dec(-precipChange, 0)}% " +
                        "kam bo'ldi (${Fmt.dec(thisSeason.precip, 0)} mm)"
                }
                val meanTemp = history.map { it.tAvg }.average()
                if (thisSeason.tAvg - meanTemp > 1) {
                    reasons += "o'rtacha harorat ${Fmt.dec(thisSeason.tAvg - meanTemp, 1)}°C yuqori bo'ldi"
                }
            }
            context.regionId?.let { regionId ->
                val water = irrigationRepository.regionYearTotals().filter { it.regionId == regionId }
                val currentWater = water.firstOrNull { it.year == targetYear }?.waterM3
                val pastWater = water.filter { it.year < targetYear }.map { it.waterM3 }
                if (currentWater != null && pastWater.isNotEmpty()) {
                    val waterChange = Stats.percentChange(pastWater.average(), currentWater)
                    if (waterChange < -10) {
                        reasons += "sug'orish hajmi o'rtachadan ${Fmt.dec(-waterChange, 0)}% kamaydi"
                    }
                }
            }
        }

        val text = if (change < 0) {
            buildString {
                append("$scope: $targetYear-yilda o'rtacha hosildorlik ${Fmt.dec(previous, 2)} t/ga dan ")
                append("${Fmt.dec(current, 2)} t/ga ga tushdi (${Fmt.signedPercent(change)}).\n\n")
                append(
                    if (reasons.isNotEmpty()) {
                        "Asosiy sabablar (ma'lumotlar tahlili):\n" + reasons.joinToString("\n") { "• $it;" }
                    } else {
                        "Ob-havo va sug'orish ko'rsatkichlarida keskin og'ish aniqlanmadi — " +
                            "pasayish agrotexnika yoki navlar bilan bog'liq bo'lishi mumkin."
                    },
                )
            }
        } else {
            "$scope: $targetYear-yilda hosildorlik aslida pasaymagan — " +
                "${Fmt.dec(previous, 2)} dan ${Fmt.dec(current, 2)} t/ga ga o'zgardi (${Fmt.signedPercent(change)})."
        }
        val (headers, table) = yieldTable(rows)
        return AiAnswer(text, headers, table)
    }

    // ---- 2) Prognoz ----
    private suspend fun answerForecast(context: QueryContext): AiAnswer {
        val rows = series(context)
        if (rows.size < 3) return AiAnswer("Prognoz uchun kamida 3 yillik ma'lumot kerak.")
        val values = rows.map { it.avgYield }
        val forecast = Stats.linearForecast(values, 1)
        val nextYear = rows.last().year + 1
        val text = "${scopeLabel(context).replaceFirstChar { it.uppercase() }} uchun $nextYear-yil prognozi: " +
            "o'rtacha hosildorlik ≈ ${Fmt.dec(forecast.point[0], 2)} t/ga " +
            "(ishonch oralig'i: ${Fmt.dec(forecast.lower[0], 2)} – ${Fmt.dec(forecast.upper[0], 2)} t/ga).\n" +
            "So'nggi trend: ${Fmt.dec(values.first(), 2)} → ${Fmt.dec(values.last(), 2)} t/ga."
        val (headers, table) = yieldTable(rows)
        return AiAnswer(text, headers, table)
    }

    // ---- 3) Narx ----
    private suspend fun answerPrice(context: QueryContext): AiAnswer {
        val cropId = context.cropId
        if (cropId == null) {
            val latest = marketRepository.latestPrices()
            if (latest.isEmpty()) return AiAnswer("Bozor narxlari hali kiritilmagan.")
            return AiAnswer(
                "Barcha ekinlar bo'yicha so'nggi bozor narxlari:",
                listOf("Ekin", "Narx (so'm/kg)", "30 kun"),
                latest.map { listOf(it.crop, Fmt.num(it.price, 0), Fmt.signedPercent(it.change30d)) },
            )
        }
        val history = marketRepository.history(cropId, 365)
        if (history.isEmpty()) return AiAnswer("${context.crop}: narx tarixi topilmadi.")
        val prices = history.map { it.price }
        val forecast = Stats.linearForecast(prices, 4)
        val text = "${context.crop}: joriy narx ${Fmt.num(prices.last(), 0)} so'm/kg " +
            "(yillik o'rtacha ${Fmt.num(Stats.mean(prices), 0)} so'm/kg).\n" +
            "1 oylik prognoz: ${Fmt.num(forecast.point.last(), 0)} so'm/kg atrofida " +
            "(${Fmt.num(forecast.lower.last(), 0)} – ${Fmt.num(forecast.upper.last(), 0)})."
        return AiAnswer(
            text,
            listOf("Sana", "Narx (so'm/kg)"),
            history.takeLast(10).map { listOf(Fmt.date(it.epochDay), Fmt.num(it.price, 0)) },
        )
    }

    // ---- 4) Ekin tavsiyasi (ML) ----
    private suspend fun answerRecommend(context: QueryContext): AiAnswer {
        val regionName = context.region ?: geoDao.regions().firstOrNull()?.name
            ?: return AiAnswer("Viloyatlar ma'lumotnomasi bo'sh.")
        val region = geoDao.regionByName(regionName)
            ?: return AiAnswer("Viloyat topilmadi — savolda viloyat nomini keltiring.")
        val year = kpiRepository.latestYear()
        val season = weatherRepository.seasonSummary(regionName, year) ?: SeasonSummary(150.0, 24.0, 55.0)
        val recommendations = mlRepository.recommendCrops(region.id, season.precip, season.tAvg, region.fertility)
        if (recommendations.isEmpty()) {
            return AiAnswer("$regionName uchun tavsiya berish uchun ma'lumot yetarli emas (ML modeli o'qitilmagan).")
        }
        val lines = recommendations.mapIndexed { i, item ->
            "${i + 1}. ${item.crop} (model ishonchi: ${Fmt.dec(item.confidence, 1)}%)"
        }
        return AiAnswer(
            "$regionName viloyati uchun ML modeli tavsiya qilgan eng foydali ekinlar " +
                "(tarixiy foyda va iqlim asosida):\n" + lines.joinToString("\n"),
            listOf("Ekin", "Ishonch"),
            recommendations.map { listOf(it.crop, "${Fmt.dec(it.confidence, 1)}%") },
        )
    }

    // ---- 5) Ob-havo ----
    private suspend fun answerWeather(context: QueryContext): AiAnswer {
        val regionName = context.region ?: geoDao.regions().firstOrNull()?.name
            ?: return AiAnswer("Viloyatlar ma'lumotnomasi bo'sh.")
        val year = context.year ?: kpiRepository.latestYear()
        val season = weatherRepository.seasonSummary(regionName, year)
            ?: return AiAnswer("$regionName bo'yicha $year-yil ob-havo ma'lumoti topilmadi.")
        return AiAnswer(
            "$regionName viloyati, $year-yil vegetatsiya mavsumi (aprel–sentabr):\n" +
                "• Yog'ingarchilik: ${Fmt.dec(season.precip, 0)} mm\n" +
                "• O'rtacha harorat: ${Fmt.dec(season.tAvg, 1)}°C\n" +
                "• O'rtacha namlik: ${Fmt.dec(season.humidity, 0)}%",
        )
    }

    // ---- 6) Taqqoslash ----
    private suspend fun answerCompare(context: QueryContext): AiAnswer {
        val year = context.year ?: kpiRepository.latestYear()
        val rows = kpiRepository.byRegion(year)
        if (rows.isEmpty()) return AiAnswer("$year-yil uchun hosildorlik ma'lumotlari topilmadi.")
        val best = rows.first()
        val worst = rows.last()
        return AiAnswer(
            "$year-yil viloyatlar taqqoslamasi:\n" +
                "• Eng yuqori ishlab chiqarish: ${best.region} (${Fmt.num(best.production, 0)} t)\n" +
                "• Eng past: ${worst.region} (${Fmt.num(worst.production, 0)} t)",
            listOf("Hudud", "t/ga", "Ishlab chiqarish (t)"),
            rows.map { listOf(it.region, Fmt.dec(it.avgYield, 2), Fmt.num(it.production, 0)) },
        )
    }

    // ---- 7) Moliya ----
    private suspend fun answerFinance(context: QueryContext): AiAnswer {
        val summary = financeRepository.yearlySummary()
        if (summary.isEmpty()) return AiAnswer("Moliya yozuvlari hali kiritilmagan.")
        val year = context.year ?: kpiRepository.latestYear()
        val record = summary.firstOrNull { it.year == year }
            ?: return AiAnswer("$year-yil moliya ma'lumotlari topilmadi.")
        return AiAnswer(
            "$year-yil moliyaviy natijalar (platforma bo'yicha):\n" +
                "• Daromad: ${Fmt.money(record.income)} so'm\n" +
                "• Xarajat: ${Fmt.money(record.expense)} so'm\n" +
                "• Sof foyda: ${Fmt.money(record.profit)} so'm (ROI: ${Fmt.dec(record.roi, 1)}%)\n" +
                "• Kreditlar: ${Fmt.money(record.credit)}, subsidiyalar: ${Fmt.money(record.subsidy)} so'm",
            listOf("Yil", "Daromad", "Xarajat", "Foyda", "ROI"),
            summary.map {
                listOf(
                    it.year.toString(), Fmt.money(it.income), Fmt.money(it.expense),
                    Fmt.money(it.profit), "${Fmt.dec(it.roi, 1)}%",
                )
            },
        )
    }

    // ---- 8) Umumiy statistika ----
    private suspend fun answerStats(context: QueryContext): AiAnswer {
        val kpi = kpiRepository.compute(context.year)
        val rows = series(context)
        val extra = if (rows.isNotEmpty() && (context.region != null || context.crop != null)) {
            val last = rows.last()
            "\n${scopeLabel(context).replaceFirstChar { it.uppercase() }}: ${last.year}-yilda o'rtacha " +
                "hosildorlik ${Fmt.dec(last.avgYield, 2)} t/ga, ishlab chiqarish ${Fmt.num(last.production, 0)} t."
        } else {
            ""
        }
        val text = "${kpi.year}-yil umumiy ko'rsatkichlari:\n" +
            "• Yer maydoni: ${Fmt.num(kpi.totalAreaHa, 0)} ga | Fermerlar: ${kpi.farmers} | " +
            "Xo'jaliklar: ${kpi.farms} | Dalalar: ${kpi.fields}\n" +
            "• O'rtacha hosildorlik: ${Fmt.dec(kpi.avgYieldTHa, 2)} t/ga, jami ${Fmt.num(kpi.productionT, 0)} t\n" +
            "• Moliyaviy natija: foyda ${Fmt.money(kpi.profit)} so'm (ROI ${Fmt.dec(kpi.roiPercent, 1)}%)\n" +
            "• O'rtacha NDVI (so'nggi 60 kun): ${Fmt.dec(kpi.avgNdvi, 3)}" + extra
        return if (rows.isEmpty()) {
            AiAnswer(text)
        } else {
            val (headers, table) = yieldTable(rows)
            AiAnswer(text, headers, table)
        }
    }
}
