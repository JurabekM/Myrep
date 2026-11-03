package uz.havoradar.engine

import kotlinx.coroutines.runBlocking
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.net.UrlConnectionFetcher
import kotlin.test.Test
import kotlin.test.assertTrue

/**
 * Haqiqiy Open-Meteo'ga qarshi tekshiruv (tarmoq kerak): `HAVORADAR_LIVE=1 ./gradlew test --tests '*LiveSmokeTest*' -i`.
 * Odatiy `gradle test` da o'tkazib yuboriladi — CI tashqi saytlarga bog'liq bo'lmasligi uchun.
 */
class LiveSmokeTest {
    @Test
    fun `live sources are reachable and parse`() {
        if (System.getenv("HAVORADAR_LIVE") != "1") return
        val engine = Engine(UrlConnectionFetcher())
        val snap = runBlocking { engine.sync(Settings(placeId = "tashkent", extraPlaces = listOf("termez")), null) }.snapshot
        snap.sources.forEach { println("  ${it.source}: ok=${it.ok} ${it.error ?: ""}") }
        for (p in snap.places) {
            println("  ${p.place.name}: bugun ${p.today?.personalScore} · ${p.days.size} kun · ${p.hours.size} soat")
            p.days.forEach { d ->
                println("    ${d.date} T ${d.tempMin}..${d.tempMax} his ${d.feelsMax} UV ${d.uvMax} PM2.5 ${d.air?.pm25Mean?.toInt()} → issiq ${d.heatRisk?.baseScore} havo ${d.airRisk?.baseScore}")
            }
        }
        assertTrue(snap.sources.all { it.ok }, snap.sources.toString())
        assertTrue(snap.places.all { it.days.size >= 5 && it.today?.heatRisk != null && it.today?.airRisk != null })
    }
}
