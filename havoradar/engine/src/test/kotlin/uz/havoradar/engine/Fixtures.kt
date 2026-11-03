package uz.havoradar.engine

import uz.havoradar.engine.geo.Places
import uz.havoradar.engine.knowledge.Guide
import uz.havoradar.engine.net.HttpException
import uz.havoradar.engine.net.HttpFetcher
import java.time.Instant

/**
 * Test ma'lumotlari (src/test/resources/fixtures):
 * - air_*_2026-11-02.json — Open-Meteo havo sifati API'sidan 2026-11-02 da jonli olingan haqiqiy javoblar;
 * - weather_*.json, air_tashkent_2026-07.json — tool/synth_fixtures.py yaratgan namunaviy javoblar (aynan Open-Meteo formatida).
 */
object Fixtures {
    val places: Places by lazy { Places.load() }
    val guide: Guide by lazy { Guide.load() }

    /** Iyul ssenariysi: Toshkentda 09:00 (15-iyul), issiqlik to'lqini boshlanmoqda. */
    val JULY: Instant = Instant.parse("2026-07-15T04:00:00Z")

    /** Noyabr ssenariysi: haqiqiy havo sifati javoblari olingan payt (Toshkentda 17:00). */
    val NOVEMBER: Instant = Instant.parse("2026-11-02T12:00:00Z")

    fun text(name: String): String =
        Fixtures::class.java.getResourceAsStream("/fixtures/$name")!!.bufferedReader().use { it.readText() }

    enum class Scenario { JULY, NOVEMBER }

    /** URL bo'yicha fixture qaytaruvchi soxta tarmoq. `failing` — xato beradigan URL qismlari. */
    class FakeHttp(
        private val scenario: Scenario,
        private val failing: Set<String> = emptySet(),
    ) : HttpFetcher {
        val requests = mutableListOf<String>()

        override suspend fun get(url: String): String {
            requests += url
            if (failing.any { url.contains(it) }) throw HttpException(503, url)
            val air = "air-quality" in url
            val city =
                when {
                    "latitude=41.2995" in url -> "tashkent"
                    "latitude=28.6139" in url -> "delhi"
                    else -> throw HttpException(404, url)
                }
            val name =
                when (scenario) {
                    Scenario.JULY -> if (air) "air_${city}_2026-07.json" else "weather_${city}_2026-07.json"
                    Scenario.NOVEMBER -> if (air) "air_${city}_2026-11-02.json" else "weather_${city}_2026-11.json"
                }
            return Fixtures::class.java.getResourceAsStream("/fixtures/$name")?.bufferedReader()?.use { it.readText() }
                ?: throw HttpException(404, url)
        }
    }
}
