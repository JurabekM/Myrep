package com.agrovision.app.data.remote

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit

/**
 * Ob-havo provayderlari — desktop `weather/service.py` bilan bir xil ikki manba:
 *  • Open-Meteo (archive = haqiqiy tarixiy ERA5, forecast = 7 kunlik prognoz)
 *  • NASA POWER (qishloq xo'jaligi uchun kunlik tarixiy ma'lumot)
 *
 * Ikkalasi ham bepul va API kalitisiz. Har qanday tarmoq xatosi `null`
 * qaytaradi — chaqiruvchi keshdagi ma'lumot bilan davom etadi, ilova qulamaydi.
 */
object WeatherApi {

    data class DailyPoint(
        val date: LocalDate,
        val tMax: Double,
        val tMin: Double,
        val precipitationMm: Double,
        val humidity: Double,
    )

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(20, TimeUnit.SECONDS)
        .build()

    private val ISO: DateTimeFormatter = DateTimeFormatter.ISO_LOCAL_DATE
    private const val DAILY_FIELDS =
        "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean"

    /** Haqiqiy tarixiy kunlik ma'lumot (Open-Meteo archive / ERA5). */
    suspend fun openMeteoHistory(lat: Double, lon: Double, start: LocalDate, end: LocalDate): List<DailyPoint>? =
        request(
            HttpUrl.Builder().scheme("https").host("archive-api.open-meteo.com")
                .addPathSegments("v1/archive")
                .addQueryParameter("latitude", lat.toString())
                .addQueryParameter("longitude", lon.toString())
                .addQueryParameter("start_date", start.format(ISO))
                .addQueryParameter("end_date", end.format(ISO))
                .addQueryParameter("daily", DAILY_FIELDS)
                .addQueryParameter("timezone", "Asia/Tashkent")
                .build(),
        ) { parseOpenMeteo(it) }

    /** 7 kunlik jonli prognoz. */
    suspend fun openMeteoForecast(lat: Double, lon: Double, days: Int = 7): List<DailyPoint>? =
        request(
            HttpUrl.Builder().scheme("https").host("api.open-meteo.com")
                .addPathSegments("v1/forecast")
                .addQueryParameter("latitude", lat.toString())
                .addQueryParameter("longitude", lon.toString())
                .addQueryParameter("daily", DAILY_FIELDS)
                .addQueryParameter("forecast_days", days.toString())
                .addQueryParameter("timezone", "Asia/Tashkent")
                .build(),
        ) { parseOpenMeteo(it) }

    /** NASA POWER (AG community) — tarixiy kunlik ma'lumot muqobil manbasi. */
    suspend fun nasaPowerHistory(lat: Double, lon: Double, start: LocalDate, end: LocalDate): List<DailyPoint>? =
        request(
            HttpUrl.Builder().scheme("https").host("power.larc.nasa.gov")
                .addPathSegments("api/temporal/daily/point")
                .addQueryParameter("parameters", "T2M_MAX,T2M_MIN,PRECTOTCORR,RH2M")
                .addQueryParameter("community", "AG")
                .addQueryParameter("latitude", lat.toString())
                .addQueryParameter("longitude", lon.toString())
                .addQueryParameter("start", start.format(DateTimeFormatter.BASIC_ISO_DATE))
                .addQueryParameter("end", end.format(DateTimeFormatter.BASIC_ISO_DATE))
                .addQueryParameter("format", "JSON")
                .build(),
        ) { parseNasaPower(it) }

    private suspend fun request(url: HttpUrl, parse: (String) -> List<DailyPoint>): List<DailyPoint>? =
        withContext(Dispatchers.IO) {
            try {
                client.newCall(Request.Builder().url(url).build()).execute().use { response ->
                    if (!response.isSuccessful) return@withContext null
                    val body = response.body?.string() ?: return@withContext null
                    parse(body).ifEmpty { null }
                }
            } catch (e: Exception) {
                null
            }
        }

    private fun parseOpenMeteo(body: String): List<DailyPoint> {
        val daily = JSONObject(body).optJSONObject("daily") ?: return emptyList()
        val times = daily.optJSONArray("time") ?: return emptyList()
        val tMax = daily.optJSONArray("temperature_2m_max")
        val tMin = daily.optJSONArray("temperature_2m_min")
        val precip = daily.optJSONArray("precipitation_sum")
        val humidity = daily.optJSONArray("relative_humidity_2m_mean")

        val points = ArrayList<DailyPoint>(times.length())
        for (i in 0 until times.length()) {
            val high = tMax?.optDouble(i, Double.NaN) ?: Double.NaN
            val low = tMin?.optDouble(i, Double.NaN) ?: Double.NaN
            if (high.isNaN() || low.isNaN()) continue
            val date = runCatching { LocalDate.parse(times.optString(i)) }.getOrNull() ?: continue
            points += DailyPoint(
                date = date, tMax = high, tMin = low,
                precipitationMm = precip.safeDouble(i, 0.0),
                humidity = humidity.safeDouble(i, 55.0),
            )
        }
        return points
    }

    private fun parseNasaPower(body: String): List<DailyPoint> {
        val parameters = JSONObject(body).optJSONObject("properties")?.optJSONObject("parameter")
            ?: return emptyList()
        val tMax = parameters.optJSONObject("T2M_MAX") ?: return emptyList()
        val tMin = parameters.optJSONObject("T2M_MIN")
        val precip = parameters.optJSONObject("PRECTOTCORR")
        val humidity = parameters.optJSONObject("RH2M")

        val points = ArrayList<DailyPoint>()
        val keys = tMax.keys()
        while (keys.hasNext()) {
            val key = keys.next()
            val date = runCatching {
                LocalDate.parse(key, DateTimeFormatter.BASIC_ISO_DATE)
            }.getOrNull() ?: continue
            val high = tMax.optDouble(key, Double.NaN)
            val low = tMin?.optDouble(key, Double.NaN) ?: Double.NaN
            // NASA POWER mavjud bo'lmagan qiymatni -999 bilan belgilaydi
            if (high.isNaN() || low.isNaN() || high < -100 || low < -100) continue
            points += DailyPoint(
                date = date, tMax = high, tMin = low,
                precipitationMm = (precip?.optDouble(key, 0.0) ?: 0.0).coerceAtLeast(0.0),
                humidity = (humidity?.optDouble(key, 55.0) ?: 55.0).coerceIn(0.0, 100.0),
            )
        }
        return points.sortedBy { it.date }
    }

    private fun org.json.JSONArray?.safeDouble(index: Int, fallback: Double): Double {
        val value = this?.optDouble(index, fallback) ?: fallback
        return if (value.isNaN()) fallback else value
    }
}
