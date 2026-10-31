package uz.epiradar.engine.trend

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import uz.epiradar.engine.net.HttpFetcher
import java.time.LocalDate

/** Bir hafta bo'yicha jamlangan gripp laboratoriya ma'lumoti (sentinel + nosentinel). */
data class FluWeek(
    val weekStart: LocalDate,
    val tested: Int,
    val positive: Int,
    /** Inson namunalarida A(H5) qush grippi. */
    val h5: Int,
    val h7n9: Int,
) {
    /** Musbatlik ulushi (%), namunalar kam bo'lsa (< [MIN_TESTED]) — null. */
    val positivity: Double? get() = if (tested >= MIN_TESTED) positive * 100.0 / tested else null

    companion object {
        const val MIN_TESTED = 10
    }
}

/** JSST FluNet (xMart ochiq OData API) — mamlakatlar bo'yicha haftalik gripp kuzatuvi. */
class FluNetSource {
    fun url(
        iso3: String,
        since: LocalDate,
    ): String =
        "https://xmart-api-public.who.int/FLUMART/VIW_FNT?\$format=json" +
            "&\$select=COUNTRY_CODE,ISO_WEEKSTARTDATE,ORIGIN_SOURCE,SPEC_PROCESSED_NB,INF_ALL,INF_A,INF_B,AH5,AH7N9" +
            "&\$filter=COUNTRY_CODE%20eq%20'$iso3'%20and%20ISO_WEEKSTARTDATE%20ge%20$since" +
            "&\$orderby=ISO_WEEKSTARTDATE%20desc"

    suspend fun fetch(
        http: HttpFetcher,
        iso3: String,
        since: LocalDate,
    ): List<FluWeek> {
        require(iso3.matches(Regex("[A-Z]{3}"))) { "ISO3 kod noto'g'ri: $iso3" }
        return parse(http.get(url(iso3, since)))
    }

    /** Haftalar o'sish tartibida; bir haftadagi bir nechta qator (SENTINEL/NONSENTINEL) qo'shiladi. */
    fun parse(json: String): List<FluWeek> {
        val rows = Json.parseToJsonElement(json).jsonObject.getValue("value").jsonArray
        return rows
            .mapNotNull { el ->
                val o = el.jsonObject
                val week = o.str("ISO_WEEKSTARTDATE")?.take(10)?.let { runCatching { LocalDate.parse(it) }.getOrNull() } ?: return@mapNotNull null
                val infA = o.int("INF_A")
                val infB = o.int("INF_B")
                // INF_ALL ba'zan null, A va B esa to'ldirilgan bo'ladi.
                val positive = o.int("INF_ALL").takeIf { o["INF_ALL"].isNumber() } ?: (infA + infB)
                FluWeek(week, o.int("SPEC_PROCESSED_NB"), positive, o.int("AH5"), o.int("AH7N9"))
            }.groupBy { it.weekStart }
            .map { (week, list) ->
                FluWeek(week, list.sumOf { it.tested }, list.sumOf { it.positive }, list.sumOf { it.h5 }, list.sumOf { it.h7n9 })
            }.sortedBy { it.weekStart }
    }

    private fun JsonObject.str(key: String): String? = (this[key] as? JsonPrimitive)?.takeUnless { it is JsonNull }?.content

    private fun JsonObject.int(key: String): Int = (this[key] as? JsonPrimitive)?.intOrNull ?: 0

    private fun kotlinx.serialization.json.JsonElement?.isNumber(): Boolean = this is JsonPrimitive && this !is JsonNull && intOrNull != null
}
