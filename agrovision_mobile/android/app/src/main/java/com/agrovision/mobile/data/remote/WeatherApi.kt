package com.agrovision.mobile.data.remote

import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.HttpUrl
import okhttp3.OkHttpClient
import okhttp3.Request
import org.json.JSONObject

/**
 * Open-Meteo — bepul, kalitsiz ochiq API. Ikki uchi bor:
 *  - archive-api.open-meteo.com — HAQIQIY tarixiy kunlik ob-havo (ERA5 reanaliz)
 *  - api.open-meteo.com — joriy va 7 kunlik prognoz
 * Ikkalasi ham desktop AgroVision (weather/service.py) da ishlatilgan bilan bir xil.
 * Internet yo'q yoki so'rov muvaffaqiyatsiz bo'lsa — `null` qaytadi, chaqiruvchi
 * mahalliy keshdagi ma'lumot bilan davom etadi (ilova hech qachon shu sababli
 * qulamaydi).
 */
object WeatherApi {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .build()

    private val ISO = DateTimeFormatter.ISO_LOCAL_DATE
    private val DAILY_FIELDS = "temperature_2m_max,temperature_2m_min,precipitation_sum,relative_humidity_2m_mean"

    data class DailyPoint(val date: LocalDate, val tMax: Double, val tMin: Double, val precip: Double, val humidity: Double)

    suspend fun fetchHistory(lat: Double, lon: Double, start: LocalDate, end: LocalDate): List<DailyPoint>? =
        withContext(Dispatchers.IO) {
            try {
                val url = HttpUrl.Builder()
                    .scheme("https").host("archive-api.open-meteo.com").addPathSegments("v1/archive")
                    .addQueryParameter("latitude", lat.toString())
                    .addQueryParameter("longitude", lon.toString())
                    .addQueryParameter("start_date", start.format(ISO))
                    .addQueryParameter("end_date", end.format(ISO))
                    .addQueryParameter("daily", DAILY_FIELDS)
                    .addQueryParameter("timezone", "Asia/Tashkent")
                    .build()
                execute(url)
            } catch (e: Exception) {
                null
            }
        }

    suspend fun fetchForecast(lat: Double, lon: Double, days: Int = 7): List<DailyPoint>? =
        withContext(Dispatchers.IO) {
            try {
                val url = HttpUrl.Builder()
                    .scheme("https").host("api.open-meteo.com").addPathSegments("v1/forecast")
                    .addQueryParameter("latitude", lat.toString())
                    .addQueryParameter("longitude", lon.toString())
                    .addQueryParameter("daily", DAILY_FIELDS)
                    .addQueryParameter("forecast_days", days.toString())
                    .addQueryParameter("timezone", "Asia/Tashkent")
                    .build()
                execute(url)
            } catch (e: Exception) {
                null
            }
        }

    private fun execute(url: HttpUrl): List<DailyPoint>? {
        val request = Request.Builder().url(url).build()
        client.newCall(request).execute().use { response ->
            if (!response.isSuccessful) return null
            val body = response.body?.string() ?: return null
            return parseDaily(body)
        }
    }

    private fun parseDaily(body: String): List<DailyPoint> {
        val json = JSONObject(body)
        val daily = json.optJSONObject("daily") ?: return emptyList()
        val dates = daily.optJSONArray("time") ?: return emptyList()
        val tMax = daily.optJSONArray("temperature_2m_max")
        val tMin = daily.optJSONArray("temperature_2m_min")
        val precip = daily.optJSONArray("precipitation_sum")
        val humidity = daily.optJSONArray("relative_humidity_2m_mean")

        val points = mutableListOf<DailyPoint>()
        for (i in 0 until dates.length()) {
            val maxVal = tMax?.optDouble(i, Double.NaN) ?: Double.NaN
            val minVal = tMin?.optDouble(i, Double.NaN) ?: Double.NaN
            if (maxVal.isNaN() || minVal.isNaN()) continue
            points += DailyPoint(
                date = LocalDate.parse(dates.optString(i)),
                tMax = maxVal, tMin = minVal,
                precip = (precip?.optDouble(i, 0.0) ?: 0.0).let { if (it.isNaN()) 0.0 else it },
                humidity = (humidity?.optDouble(i, 55.0) ?: 55.0).let { if (it.isNaN()) 55.0 else it },
            )
        }
        return points
    }
}
