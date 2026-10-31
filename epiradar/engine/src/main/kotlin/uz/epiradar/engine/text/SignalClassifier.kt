package uz.epiradar.engine.text

import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.SignalFlag

/**
 * Inglizcha rasmiy xabar matnidan kasallik, mamlakatlar va epidemiologik belgilarni ajratadi.
 * Qoidaga asoslangan (ML emas) — natija tushuntiriladigan va tekshiriladigan bo'lishi uchun.
 */
class SignalClassifier(
    private val catalog: DiseaseCatalog,
    private val countries: Countries,
) {
    private data class Pattern(
        val regex: Regex,
        val length: Int,
    )

    private val diseasePatterns: List<Pair<String, Pattern>> =
        catalog.all.flatMap { d -> d.aliases.map { a -> d.id to Pattern(boundary(a, ignoreCase = true), a.length) } }

    private val countryPatterns: List<Triple<String, Regex, Int>> =
        countries.all
            .flatMap { c ->
                c.aliases.map { a ->
                    // Faqat bosh harfli qisqa yozuvlar (DRC, USA, UK) katta-kichik harfga sezgir.
                    val caseSensitive = a.length <= 4 && a == a.uppercase()
                    Triple(c.iso3, boundary(a, ignoreCase = !caseSensitive), a.length)
                }
            }.sortedByDescending { it.third }

    private val flagPatterns: Map<SignalFlag, List<Regex>> =
        mapOf(
            SignalFlag.PHEIC to listOf("public health emergency of international concern", "pheic", "pandemic emergency"),
            SignalFlag.UNKNOWN_ETIOLOGY to
                listOf(
                    "undetermined etiology", "unknown etiology", "unknown aetiology", "undetermined aetiology",
                    "undiagnosed", "unexplained", "unidentified", "unknown cause", "mystery illness", "disease x",
                ),
            SignalFlag.NOVEL_PATHOGEN to
                listOf("novel", "new strain", "new variant", "variant influenza", "reassortant", "never before", "new subtype"),
            SignalFlag.HUMAN_TO_HUMAN to
                listOf(
                    "human-to-human", "human to human", "person-to-person", "person to person", "secondary transmission",
                    "community transmission", "local transmission", "nosocomial", "sustained transmission",
                ),
            SignalFlag.MULTI_COUNTRY to
                listOf("multi-country", "multicountry", "several countries", "multiple countries", "neighbouring countries", "neighboring countries"),
            SignalFlag.IMPORTED to
                listOf("imported", "travel-associated", "travel history", "returning travel", "travel-related"),
            SignalFlag.HEALTHCARE_WORKERS to
                listOf("health worker", "healthcare worker", "health-care worker", "health care worker", "medical staff"),
            SignalFlag.ESCALATING to
                listOf("expanded", "expanding", "spreading", "surge", "rapid increase", "rising", "escalat", "increasing number", "increase in cases", "spread to"),
            SignalFlag.FIRST_DETECTION to
                listOf("first case", "first confirmed", "first reported", "first time", "first detection", "first-ever"),
            SignalFlag.CLUSTER to listOf("cluster"),
            SignalFlag.DEATHS to listOf("death", "deaths", "died", "fatal", "fatalities"),
        ).mapValues { (_, words) -> words.map { prefixBoundary(it) } }

    private val negations = Regex("\\b(no|not|without|absence of|no evidence of|none)\\b[^.;]{0,30}$", RegexOption.IGNORE_CASE)

    /** Eng aniq (eng uzun mos kelgan iborali) kasallik; topilmasa — "other". */
    fun disease(text: String): String {
        var best: String? = null
        var bestLen = -1
        var bestHazard = -1.0
        for ((id, p) in diseasePatterns) {
            if (p.length < bestLen) continue
            if (!p.regex.containsMatchIn(text)) continue
            val hazard = catalog[id].hazard
            if (p.length > bestLen || hazard > bestHazard) {
                best = id
                bestLen = p.length
                bestHazard = hazard
            }
        }
        return best ?: DiseaseCatalog.OTHER
    }

    /** Matndagi mamlakatlar (birinchi uchrash tartibida). Uzun nom avval «yeb» olinadi: "Papua New Guinea" ≠ "Guinea". */
    fun countries(text: String): List<String> {
        val taken = BooleanArray(text.length)
        val found = mutableListOf<Pair<Int, String>>()
        for ((iso3, regex, _) in countryPatterns) {
            for (m in regex.findAll(text)) {
                if ((m.range).any { taken[it] }) continue
                m.range.forEach { taken[it] = true }
                found += m.range.first to iso3
            }
        }
        return found.sortedBy { it.first }.map { it.second }.distinct()
    }

    fun flags(text: String): Set<SignalFlag> {
        val result = mutableSetOf<SignalFlag>()
        for ((flag, patterns) in flagPatterns) {
            val hit =
                patterns.any { r ->
                    r.findAll(text).any { m ->
                        // "no evidence of human-to-human transmission" — inkor qilingan belgini hisoblamaymiz.
                        val before = text.substring(maxOf(0, m.range.first - 40), m.range.first)
                        !negations.containsMatchIn(before)
                    }
                }
            if (hit) result += flag
        }
        return result
    }

    companion object {
        private fun boundary(
            phrase: String,
            ignoreCase: Boolean,
        ): Regex {
            val opts = if (ignoreCase) setOf(RegexOption.IGNORE_CASE) else emptySet()
            return Regex("(?<![\\p{L}\\p{N}])" + Regex.escape(phrase) + "(?![\\p{L}\\p{N}])", opts)
        }

        /** Faqat boshidan chegaralangan: "escalat" → "escalating", "escalation". */
        private fun prefixBoundary(phrase: String): Regex =
            Regex("(?<![\\p{L}\\p{N}])" + Regex.escape(phrase), RegexOption.IGNORE_CASE)

        /** Turli apostrof va tirelarni bir xil ko'rinishga keltirish. */
        fun normalize(text: String): String =
            text
                .replace('’', '\'')
                .replace('‘', '\'')
                .replace('–', '-')
                .replace('—', '-')
                .replace(' ', ' ')
    }
}
