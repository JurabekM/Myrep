package uz.havoradar.engine.net

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import java.io.ByteArrayOutputStream
import java.io.IOException
import java.io.InputStream
import java.net.HttpURLConnection
import java.net.URI
import java.util.zip.GZIPInputStream

/** Tarmoqdan matn olish. Testlarda soxta (fixture) bilan almashtiriladi. */
fun interface HttpFetcher {
    suspend fun get(url: String): String
}

class HttpException(
    val code: Int,
    url: String,
) : IOException("HTTP $code: $url")

/**
 * Tashqi kutubxonasiz HTTP mijoz (`HttpURLConnection`) — Android va JVM'da bir xil ishlaydi.
 * Faqat HTTPS, javob hajmi cheklangan, gzip qo'llab-quvvatlanadi.
 */
class UrlConnectionFetcher(
    private val userAgent: String = "HavoRadar/1.0 (+https://github.com/JurabekM/Myrep)",
    private val timeoutMs: Int = 20_000,
    private val maxBytes: Int = 2 * 1024 * 1024,
) : HttpFetcher {
    /**
     * Vaqtinchalik ulanish xatosida (mobil tarmoq, IPv6 marshruti uzilishi) bir marta qayta uriniladi.
     * Server javobi (HTTP xato kodi) qayta urinilmaydi — u darhol yuqoriga uzatiladi.
     */
    override suspend fun get(url: String): String {
        repeat(RETRIES) {
            try {
                return fetch(url)
            } catch (e: HttpException) {
                throw e
            } catch (_: IOException) {
                delay(RETRY_DELAY_MS)
            }
        }
        return fetch(url)
    }

    private suspend fun fetch(url: String): String =
        withContext(Dispatchers.IO) {
            val uri = URI(url)
            require(uri.scheme == "https") { "Faqat HTTPS: $url" }
            val conn = uri.toURL().openConnection() as HttpURLConnection
            try {
                conn.connectTimeout = timeoutMs
                conn.readTimeout = timeoutMs
                conn.instanceFollowRedirects = true
                conn.setRequestProperty("User-Agent", userAgent)
                conn.setRequestProperty("Accept", "application/json")
                conn.setRequestProperty("Accept-Encoding", "gzip")
                val code = conn.responseCode
                if (code != HttpURLConnection.HTTP_OK) {
                    throw HttpException(code, url)
                }
                val raw = conn.inputStream
                val stream = if ("gzip".equals(conn.contentEncoding, ignoreCase = true)) GZIPInputStream(raw) else raw
                stream.use { readLimited(it) }.toString(Charsets.UTF_8)
            } finally {
                conn.disconnect()
            }
        }

    private fun readLimited(input: InputStream): ByteArray {
        val out = ByteArrayOutputStream()
        val buf = ByteArray(16 * 1024)
        while (true) {
            val n = input.read(buf)
            if (n < 0) break
            out.write(buf, 0, n)
            if (out.size() > maxBytes) throw IOException("Javob juda katta (> $maxBytes bayt)")
        }
        return out.toByteArray()
    }

    private companion object {
        const val RETRIES = 1
        const val RETRY_DELAY_MS = 1_500L
    }
}
