package uz.epiradar.engine.risk

import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.Assessment
import uz.epiradar.engine.model.OutbreakEvent
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.SignalFlag
import java.time.Duration
import java.time.Instant
import kotlin.math.min
import kotlin.math.pow
import kotlin.math.roundToInt

/**
 * Bir xil kasallik va kesishgan mamlakatlar bo'yicha [WINDOW_DAYS] ichidagi xabarlarni bitta
 * avj olish hodisasiga birlashtiradi (turli manbalar bitta voqeani tasdiqlashi — «korroboratsiya»).
 */
object EventClusterer {
    const val WINDOW_DAYS = 60L

    data class Cluster(
        val diseaseId: String,
        val signals: MutableList<Signal>,
        val countries: MutableSet<String>,
    ) {
        val last: Instant get() = signals.maxOf { it.publishedAt }
    }

    fun cluster(signals: List<Signal>): List<Cluster> {
        val clusters = mutableListOf<Cluster>()
        for (s in signals.sortedBy { it.publishedAt }) {
            val matches =
                clusters.filter { c ->
                    c.diseaseId == s.diseaseId &&
                        s.diseaseId != DiseaseCatalog.OTHER &&
                        Duration.between(c.last, s.publishedAt).toDays() <= WINDOW_DAYS &&
                        (
                            c.countries.any { it in s.countries } ||
                                // Mamlakatsiz umumiy obzor (masalan, "Dengue worldwide overview") — shu kasallikning
                                // mamlakatsiz klasteriga qo'shiladi.
                                (c.countries.isEmpty() && s.countries.isEmpty())
                        )
                }
            if (matches.isEmpty()) {
                clusters += Cluster(s.diseaseId, mutableListOf(s), s.countries.toMutableSet())
                continue
            }
            // Yangi xabar ikki alohida klasterni bog'lasa (DRC + Keniya), ular bitta hodisaga qo'shiladi.
            val target = matches.first()
            for (other in matches.drop(1)) {
                target.signals += other.signals
                target.countries += other.countries
                clusters.remove(other)
            }
            target.signals += s
            target.countries += s.countries
        }
        return clusters
    }
}

/**
 * Tushuntiriladigan xavf bahosi (0..100).
 *
 * ```
 * intensivlik I = min(1, 0.6·H + 0.6·ΣF + T)
 *   H  — qo'zg'atuvchi xavfi (diseases.json, 0..1)
 *   ΣF — epidemiologik belgilar yig'indisi (noma'lum sabab, odamdan odamga, ko'p mamlakat...; ≤ 0.6)
 *   T  — CDC sayohat darajasi qo'shimchasi (L4 0.30, L3 0.20, L2 0.10)
 * global = 100 · I · ishonchlilik · tasdiq · yangilik
 *   yangilik  = 0.5^(oxirgi yangilanishdan beri kun / 30)
 *   tasdiq    = 1 manba 0.9, 2 manba 1.0, 3+ manba 1.1
 * shaxsiy = global · P',  P' = P + (1 − P)·tarqalish
 *   P — mamlakatlar yaqinligi (bir mamlakat 1, chegaradosh 0.9, ... uzoq 0.25)
 *   tarqalish — pandemik salohiyat (yuqori 0.35, o'rta 0.15) · (odamdan odamga/olib kirilgan bo'lsa 1, aks holda 0.5)
 * ```
 */
