package uz.havoradar.engine.risk

import uz.havoradar.engine.model.Hazard
import uz.havoradar.engine.model.HazardAssessment
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Vulnerability
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

/**
 * AQSh Milliy ob-havo xizmati (NWS) issiqlik indeksi: Rothfusz regressiyasi va tuzatishlar.
 * https://www.wpc.ncep.noaa.gov/html/heatindex_equation.shtml
 */
object HeatIndex {
    fun fahrenheit(
        t: Double,
        rh: Double,
    ): Double {
        // Avval Steadman'ning oddiy formulasi; uning harorat bilan o'rtachasi 80°F dan past bo'lsa — shu natija.
        val simple = 0.5 * (t + 61.0 + (t - 68.0) * 1.2 + rh * 0.094)
        if ((simple + t) / 2 < 80.0) return simple
        var hi =
            -42.379 + 2.04901523 * t + 10.14333127 * rh - 0.22475541 * t * rh - 0.00683783 * t * t -
                0.05481717 * rh * rh + 0.00122874 * t * t * rh + 0.00085282 * t * rh * rh - 0.00000199 * t * t * rh * rh
        if (rh < 13 && t > 80 && t < 112) hi -= (13 - rh) / 4 * sqrt((17 - abs(t - 95)) / 17)
        if (rh > 85 && t > 80 && t < 87) hi += (rh - 85) / 10 * ((87 - t) / 5)
        return hi
    }

    fun celsius(
        t: Double,
        rh: Double,
    ): Double = (fahrenheit(t * 9 / 5 + 32, rh.coerceIn(0.0, 100.0)) - 32) * 5 / 9

    /**
     * Xavf ko'rsatkichi, °C: issiqlik indeksi va havo haroratining kattasi. Quruq issiqda (O'zbekiston yozi)
     * indeks havo haroratidan past chiqadi — xavf kamaytirib ko'rsatilmasligi uchun harorat olinadi.
     */
    fun feels(
        t: Double,
        rh: Double?,
    ): Double = if (rh == null) t else max(t, celsius(t, rh))
}

/**
 * Issiqlik xavfi. Ball NWS issiqlik indeksi toifalariga bog'langan:
 * 26,7°C «Ehtiyot» → 20, 32,2°C «Kuchli ehtiyot» → 40, 39,4°C «Xavf» → 60, 51,7°C «O'ta xavfli» → 80.
 * Qo'shimchalar: tropik tun (eng past harorat > 20°C, WMO ETCCDI «TR» ta'rifi) +5,
 * 3+ kun ketma-ket «Xavf» toifasi +7. Sezgir guruh — ×1,25.
 */
object HeatRisk {
    val scale = Scale(20.0 to 0.0, 26.7 to 20.0, 32.2 to 40.0, 39.4 to 60.0, 51.7 to 80.0, 58.0 to 100.0)

    const val CAUTION = 26.7
    const val EXTREME_CAUTION = 32.2
    const val DANGER = 39.4
    const val EXTREME_DANGER = 51.7
    const val TROPICAL_NIGHT = 20.0
    const val TROPICAL_BONUS = 5
    const val STREAK_DAYS = 3
    const val STREAK_BONUS = 7

    fun category(feels: Double): String =
        when {
            feels >= EXTREME_DANGER -> "NWS «O'ta xavfli» toifasi (51,7°C dan yuqori)"
            feels >= DANGER -> "NWS «Xavf» toifasi (39,4–51,7°C)"
            feels >= EXTREME_CAUTION -> "NWS «Kuchli ehtiyot» toifasi (32,2–39,4°C)"
            feels >= CAUTION -> "NWS «Ehtiyot» toifasi (26,7–32,2°C)"
            else -> "issiqlik stressi kutilmaydi"
        }

