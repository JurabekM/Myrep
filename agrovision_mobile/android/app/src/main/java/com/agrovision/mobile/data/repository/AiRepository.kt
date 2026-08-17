package com.agrovision.mobile.data.repository

import com.agrovision.mobile.core.AnalyticsMath
import com.agrovision.mobile.data.local.CropDao
import com.agrovision.mobile.data.local.GeoDao
import com.agrovision.mobile.data.local.YieldDao
import javax.inject.Inject
import javax.inject.Singleton

data class AiAnswer(val text: String, val yieldSeries: List<Pair<Int, Double>>? = null)

private data class QueryContext(
    var intent: String = "stats",
    var region: String? = null,
    var crop: String? = null,
    var year: Int? = null,
)

/**
 * Offline tabiiy-til so'rov dvigateli — desktop ai/engine.py'ning Kotlin porti.
 * Hech qanday tarmoq yoki LLM chaqiruvi yo'q: kalit-so'z asosida niyatni
 * aniqlaydi, mahalliy Room bazasidan dalillarni yig'adi va o'zbek tilida
 * tushuntirilgan javob quradi.
 */
@Singleton
class AiRepository @Inject constructor(
    private val geoDao: GeoDao,
    private val cropDao: CropDao,
    private val yieldDao: YieldDao,
    private val weatherRepository: WeatherRepository,
    private val kpiRepository: KpiRepository,
    private val marketRepository: MarketRepository,
    private val financeRepository: FinanceRepository,
    private val mlRepository: MlRepository,
) {
    private val intentKeywords = mapOf(
        "why" to listOf("nega", "nima uchun", "sabab", "pasaydi", "kamaydi", "tushdi"),
        "forecast" to listOf("prognoz", "bashorat", "kelgusi", "keyingi yil", "qancha bo'ladi"),
        "price" to listOf("narx", "narxi", "qancha turadi", "bozor"),
        "recommend" to listOf("tavsiya", "qaysi ekin", "nima eksam", "eng foydali", "maslahat"),
        "weather" to listOf("ob-havo", "harorat", "yog'in", "yomg'ir", "namlik", "iqlim"),
        "compare" to listOf("solishtir", "taqqosla", "farqi", "qaysi yaxshi"),
        "finance" to listOf("daromad", "foyda", "zarar", "roi", "xarajat", "kredit", "subsidiya"),
    )

    suspend fun ask(question: String): AiAnswer {
        val normalized = normalize(question)
        val context = parse(normalized)
        return try {
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
    }

    private fun normalize(text: String): String {
        var t = text.lowercase()
        for (ch in listOf("‘", "’", "ʻ", "ʼ", "`", "´")) t = t.replace(ch, "'")
        return t.replace(Regex("\\s+"), " ").trim()
    }

    private suspend fun parse(text: String): QueryContext {
        val context = QueryContext()
        for ((intent, keywords) in intentKeywords) {
            if (keywords.any { text.contains(it) }) {
                context.intent = intent
                break
            }
        }
        geoDao.regions().firstOrNull { region -> normalize(region.name).take(5).let { text.contains(it) } }
            ?.let { context.region = it.name }
        cropDao.all().firstOrNull { crop -> normalize(crop.name).take(5).let { text.contains(it) } }
            ?.let { context.crop = it.name }
        Regex("(20\\d{2})").find(text)?.groupValues?.get(1)?.toIntOrNull()?.let { context.year = it }
        return context
    }

    private suspend fun yieldSeries(region: String?, crop: String?): List<Pair<Int, Double>> {
        val allYears = yieldDao.years()
        val results = mutableListOf<Pair<Int, Double>>()
        for (year in allYears) {
            val rows = yieldDao.byRegion(year)
            val row = rows.firstOrNull { region == null || it.region == region }
            if (row != null) results += year to row.avgYield
        }
        return results
    }

    private fun scopeLabel(context: QueryContext): String {
        val parts = listOfNotNull(context.region, context.crop?.lowercase())
        return if (parts.isEmpty()) "respublika bo'yicha" else parts.joinToString(" — ")
    }

    private suspend fun answerWhy(context: QueryContext): AiAnswer {
        val series = yieldSeries(context.region, context.crop)
        if (series.size < 2) return AiAnswer("Tahlil uchun yetarli tarixiy ma'lumot topilmadi.")
        val targetYear = context.year ?: series.last().first
        val current = series.firstOrNull { it.first == targetYear }?.second
        val previous = series.firstOrNull { it.first == targetYear - 1 }?.second
        if (current == null || previous == null) return AiAnswer("$targetYear-yil uchun ma'lumot topilmadi.")
        val change = AnalyticsMath.percentChange(previous, current)
        val scope = scopeLabel(context)

        val reasons = mutableListOf<String>()
        if (context.region != null) {
            val thisSeason = weatherRepository.seasonSummary(context.region!!, targetYear)
            val history = (targetYear - 4 until targetYear).mapNotNull {
                weatherRepository.seasonSummary(context.region!!, it)
            }
            if (thisSeason != null && history.isNotEmpty()) {
                val meanPrecip = history.map { it.precip }.average()
                val precipChange = AnalyticsMath.percentChange(meanPrecip, thisSeason.precip)
                if (precipChange < -15) {
                    reasons += "mavsumiy yog'ingarchilik o'rtachadan ${"%.0f".format(-precipChange)}% kam bo'ldi (${"%.0f".format(thisSeason.precip)} mm)"
                }
                val meanTemp = history.map { it.tAvg }.average()
                if (thisSeason.tAvg - meanTemp > 1) {
                    reasons += "o'rtacha harorat ${"%.1f".format(thisSeason.tAvg - meanTemp)}°C yuqori bo'ldi"
                }
            }
        }

        val builder = StringBuilder()
        if (change < 0) {
            builder.append(
                "${scope.replaceFirstChar { it.uppercase() }}: $targetYear-yilda o'rtacha hosildorlik " +
                    "${"%.2f".format(previous)} t/ga dan ${"%.2f".format(current)} t/ga ga tushdi (${"%.1f".format(change)}%).\n\n",
            )
            builder.append(
                if (reasons.isNotEmpty()) "Asosiy sabablar (ma'lumotlar tahlili):\n" + reasons.joinToString("\n") { "• $it;" }
                else "Ob-havo ko'rsatkichlarida keskin og'ish aniqlanmadi — pasayish agrotexnika yoki navlar bilan bog'liq bo'lishi mumkin.",
            )
        } else {
            builder.append(
                "${scope.replaceFirstChar { it.uppercase() }}: $targetYear-yilda hosildorlik aslida pasaymagan — " +
                    "${"%.2f".format(previous)} dan ${"%.2f".format(current)} t/ga ga o'zgardi (${"%.1f".format(change)}%).",
            )
        }
        return AiAnswer(builder.toString(), series)
    }

    private suspend fun answerForecast(context: QueryContext): AiAnswer {
        val series = yieldSeries(context.region, context.crop)
        if (series.size < 3) return AiAnswer("Prognoz uchun kamida 3 yillik ma'lumot kerak.")
        val values = series.map { it.second }
        val (forecast, lower, upper) = AnalyticsMath.linearForecast(values, 1)
        val nextYear = series.last().first + 1
        val text = "${scopeLabel(context).replaceFirstChar { it.uppercase() }} uchun $nextYear-yil prognozi: " +
            "o'rtacha hosildorlik ≈ ${"%.2f".format(forecast[0])} t/ga " +
            "(ishonch oralig'i: ${"%.2f".format(lower[0])} – ${"%.2f".format(upper[0])} t/ga).\n" +
            "So'nggi trend: ${"%.2f".format(values.first())} → ${"%.2f".format(values.last())} t/ga."
        return AiAnswer(text, series)
    }

    private suspend fun answerPrice(context: QueryContext): AiAnswer {
        val latest = marketRepository.latestPrices()
        if (latest.isEmpty()) return AiAnswer("Bozor narxlari topilmadi.")
        val lines = latest.take(8).joinToString("\n") { "• ${it.crop}: ${"%.0f".format(it.price)} so'm/kg" }
        return AiAnswer("So'nggi bozor narxlari:\n$lines")
    }

    private suspend fun answerRecommend(context: QueryContext): AiAnswer {
        val region = context.region ?: "Toshkent"
        val year = kpiRepository.latestYear()
        val recommendations = mlRepository.recommendCrops(region, year)
        if (recommendations.isEmpty()) return AiAnswer("$region uchun tavsiya berish uchun ma'lumot yetarli emas.")
        val lines = recommendations.mapIndexed { i, r -> "${i + 1}. ${r.crop} (ishonch: ${r.confidencePercent}%)" }
            .joinToString("\n")
        return AiAnswer("$region viloyati uchun tarixiy foydaga asoslangan eng yaxshi ekinlar:\n$lines")
    }

    private suspend fun answerWeather(context: QueryContext): AiAnswer {
        val region = context.region ?: "Toshkent"
        val year = context.year ?: kpiRepository.latestYear()
        val season = weatherRepository.seasonSummary(region, year)
            ?: return AiAnswer("$region bo'yicha $year-yil ob-havo ma'lumoti topilmadi.")
        val text = "$region viloyati, $year-yil vegetatsiya mavsumi (aprel–sentabr):\n" +
            "• Yog'ingarchilik: ${"%.0f".format(season.precip)} mm\n" +
            "• O'rtacha harorat: ${"%.1f".format(season.tAvg)}°C\n" +
            "• O'rtacha namlik: ${"%.0f".format(season.humidity)}%"
        return AiAnswer(text)
    }

    private suspend fun answerCompare(context: QueryContext): AiAnswer {
        val year = context.year ?: kpiRepository.latestYear()
        val table = kpiRepository.byRegion(year)
        if (table.isEmpty()) return AiAnswer("Ma'lumot topilmadi.")
        val best = table.first()
        val worst = table.last()
        val text = "$year-yil viloyatlar taqqoslamasi:\n" +
            "• Eng yuqori ishlab chiqarish: ${best.region} (${"%.0f".format(best.production)} t)\n" +
            "• Eng past: ${worst.region} (${"%.0f".format(worst.production)} t)"
        return AiAnswer(text)
    }

    private suspend fun answerFinance(context: QueryContext): AiAnswer {
        val year = context.year ?: kpiRepository.latestYear()
        val record = financeRepository.yearlySummary().firstOrNull { it.year == year }
            ?: return AiAnswer("$year-yil moliya ma'lumotlari topilmadi.")
        val text = "$year-yil moliyaviy natijalar:\n" +
            "• Daromad: ${"%.1f".format(record.income / 1e9)} mlrd so'm\n" +
            "• Xarajat: ${"%.1f".format(record.expense / 1e9)} mlrd so'm\n" +
            "• Sof foyda: ${"%.1f".format(record.profit / 1e9)} mlrd so'm (ROI: ${record.roi}%)"
        return AiAnswer(text)
    }

    private suspend fun answerStats(context: QueryContext): AiAnswer {
        val kpi = kpiRepository.compute(context.year)
        val text = "${kpi.year}-yil umumiy ko'rsatkichlari:\n" +
            "• Yer maydoni: ${"%.0f".format(kpi.totalAreaHa)} ga | Fermerlar: ${kpi.farmers} | " +
            "Xo'jaliklar: ${kpi.farms} | Dalalar: ${kpi.fields}\n" +
            "• O'rtacha hosildorlik: ${kpi.avgYieldTHa} t/ga, jami ${"%.0f".format(kpi.productionT)} t\n" +
            "• Moliyaviy natija: foyda ${"%.1f".format(kpi.profit / 1e9)} mlrd so'm (ROI ${kpi.roiPercent}%)\n" +
            "• O'rtacha NDVI: ${kpi.avgNdvi}"
        return AiAnswer(text)
    }
}
