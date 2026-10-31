package uz.epiradar.engine.sources

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.net.HttpFetcher
import uz.epiradar.engine.parse.Dates
import uz.epiradar.engine.parse.Html
import uz.epiradar.engine.parse.RssParser
import uz.epiradar.engine.text.SignalClassifier
import java.time.Instant

/** Xabarlar manbasi: tarmoqdan oladi va [Signal] larga aylantiradi. */
interface SignalSource {
    val id: SourceId

    suspend fun fetch(http: HttpFetcher): List<Signal>
}

/** Matnni tasniflab [Signal] yaratadi — barcha manbalar uchun umumiy. */
class SignalFactory(
    private val classifier: SignalClassifier,
) {
    fun create(
        source: SourceId,
        id: String,
        title: String,
        summary: String,
        url: String,
        publishedAt: Instant,
        travelLevel: Int? = null,
        extraCountryText: String = "",
    ): Signal {
        val t = SignalClassifier.normalize(title)
        val s = SignalClassifier.normalize(summary)
        val all = "$t. $s"
        // Sarlavhadagi mamlakatlar asosiy; tavsifdagilar (masalan, "travel history from ...") keyin qo'shiladi.
        val countries = (classifier.countries(t) + classifier.countries(SignalClassifier.normalize(extraCountryText)) + classifier.countries(s)).distinct()
        val flags = classifier.flags(all).toMutableSet()
        if (countries.size >= 3) flags += SignalFlag.MULTI_COUNTRY
        val disease = classifier.disease(t).takeIf { it != DiseaseCatalog.OTHER } ?: classifier.disease(all)
        return Signal(
            id = id,
            source = source,
            title = t.trim(),
            summary = s.trim(),
            url = url,
            publishedAt = publishedAt,
            countries = countries,
            diseaseId = disease,
            flags = flags,
            travelLevel = travelLevel,
        )
    }
}

/** JSST Disease Outbreak News — rasmiy OData API (www.who.int/api/news/diseaseoutbreaknews). */
class WhoDonSource(
    private val factory: SignalFactory,
    private val top: Int = 40,
) : SignalSource {
    override val id = SourceId.WHO_DON

    val url: String =
        "https://www.who.int/api/news/diseaseoutbreaknews?sf_culture=en" +
            "&\$orderby=PublicationDateAndTime%20desc&\$top=$top" +
            "&\$select=Id,Title,OverrideTitle,UseOverrideTitle,PublicationDateAndTime,UrlName,DonId,Summary"

    override suspend fun fetch(http: HttpFetcher): List<Signal> = parse(http.get(url))

    fun parse(json: String): List<Signal> =
        Json.parseToJsonElement(json).jsonObject.getValue("value").jsonArray.mapNotNull { el ->
            val o = el.jsonObject
            val published = Dates.iso(o.s("PublicationDateAndTime")) ?: return@mapNotNull null
            val override = o.s("UseOverrideTitle").equals("true", ignoreCase = true) && o.s("OverrideTitle").isNotBlank()
            val title = Html.toText(if (override) o.s("OverrideTitle") else o.s("Title"))
            val slug = o.s("UrlName").ifBlank { o.s("DonId") }
            if (title.isBlank() || slug.isBlank()) return@mapNotNull null
            factory.create(
                source = id,
                id = "who:" + o.s("DonId").ifBlank { o.s("Id") },
                title = title,
                summary = Html.toText(o.s("Summary")),
                url = "https://www.who.int/emergencies/disease-outbreak-news/item/$slug",
                publishedAt = published,
            )
        }
}

/** CDC Travelers' Health — sayohat ogohlantirishlari (1–4 daraja). */
class CdcTravelSource(
    private val factory: SignalFactory,
) : SignalSource {
    override val id = SourceId.CDC_TRAVEL
    val url = "https://wwwnc.cdc.gov/travel/rss/notices.xml"

    private val levelRe = Regex("^\\s*Level\\s+(\\d)\\s*[-–:]\\s*(.+)$", RegexOption.IGNORE_CASE)
    private val countryListRe = Regex("Country List\\s*:\\s*(.+)$", RegexOption.IGNORE_CASE)

    override suspend fun fetch(http: HttpFetcher): List<Signal> = parse(http.get(url))

    fun parse(xml: String): List<Signal> =
        RssParser.parse(xml).mapNotNull { item ->
            val m = levelRe.find(item.title)
            val level = m?.groupValues?.get(1)?.toIntOrNull()?.takeIf { it in 1..4 }
            val title = m?.groupValues?.get(2)?.trim() ?: item.title
            val countryList = countryListRe.find(item.description)?.groupValues?.get(1).orEmpty()
            factory.create(
                source = id,
                id = "cdc:" + item.guid,
                title = title,
                summary = item.description.replace(countryListRe, "").trim(),
                url = item.link,
                publishedAt = item.pubDate ?: return@mapNotNull null,
                travelLevel = level,
                extraCountryText = countryList,
            )
        }
}

/**
 * ECDC RSS lentalari: epidemiologik yangilanishlar (hammasi) va umumiy yangiliklar (faqat aniq
 * kasallik haqidagilari — tayyorgarlik, tadbirlar va h.k. tashlab yuboriladi).
 * Bitta lenta ishlamasa, ikkinchisi baribir qaytariladi.
 */
class EcdcSource(
    private val factory: SignalFactory,
) : SignalSource {
    override val id = SourceId.ECDC

    override suspend fun fetch(http: HttpFetcher): List<Signal> {
        val updates = runCatching { parse(http.get(EPI_UPDATES), requireDisease = false) }
        val news = runCatching { parse(http.get(NEWS), requireDisease = true) }
        if (updates.isFailure && news.isFailure) throw updates.exceptionOrNull()!!
        return (updates.getOrDefault(emptyList()) + news.getOrDefault(emptyList())).distinctBy { it.id }
    }

    fun parse(
        xml: String,
        requireDisease: Boolean,
    ): List<Signal> =
        RssParser.parse(xml).mapNotNull { item ->
            val signal =
                factory.create(
                    source = id,
                    id = "ecdc:" + item.guid,
                    title = item.title,
                    summary = item.description,
                    url = item.link,
                    publishedAt = item.pubDate ?: return@mapNotNull null,
                )
            signal.takeUnless { requireDisease && it.diseaseId == DiseaseCatalog.OTHER }
        }

    companion object {
        const val EPI_UPDATES = "https://www.ecdc.europa.eu/en/taxonomy/term/1310/feed"
        const val NEWS = "https://www.ecdc.europa.eu/en/taxonomy/term/1307/feed"
    }
}

private fun JsonObject.s(key: String): String = (this[key] as? JsonPrimitive)?.takeUnless { it is JsonNull }?.content.orEmpty()
