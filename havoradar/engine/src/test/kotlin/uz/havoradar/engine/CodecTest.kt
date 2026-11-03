package uz.havoradar.engine

import kotlinx.coroutines.test.runTest
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import uz.havoradar.engine.Fixtures.FakeHttp
import uz.havoradar.engine.Fixtures.JULY
import uz.havoradar.engine.Fixtures.Scenario
import uz.havoradar.engine.model.RiskLevel
import uz.havoradar.engine.model.Settings
import uz.havoradar.engine.model.Vulnerability
import java.io.File
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class CodecTest {
    private val settings = Settings(placeId = "tashkent", extraPlaces = listOf("termez"), profile = setOf(Vulnerability.ELDERLY))

    @Test
    fun `stored state round-trips and gives the same assessment`() =
        runTest {
            val e = Engine(FakeHttp(Scenario.JULY), Fixtures.places, Fixtures.guide) { JULY }
            val synced = e.sync(settings, null)
            val text = e.codec.encodeState(synced.state).toString()
            val back = e.codec.decodeState(text)!!
            assertEquals(synced.state.weather.map { it.times }, back.weather.map { it.times })
            assertEquals(synced.state.weather.first().temp, back.weather.first().temp)
            assertEquals(synced.state.air.first().pm25, back.air.first().pm25)
            assertEquals(synced.state.sources, back.sources)
            assertEquals(e.codec.encode(synced.snapshot), e.codec.encode(e.reassess(back, settings)))
            // Ketma-ket soatlar uchun vaqtlar ro'yxati yozilmaydi (fayl kichik).
            assertFalse("\"times\"" in text)
            assertNull(e.codec.decodeState("""{"schema":99}"""))
            assertNull(e.codec.decodeState("buzilgan"))
        }

    @Test
    fun `settings are sanitized`() {
        val c = Engine({ error("tarmoq yo'q") }, Fixtures.places, Fixtures.guide).codec
        assertEquals(settings, c.decodeSettings(c.encodeSettings(settings).toString()))
        val bad =
            c.decodeSettings(
                """{"placeId":"atlantis","extraPlaces":["tashkent","termez","termez","x","delhi","mecca","seoul"],
                   "profile":["ELDERLY","ALIEN"],"alertThreshold":"CALM","syncHours":5,"quietHours":false}""",
            )
        assertEquals("tashkent", bad.placeId)
        assertEquals(listOf("termez", "delhi", "mecca"), bad.extraPlaces)
        assertEquals(setOf(Vulnerability.ELDERLY), bad.profile)
        assertEquals(RiskLevel.WARNING, bad.alertThreshold)
        assertEquals(3, bad.syncHours)
        assertFalse(bad.quietHours)
        assertEquals(Settings(), c.decodeSettings(null))
        assertEquals(Settings(), c.decodeSettings("[1,2]"))
    }

    @Test
    fun `snapshot json carries ready-made Uzbek texts`() =
        runTest {
            val e = Engine(FakeHttp(Scenario.JULY), Fixtures.places, Fixtures.guide) { JULY }
            val json = e.codec.encode(e.sync(settings, null).snapshot)
            val place = json["places"]!!.jsonArray[0].jsonObject
            assertEquals("Toshkent", place["name"]!!.jsonPrimitive.content)
            val day = place["days"]!!.jsonArray[0].jsonObject
            val heat = day["heatRisk"]!!.jsonObject
            assertEquals("Favqulodda", heat["personal"]!!.jsonObject["name"]!!.jsonPrimitive.content)
            assertTrue(heat["reasons"]!!.jsonArray.isNotEmpty())
            assertEquals("Juda yuqori", day["uv"]!!.jsonObject["name"]!!.jsonPrimitive.content)
            // Termiz uchun fixture yo'q — joy bor, kunlar bo'sh.
            val termez = json["places"]!!.jsonArray[1].jsonObject
            assertEquals(JsonNull, termez["today"])
            assertTrue(termez["days"]!!.jsonArray.isEmpty())

            val catalog = e.codec.catalog()
            assertEquals(5, (catalog["levels"] as JsonArray).size)
            assertEquals(Vulnerability.entries.size, (catalog["vulnerabilities"] as JsonArray).size)
            assertTrue((catalog["guide"] as JsonArray).isNotEmpty())

            // Flutter testlari uchun yadroning haqiqiy chiqishi: HAVORADAR_EXPORT=../test/fixtures ./gradlew test --rerun-tasks
            System.getenv("HAVORADAR_EXPORT")?.let { dir ->
                val pretty = Json { prettyPrint = true }
                File(dir).mkdirs()
                File(dir, "snapshot.json").writeText(pretty.encodeToString(JsonObject.serializer(), json) + "\n")
                File(dir, "catalog.json").writeText(pretty.encodeToString(JsonObject.serializer(), catalog) + "\n")
                File(dir, "settings.json").writeText(pretty.encodeToString(JsonObject.serializer(), e.codec.encodeSettings(settings)) + "\n")
                println("Eksport: $dir")
            }
        }

    @Test
    fun `guide parser rejects entries without sources`() {
        val ok = Fixtures.guide.json.toString()
        assertEquals(Fixtures.guide.ids, uz.havoradar.engine.knowledge.Guide.parse(ok).ids)
        val broken = Json.parseToJsonElement(ok).jsonArray.first().jsonObject.toMutableMap().apply { remove("sources") }
        kotlin.test.assertFailsWith<IllegalArgumentException> {
            uz.havoradar.engine.knowledge.Guide.parse(JsonArray(listOf(JsonObject(broken))).toString())
        }
    }
}
