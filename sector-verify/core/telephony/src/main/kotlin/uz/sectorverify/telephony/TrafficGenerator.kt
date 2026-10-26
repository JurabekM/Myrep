package uz.sectorverify.telephony

import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn

sealed interface TrafficStatus {
    data object Disabled : TrafficStatus

    data class Ok(val httpCode: Int, val latencyMs: Long) : TrafficStatus

    data class Error(val reason: String) : TrafficStatus
}

/**
 * §7 TrafficGenerator: har [intervalMs] da HEAD so'rov UE'ni connected rejimda ushlab turadi, shunda TA xabar qilinadi.
 * Faqat HTTPS, query, body va foydalanuvchi ma'lumoti yo'q. Bu ilovadagi yagona tarmoq murojaati (§11).
 */
class TrafficGenerator(
    private val url: String,
    private val intervalMs: Long = DEFAULT_INTERVAL_MS,
    private val timeoutMs: Int = TIMEOUT_MS,
    private val open: (URL) -> HttpURLConnection = { it.openConnection() as HttpURLConnection },
) {
    fun run(): Flow<TrafficStatus> = flow {
        if (!isValidUrl(url)) {
            emit(TrafficStatus.Disabled)
            return@flow
        }
        while (true) {
            emit(ping())
            delay(intervalMs)
        }
    }.flowOn(Dispatchers.IO)

    internal fun ping(): TrafficStatus {
        val t0 = System.nanoTime()
        return try {
            val c = open(URL(url))
            try {
                c.requestMethod = "HEAD"
                c.instanceFollowRedirects = false
                c.useCaches = false
                c.connectTimeout = timeoutMs
                c.readTimeout = timeoutMs
                c.setRequestProperty("User-Agent", "SectorVerify")
                val code = c.responseCode
                TrafficStatus.Ok(code, (System.nanoTime() - t0) / NANOS_PER_MS)
            } finally {
                c.disconnect()
            }
        } catch (e: IOException) {
            TrafficStatus.Error(e.javaClass.simpleName)
        }
    }

    companion object {
        const val DEFAULT_INTERVAL_MS = 2000L
        private const val TIMEOUT_MS = 5000
        private const val NANOS_PER_MS = 1_000_000L

        /** Bo'sh → generator o'chiq; faqat host'i bor https URL'lar qabul qilinadi. */
        fun isValidUrl(url: String): Boolean {
            if (url.isBlank()) return false
            return runCatching { URL(url) }.getOrNull()?.let { it.protocol == "https" && it.host.isNotBlank() && it.query == null } == true
        }
    }
}
