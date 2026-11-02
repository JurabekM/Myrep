package uz.havoradar.engine.geo

import uz.havoradar.engine.model.Place

/** Oflayn joylar ro'yxati (resources/havoradar/places.tsv): GPS ruxsati va geokodlash so'rovi kerak emas. */
class Places(
    val all: List<Place>,
) {
    private val byId = all.associateBy { it.id }

    operator fun get(id: String): Place? = byId[id]

    fun name(id: String): String = byId[id]?.name ?: id

    companion object {
        fun load(): Places {
            val text =
                Places::class.java.getResourceAsStream("/havoradar/places.tsv")!!.bufferedReader(Charsets.UTF_8).use { it.readText() }
            return parse(text)
        }

        fun parse(text: String): Places =
            Places(
                text
                    .lineSequence()
                    .filter { it.isNotBlank() && !it.startsWith("#") }
                    .map { line ->
                        val c = line.split('\t')
                        require(c.size == 5) { "places.tsv: noto'g'ri qator: $line" }
                        Place(c[0], c[1], c[2].toDouble(), c[3].toDouble(), c[4] == "1")
                    }.toList(),
            )
    }
}
