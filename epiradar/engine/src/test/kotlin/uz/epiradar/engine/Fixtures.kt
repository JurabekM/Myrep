package uz.epiradar.engine

import uz.epiradar.engine.geo.Countries
import uz.epiradar.engine.knowledge.DiseaseCatalog
import uz.epiradar.engine.model.Signal
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.model.SourceId
import uz.epiradar.engine.net.HttpException
import uz.epiradar.engine.net.HttpFetcher
import uz.epiradar.engine.text.SignalClassifier
import java.time.Instant

/** Haqiqiy manbalardan 2026-10-31 da olingan javoblar (src/test/resources/fixtures). */
object Fixtures {
    val catalog: DiseaseCatalog by lazy { DiseaseCatalog.load() }
    val countries: Countries by lazy { Countries.load() }
    val classifier: SignalClassifier by lazy { SignalClassifier(catalog, countries) }

    /** Fixture'lar olingan payt. */
    val NOW: Instant = Instant.parse("2026-10-31T12:00:00Z")

    fun text(name: String): String =
        Fixtures::class.java.getResourceAsStream("/fixtures/$name")!!.bufferedReader().use { it.readText() }

    /** URL bo'yicha fixture qaytaruvchi soxta tarmoq. `failing` — xato beradigan URL qismlari. */
    class FakeHttp(
        private val failing: Set<String> = emptySet(),
    ) : HttpFetcher {
        val requests = mutableListOf<String>()

        override suspend fun get(url: String): String {
            requests += url
            if (failing.any { url.contains(it) }) throw HttpException(503, url)
            return when {
                "diseaseoutbreaknews" in url -> text("who_don.json")
                "travel/rss" in url -> text("cdc_travel_notices.xml")
                "term/1310" in url -> text("ecdc_epi_updates.xml")
                "term/1307" in url -> EMPTY_RSS
                "FLUMART" in url && "'KAZ'" in url -> text("flunet_kaz.json")
                "FLUMART" in url -> """{"value":[]}"""
                else -> throw HttpException(404, url)
            }
        }
    }

    const val EMPTY_RSS = """<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>"""

    fun signal(
        id: String,
        disease: String,
        countries: List<String>,
        at: Instant = NOW,
        source: SourceId = SourceId.WHO_DON,
        flags: Set<SignalFlag> = emptySet(),
        travelLevel: Int? = null,
    ) = Signal(id, source, "t-$id", "s-$id", "https://example.org/$id", at, countries, disease, flags, travelLevel)
}
