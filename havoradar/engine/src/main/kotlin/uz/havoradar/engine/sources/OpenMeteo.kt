package uz.havoradar.engine.sources

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonNull
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.booleanOrNull
import kotlinx.serialization.json.doubleOrNull
import kotlinx.serialization.json.intOrNull
import kotlinx.serialization.json.jsonObject
import uz.havoradar.engine.model.AirSeries
import uz.havoradar.engine.model.Place
import uz.havoradar.engine.model.WeatherSeries
import uz.havoradar.engine.net.HttpFetcher
import java.io.IOException
import java.time.Instant
import java.time.LocalDateTime
import java.util.Locale

/** Manba javobi kutilgan formatda emas yoki xato haqida xabar qaytardi. */
class SourceFormatException(
    message: String,
) : IOException(message)

/**
 * Open-Meteo: ob-havo (https://open-meteo.com/en/docs) va havo sifati (Copernicus CAMS,
 * https://open-meteo.com/en/docs/air-quality-api). Vaqtlar joyning mahalliy vaqtida (`timezone=auto`).
 * Ma'lumotlar litsenziyasi: CC BY 4.0 — ilovada manba ko'rsatiladi.
 */
object OpenMeteo {
    /** O'tgan 2 kun — ketma-ket issiq kunlarni hisoblash uchun; 7 kun oldinga. */
    fun weatherUrl(p: Place): String =
        "https://api.open-meteo.com/v1/forecast?latitude=${coord(p.lat)}&longitude=${coord(p.lon)}" +
            "&hourly=temperature_2m,relative_humidity_2m,uv_index&past_days=2&forecast_days=7&timezone=auto"

    /** CAMS global prognozi 5 kungacha; o'tgan 1 kun — bugungi sutkalik o'rtacha uchun. */
    fun airUrl(p: Place): String =
        "https://air-quality-api.open-meteo.com/v1/air-quality?latitude=${coord(p.lat)}&longitude=${coord(p.lon)}" +
            "&hourly=pm2_5,pm10,ozone,nitrogen_dioxide,dust&past_days=1&forecast_days=5&timezone=auto"

    suspend fun fetchWeather(
        http: HttpFetcher,
        p: Place,
        now: Instant,
    ): WeatherSeries = parseWeather(http.get(weatherUrl(p)), p.id, now)

    suspend fun fetchAir(
        http: HttpFetcher,
        p: Place,
        now: Instant,
    ): AirSeries = parseAir(http.get(airUrl(p)), p.id, now)

    fun parseWeather(
        text: String,
        placeId: String,
        fetchedAt: Instant,
    ): WeatherSeries {
        val h = Hourly.parse(text)
        return WeatherSeries(
            placeId = placeId,
            fetchedAt = fetchedAt,
            utcOffsetSeconds = h.offset,
            times = h.times,
            temp = h.values("temperature_2m"),
            humidity = h.values("relative_humidity_2m"),
            uv = h.values("uv_index", required = false),
        )
    }

    fun parseAir(
        text: String,
        placeId: String,
        fetchedAt: Instant,
    ): AirSeries {
        val h = Hourly.parse(text)
        return AirSeries(
            placeId = placeId,
            fetchedAt = fetchedAt,
            utcOffsetSeconds = h.offset,
            times = h.times,
            pm25 = h.values("pm2_5"),
            pm10 = h.values("pm10"),
            ozone = h.values("ozone", required = false),
            no2 = h.values("nitrogen_dioxide", required = false),
            dust = h.values("dust", required = false),
        )
    }

    private fun coord(v: Double) = String.format(Locale.ROOT, "%.4f", v)

    private class Hourly(
        val offset: Int,
        val times: List<LocalDateTime>,
        private val hourly: JsonObject,
    ) {
        fun values(
            key: String,
            required: Boolean = true,
        ): List<Double?> {
            val arr = hourly[key] as? JsonArray
            if (arr == null) {
                if (required) throw SourceFormatException("Open-Meteo javobida «$key» yo'q")
                return List(times.size) { null }
            }
            if (arr.size != times.size) throw SourceFormatException("Open-Meteo: «$key» uzunligi vaqtlar soniga teng emas")
            // Fizik ma'nosiz qiymatlar (model xatosi) tashlab yuboriladi.
            return arr.map { e -> (e as? JsonPrimitive)?.takeUnless { it is JsonNull }?.doubleOrNull?.takeIf { it.isFinite() && it > -90 && it < 20_000 } }
        }

        companion object {
            fun parse(text: String): Hourly {
                val o =
                    runCatching { Json.parseToJsonElement(text).jsonObject }.getOrNull()
                        ?: throw SourceFormatException("Open-Meteo javobi JSON emas")
                if ((o["error"] as? JsonPrimitive)?.booleanOrNull == true) {
                    throw SourceFormatException("Open-Meteo: ${(o["reason"] as? JsonPrimitive)?.content ?: "xato"}")
                }
                val hourly = o["hourly"] as? JsonObject ?: throw SourceFormatException("Open-Meteo javobida «hourly» yo'q")
                val times =
                    (hourly["time"] as? JsonArray)?.map { LocalDateTime.parse((it as JsonPrimitive).content) }
                        ?: throw SourceFormatException("Open-Meteo javobida vaqtlar yo'q")
                val offset = (o["utc_offset_seconds"] as? JsonPrimitive)?.intOrNull ?: 0
                return Hourly(offset, times, hourly)
            }
        }
    }
}
