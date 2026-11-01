package uz.epiradar.engine

import kotlinx.coroutines.runBlocking
import uz.epiradar.engine.model.Settings
import uz.epiradar.engine.net.UrlConnectionFetcher
import kotlin.test.Test
import kotlin.test.assertTrue

/**
 * Haqiqiy manbalarga qarshi tekshiruv (tarmoq kerak): `EPIRADAR_LIVE=1 gradle test --tests '*LiveSmokeTest*'`.
 * Odatiy `gradle test` da o'tkazib yuboriladi — CI tashqi saytlarga bog'liq bo'lmasligi uchun.
 */
class LiveSmokeTest {
    @Test
    fun `live sources are reachable and parse`() {
        if (System.getenv("EPIRADAR_LIVE") != "1") return
        val engine = Engine(UrlConnectionFetcher())
        val snap = runBlocking { engine.sync(Settings(country = "UZB"), null) }
        snap.sources.forEach { println("  ${it.source}: ok=${it.ok} n=${it.itemCount} ${it.error ?: ""}") }
        println("  Shaxsiy: ${snap.personalScore} (${snap.personalLevel.uz}), global: ${snap.globalScore}")
        snap.events.take(6).forEach { println("  ${it.assessment.personalScore}/${it.assessment.globalScore} ${it.title}") }
        snap.trends.forEach { println("  trend ${it.country}: ${it.status} ${it.points.size} nuqta — ${it.note.take(90)}") }
        assertTrue(snap.sources.all { it.ok }, snap.sources.toString())
        assertTrue(snap.events.isNotEmpty())
    }
}
