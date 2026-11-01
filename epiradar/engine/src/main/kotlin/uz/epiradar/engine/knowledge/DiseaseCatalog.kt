package uz.epiradar.engine.knowledge

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonElement
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive

enum class PandemicPotential(
    val uz: String,
    /** Havo qatnovi orqali uzoq masofaga tarqalish ehtimoli (yaqinlik koeffitsientini oshiradi). */
    val spread: Double,
) {
    HIGH("Yuqori", 0.35),
    MEDIUM("O'rta", 0.15),
    LOW("Past", 0.0),
}

data class Disease(
    val id: String,
    val name: String,
    val group: String,
    val hazard: Double,
    val pandemic: PandemicPotential,
    val aliases: List<String>,
    val transmission: String,
    val incubation: String,
    val fatality: String,
    val symptoms: List<String>,
    val prevention: List<String>,
    val redFlags: List<String>,
    val vaccine: String,
    val treatment: String,
    val localNote: String,
    /** Asl JSON (Flutter'ga o'zgarishsiz uzatiladi). */
    val json: JsonObject,
)

/** Kasalliklar ma'lumotnomasi (`diseases.json`). */
class DiseaseCatalog(
    val all: List<Disease>,
) {
    private val byId = all.associateBy { it.id }

    init {
        require(byId.containsKey(OTHER)) { "diseases.json: \"$OTHER\" yozuvi majburiy" }
        all.forEach { require(it.hazard in 0.0..1.0) { "${it.id}: hazard 0..1 oralig'ida bo'lishi kerak" } }
    }

    operator fun get(id: String): Disease = byId[id] ?: byId.getValue(OTHER)

    companion object {
        const val OTHER = "other"

        fun parse(text: String): DiseaseCatalog {
            val root = Json.parseToJsonElement(text).jsonObject
            return DiseaseCatalog(root.getValue("diseases").jsonArray.map { parseDisease(it.jsonObject) })
        }

        fun load(): DiseaseCatalog {
            val stream =
                DiseaseCatalog::class.java.getResourceAsStream("/epiradar/diseases.json")
                    ?: error("diseases.json resursi topilmadi")
            return parse(stream.bufferedReader(Charsets.UTF_8).use { it.readText() })
        }

        private fun parseDisease(o: JsonObject): Disease {
            fun str(key: String) = o[key]?.jsonPrimitive?.content.orEmpty()

            fun list(key: String) = (o[key] as? JsonArray)?.map(JsonElement::str).orEmpty()
            return Disease(
                id = str("id"),
                name = str("name"),
                group = str("group"),
                hazard = str("hazard").toDouble(),
                pandemic = PandemicPotential.valueOf(str("pandemic").uppercase()),
                aliases = list("aliases").map { it.lowercase() },
                transmission = str("transmission"),
                incubation = str("incubation"),
                fatality = str("fatality"),
                symptoms = list("symptoms"),
                prevention = list("prevention"),
                redFlags = list("redFlags"),
                vaccine = str("vaccine"),
                treatment = str("treatment"),
                localNote = str("localNote"),
                json = o,
            )
        }
    }
}

private fun JsonElement.str(): String = jsonPrimitive.content