    /**
     * @param tempMin shu kundan keyingi tunning eng past harorati (bo'lmasa — kunning minimumi).
     * @param streak shu kun bilan tugaydigan ketma-ket «Xavf» toifasidagi kunlar soni.
     */
    fun assess(
        tempMax: Double,
        feelsMax: Double,
        peakHour: Int?,
        tempMin: Double?,
        streak: Int,
        profile: Set<Vulnerability>,
    ): HazardAssessment {
        val reasons = mutableListOf<String>()
        val raw = scale(feelsMax)
        var bonus = 0
        val peak = peakHour?.let { " (${hour(it)} atrofida)" }.orEmpty()
        reasons +=
            if (feelsMax - tempMax >= 1) {
                "Eng yuqori harorat ${num(tempMax)}°C, namlik bilan issiqlik indeksi ${num(feelsMax)}°C$peak — ${category(feelsMax)}."
            } else {
                "Eng yuqori harorat ${num(tempMax)}°C$peak — ${category(feelsMax)}."
            }
        if (raw >= 20) {
            if (tempMin != null && tempMin > TROPICAL_NIGHT) {
                bonus += TROPICAL_BONUS
                reasons += "Kechasi havo ${num(TROPICAL_NIGHT)}°C dan pastga tushmaydi (eng past ${num(tempMin)}°C) — organizm tunda tiklanishga ulgurmaydi."
            }
            if (streak >= STREAK_DAYS && feelsMax >= DANGER) {
                bonus += STREAK_BONUS
                reasons += "Ketma-ket $streak-kun xavfli issiqlik — ta'siri kundan-kunga jamlanadi."
            }
        }
        val base = (raw + bonus).score()
        val sensitive = profile.filter { it.heat }
        val personal = personalize(base, sensitive.isNotEmpty())
        if (sensitive.isNotEmpty() && personal > base) {
            reasons += "Profilingizda issiqqa sezgir guruh bor (${sensitive.joinToString { it.uz.lowercase() }}) — xavf 25% yuqori baholandi."
        }
        return HazardAssessment(Hazard.HEAT, base, personal, reasons, advice(RiskLevel.of(personal), profile, peakHour))
    }

    /** JSST «Heat and health» va CDC «Extreme heat» tavsiyalari asosida. */
    fun advice(
        level: RiskLevel,
        profile: Set<Vulnerability>,
        peakHour: Int?,
    ): List<String> {
        if (level == RiskLevel.CALM) return emptyList()
        val a = mutableListOf<String>()
        a += "Chanqashni kutmasdan muntazam suv iching; spirtli, ko'p kofeinli va shakarli ichimliklardan saqlaning."
        a += "Yengil, keng va och rangli kiyim kiying, boshingizni yoping."
        if (level >= RiskLevel.ADVISORY) {
            val peak = peakHour?.let { " (bugun eng issiq payt — ${hour(it)} atrofida)" }.orEmpty()
            a += "Kunning eng issiq soatlarida$peak tashqarida og'ir jismoniy ish va sportdan saqlaning, soyada bo'ling."
            a += "Kunduzi parda va darchalarni yoping, tunda havo salqinlashganda derazalarni oching."
            a += "Bolani yoki uy hayvonini to'xtab turgan mashinada bir daqiqaga ham qoldirmang."
            if (Vulnerability.OUTDOOR in profile) {
                a += "Ochiq havoda ishlasangiz: har 15–20 daqiqada suv iching, soyada dam oling; yangi ishchilar issiqqa asta-sekin moslashsin (NIOSH)."
            }
        }
        if (level >= RiskLevel.WARNING) {
            a += "Konditsionerli yoki salqin joyda vaqt o'tkazing. Ventilyatorni faqat xona 32°C dan salqin bo'lsa ishlating — undan issiqda u tana haroratini oshirishi mumkin (CDC)."
            a += "Yolg'iz yashaydigan keksa va kasal yaqinlaringizdan kuniga ikki marta xabar oling."
            a += "Ko'p dorilar issiqda suvsizlanish xavfini oshiradi: dorini o'zingiz to'xtatmang, shifokoringizdan so'rang; dorilarni issiq joyda saqlamang."
            if (Vulnerability.DIABETES in profile) a += "Insulin, glyukometr va test-chiziqlarni issiqdan va to'g'ri quyoshdan saqlang."
            a += "Issiq urishi belgilari — chalkashlik, nutq buzilishi, hushdan ketish, tutqanoq, juda yuqori tana harorati: darhol 103 ga qo'ng'iroq qiling."
        }
        return a
    }
}
