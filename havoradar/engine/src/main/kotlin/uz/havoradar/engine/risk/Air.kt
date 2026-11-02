package uz.havoradar.engine.risk

import uz.havoradar.engine.model.AirDay
import uz.havoradar.engine.model.Hazard
import uz.havoradar.engine.model.HazardAssessment
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Vulnerability
import kotlin.math.max

/**
 * Havo sifati xavfi — JSST 2021 havo sifati tavsiyalari (AQG) va oraliq maqsadlari (IT):
 * https://www.who.int/publications/i/item/9789240034228
 *
 * Har bir ifloslantiruvchi uchun ball; umumiy ball — eng yomonining bali (AQI tamoyili).
 * - PM2.5 (24 soat): AQG 15 → 20, IT-3 37,5 → 40, IT-1 75 → 60, 125,5 (AQSh EPA «Very unhealthy») → 80, 225,5 (EPA «Hazardous») → 100.
 * - PM10 (24 soat): AQG 45 → 20, IT-3 75 → 40, IT-1 150 → 60, 355 (EPA «Very unhealthy») → 80, 425 (EPA «Hazardous») → 100.
 * - Ozon (8 soatlik eng yuqori): AQG 100 → 20, IT-1 160 → 40, 240 (JSST 2005 «yuqori daraja») → 60.
 * - NO₂ (24 soat): AQG 25 → 20, IT-2 50 → 30, IT-1 120 → 45; 1 soatlik ≥ 200 (JSST 1 soatlik tavsiya) → 50.
 */
object AirRisk {
    const val PM25_AQG = 15.0
    const val PM10_AQG = 45.0
    const val O3_AQG = 100.0
    const val NO2_AQG = 25.0
    const val NO2_1H = 200.0

    val pm25 = Scale(0.0 to 0.0, 15.0 to 20.0, 37.5 to 40.0, 75.0 to 60.0, 125.5 to 80.0, 225.5 to 100.0)
    val pm10 = Scale(0.0 to 0.0, 45.0 to 20.0, 75.0 to 40.0, 150.0 to 60.0, 355.0 to 80.0, 425.0 to 100.0)
    val ozone = Scale(0.0 to 0.0, 100.0 to 20.0, 160.0 to 40.0, 240.0 to 60.0)
    val no2 = Scale(0.0 to 0.0, 25.0 to 20.0, 50.0 to 30.0, 120.0 to 45.0)

    /** Ma'lumot yetarli bo'lmasa (masalan, prognoz oxiri) — null. */
    fun assess(
        d: AirDay,
        profile: Set<Vulnerability>,
    ): HazardAssessment? {
        val parts = mutableListOf<Pair<Double, String>>()
        d.pm25Mean?.let { v ->
            parts += pm25(v) to
                if (v > PM25_AQG) {
                    "PM2.5 (mayda zarrachalar) sutkalik o'rtacha ${num(v)} µg/m³ — JSST tavsiyasidan (15) ${num(v / PM25_AQG, 1)} barobar yuqori."
                } else {
                    ""
                }
        }
        d.pm10Mean?.let { v ->
            parts += pm10(v) to if (v > PM10_AQG) "PM10 (chang zarrachalari) sutkalik o'rtacha ${num(v)} µg/m³ (JSST tavsiyasi: 45)." else ""
        }
        d.ozoneMax8h?.let { v ->
            parts += ozone(v) to if (v > O3_AQG) "Ozon 8 soatlik eng yuqori ${num(v)} µg/m³ (JSST tavsiyasi: 100) — quyoshli issiq kunlarda tushdan keyin ko'tariladi." else ""
        }
        val no2Day = d.no2Mean?.let(no2::invoke)
        val no2Hour = d.no2Max?.let { if (it >= NO2_1H) 50.0 else 0.0 }
        if (no2Day != null || no2Hour != null) {
            val reason =
                when {
                    (d.no2Max ?: 0.0) >= NO2_1H -> "Azot dioksidi soatlik ${num(d.no2Max!!)} µg/m³ — JSST 1 soatlik chegarasidan (200) yuqori."
                    (d.no2Mean ?: 0.0) > NO2_AQG -> "Azot dioksidi (transport tutuni) sutkalik o'rtacha ${num(d.no2Mean!!)} µg/m³ (JSST tavsiyasi: 25)."
                    else -> ""
                }
            parts += max(no2Day ?: 0.0, no2Hour ?: 0.0) to reason
        }
        if (d.pm25Mean == null && d.pm10Mean == null) return null

        val base = parts.maxOf { it.first }.score()
        val reasons = parts.sortedByDescending { it.first }.map { it.second }.filter { it.isNotEmpty() }.toMutableList()
        if (reasons.isEmpty()) reasons += "Barcha ko'rsatkichlar JSST tavsiyasi doirasida."
        val dusty = (d.dustShare ?: 0.0) >= 0.5 && (d.pm10Mean ?: 0.0) > PM10_AQG
        if (dusty) reasons += "Zarrachalarning ko'p qismi chang — chang bo'roni yoki shamolda chang ko'tarilishi."
        val sensitive = profile.filter { it.air }
        val personal = personalize(base, sensitive.isNotEmpty())
        if (sensitive.isNotEmpty() && personal > base) {
            reasons += "Profilingizda havo ifloslanishiga sezgir guruh bor (${sensitive.joinToString { it.uz.lowercase() }}) — xavf 25% yuqori baholandi."
        }
        return HazardAssessment(Hazard.AIR, base, personal, reasons, advice(RiskLevel.of(personal), profile, d.worstHour))
    }

    /** JSST, AQSh EPA (AirNow) va CDC tavsiyalari asosida. */
    fun advice(
        level: RiskLevel,
        profile: Set<Vulnerability>,
        worstHour: Int?,
    ): List<String> {
        if (level == RiskLevel.CALM) return emptyList()
        val a = mutableListOf<String>()
        a += "Sezgir guruhlar (bolalar, keksalar, homiladorlar, yurak va o'pka kasallari) ochiq havoda uzoq va og'ir jismoniy faollikni kamaytirsin."
        if (Vulnerability.LUNG in profile) {
            a += "Astma bo'lsa: tez yordam ingalyatorini yoningizda saqlang va shifokor bergan harakat rejasiga amal qiling."
        }
        if (level >= RiskLevel.ADVISORY) {
            val worst = worstHour?.let { " (eng ifloslangan payt — ${hour(it)} atrofida)" }.orEmpty()
            a += "Ochiq havodagi og'ir mashg'ulotlarni qisqartiring yoki yopiq joyga ko'chiring$worst."
            a += "Ifloslanish yuqori soatlarda derazalarni yopiq tuting; HEPA filtrli havo tozalagich bo'lsa, yoqing."
            a += "Uy ichida tutunni kamaytiring: chekmang, ochiq olov va tutatqi ishlatmang."
        }
        if (level >= RiskLevel.WARNING) {
            a += "Tashqariga chiqish zarur bo'lsa, yuzga zich yopishadigan N95/FFP2 respirator taqing — mato niqob mayda zarrachalardan himoya qilmaydi."
            a += "Nafas qisishi, ko'krakda og'riq, xirillash yoki yurak urishi tezlashsa — shifokorga murojaat qiling; og'ir holatda 103."
        }
        return a
    }
}
