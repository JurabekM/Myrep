package uz.havoradar.engine.knowledge

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject

/**
 * Oflayn ma'lumotnoma (resources/havoradar/guide.json): issiqlik kasalliklari belgilari va birinchi yordam,
 * havo ifloslanishi, UV, sezgir guruhlar. Matnlar faqat JSST/CDC/NIOSH/EPA manbalariga asoslanadi;
 * har bir bo'limda manba havolasi bor.
 */
class Guide(
    val json: JsonArray,
) {
    val ids: List<String> get() = json.map { (it.jsonObject["id"] as JsonPrimitive).content }

    companion object {
        fun load(): Guide {
            val text = Guide::class.java.getResourceAsStream("/havoradar/guide.json")!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
            return parse(text)
        }

        fun parse(text: String): Guide {
            val arr = Json.parseToJsonElement(text).jsonArray
            for (e in arr) {
                val o = e.jsonObject
                for (k in listOf("id", "title", "icon", "summary")) require(o[k] is JsonPrimitive) { "guide.json: «$k» yo'q: $o" }
                val sources = o["sources"]?.jsonArray
                require(!sources.isNullOrEmpty()) { "guide.json: «${o["id"]}» manbasiz" }
                sources.forEach { s -> require((s.jsonObject["url"] as JsonPrimitive).content.startsWith("https://")) }
                require(o["sections"]?.jsonArray?.all { s -> (s as JsonObject)["items"] is JsonArray } == true)
            }
            return Guide(arr)
        }
    }
}