class RiskScorer(
    private val catalog: DiseaseCatalog,
    private val countries: Countries,
) {
    fun assess(
        cluster: EventClusterer.Cluster,
        userCountry: String,
        now: Instant,
    ): OutbreakEvent {
        val disease = catalog[cluster.diseaseId]
        val signals = cluster.signals.sortedByDescending { it.publishedAt }
        val flags = signals.flatMap { it.flags }.toMutableSet()
        val countryList = orderedCountries(signals)
        if (countryList.size >= 3) flags += SignalFlag.MULTI_COUNTRY
        val travelLevel = signals.mapNotNull { it.travelLevel }.maxOrNull()
        val first = signals.minOf { it.publishedAt }
        val last = signals.maxOf { it.publishedAt }

        val flagSum = min(MAX_FLAG_SUM, flags.sumOf { it.weight })
        val travelBoost =
            when (travelLevel) {
                4 -> 0.30
                3 -> 0.20
                2 -> 0.10
                else -> 0.0
            }
        val intensity = min(1.0, 0.6 * disease.hazard + 0.6 * flagSum + travelBoost)
        val reliability = signals.maxOf { it.source.reliability }
        val sources = signals.map { it.source }.distinct().size
        val corroboration =
            when {
                sources >= 3 -> 1.1
                sources == 2 -> 1.0
                else -> 0.9
            }
        val ageDays = Duration.between(last, now).toHours().coerceAtLeast(0) / 24.0
        val recency = 0.5.pow(ageDays / HALF_LIFE_DAYS)
        val global = (100 * intensity * reliability * corroboration * recency).coerceIn(0.0, 100.0)

        val proximity =
            if (countryList.isEmpty()) {
                NO_COUNTRY_PROXIMITY
            } else {
                countryList.maxOf { countries.proximity(userCountry, it) }
            }
        val spreadFlags = SignalFlag.HUMAN_TO_HUMAN in flags || SignalFlag.IMPORTED in flags || SignalFlag.MULTI_COUNTRY in flags
        val spread = disease.pandemic.spread * (if (spreadFlags) 1.0 else 0.5)
        val effective = proximity + (1 - proximity) * spread
        // Masofa to'g'ridan-to'g'ri ko'paytiriladi: uzoqdagi kontakt orqali yuqadigan kasallik (Ebola)
        // «Xavf» emas, «Ogohlik»/«Kuzatuv» bo'lib qoladi; havo orqali yuqadiganlarni `spread` yaqinlashtiradi.
        val personal = (global * effective).coerceIn(0.0, 100.0)

        val distance =
            countryList.mapNotNull { countries.distanceKm(userCountry, it) }.minOrNull()
                ?.let { if (userCountry in countryList) 0 else it }

        val reasons =
            buildList {
                add("Qo'zg'atuvchi xavfi: ${hazardWord(disease.hazard)} (${disease.name})")
                add("Pandemik salohiyat: ${disease.pandemic.uz.lowercase()}")
                flags.sortedByDescending { it.weight }.forEach { add(it.uz) }
                travelLevel?.let { add("CDC sayohat darajasi: $it — ${travelWord(it)}") }
                when {
                    userCountry in countryList -> add("Sizning mamlakatingizda qayd etilgan")
                    countryList.any { countries.areNeighbors(userCountry, it) } -> add("Qo'shni mamlakatda qayd etilgan")
                    distance != null -> add("Sizdan taxminan ${formatKm(distance)} km uzoqlikda")
                    else -> add("Aniq hudud ko'rsatilmagan (global obzor)")
                }
                add(if (sources > 1) "$sources ta mustaqil manba tasdiqlagan" else "Bitta manba xabari")
                add("Oxirgi yangilanish: ${agoText(ageDays)}")
            }

        val names = countryList.take(3).map { countries.nameUz(it) }
        val more = if (countryList.size > 3) " va yana ${countryList.size - 3} ta" else ""
        val title =
            when {
                disease.id == DiseaseCatalog.OTHER -> signals.first().title
                names.isEmpty() -> disease.name
                else -> "${disease.name} — ${names.joinToString(", ")}$more"
            }

        return OutbreakEvent(
            id = "${cluster.diseaseId}:${cluster.signals.minByOrNull { it.publishedAt }!!.id}",
            diseaseId = disease.id,
            title = title,
            countries = countryList,
            signals = signals,
            firstSeen = first,
            lastUpdated = last,
            flags = flags,
            travelLevel = travelLevel,
            assessment = Assessment(global.roundToInt(), personal.roundToInt(), distance, reasons),
        )
    }

    /** Ko'p uchragan mamlakat oldinda (eng so'nggi xabardagi tartib saqlanadi). */
    private fun orderedCountries(signals: List<Signal>): List<String> {
        val freq = signals.flatMap { it.countries }.groupingBy { it }.eachCount()
        val order = signals.flatMap { it.countries }.distinct()
        return order.sortedByDescending { freq[it] ?: 0 }
    }

    companion object {
        const val HALF_LIFE_DAYS = 30.0
        const val MAX_FLAG_SUM = 0.6
        const val NO_COUNTRY_PROXIMITY = 0.4

        /**
         * Umumiy daraja: eng xavfli hodisa + keyingi ikkitasining kichik hissasi (bir vaqtdagi bir nechta
         * tahdid), lekin qo'shimcha [MAX_COMBINE_BONUS] dan oshmaydi — umumiy daraja eng xavfli hodisadan
         * keskin yuqori ko'rinmasligi uchun.
         */
        fun combine(scores: List<Int>): Int {
            val top = scores.sortedDescending()
            val bonus = min(MAX_COMBINE_BONUS, 0.1 * top.getOrElse(1) { 0 } + 0.05 * top.getOrElse(2) { 0 })
            return (top.getOrElse(0) { 0 } + bonus).toInt().coerceIn(0, 100)
        }

        const val MAX_COMBINE_BONUS = 8.0

        private fun hazardWord(h: Double) =
            when {
                h >= 0.8 -> "juda yuqori"
                h >= 0.6 -> "yuqori"
                h >= 0.4 -> "o'rtacha"
                else -> "past"
            }

        private fun travelWord(level: Int) =
            when (level) {
                4 -> "barcha safarlardan voz keching"
                3 -> "zaruriy bo'lmagan safarlarni qoldiring"
                2 -> "kuchaytirilgan ehtiyot choralari"
                else -> "odatiy ehtiyot choralari"
            }

        fun agoText(days: Double): String =
            when {
                days < 1 -> "bugun"
                days < 2 -> "kecha"
                days < 31 -> "${days.toInt()} kun oldin"
                else -> "${(days / 30).toInt()} oy oldin"
            }

        /** Yuzlikkacha yaxlitlangan, minglar bo'sh joy bilan: 6234 → "6 200" (UI ham shunday yaxlitlaydi). */
        fun formatKm(km: Int): String = ((km + 50) / 100 * 100).toString().reversed().chunked(3).joinToString(" ").reversed()
    }
}
