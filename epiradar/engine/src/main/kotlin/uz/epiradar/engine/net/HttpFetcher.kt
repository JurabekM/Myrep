package uz.epiradar.engine.net

import kotlinx.coroutines.Dispatchers
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
    private val userAgent: String = "EpiRadar/1.0 (+https://github.com/JurabekM/Myrep)",
    private val timeoutMs: Int = 20_000,
    private val maxBytes: Int = 4 * 1024 * 1024,
) : HttpFetcher {
    override suspend fun get(url: String): String =
        withContext(Dispatchers.IO) {
            val uri = URI(url)
            require(uri.scheme == "https") { "Faqat HTTPS: $url" }
            val conn = uri.toURL().openConnection() as HttpURLConnection
            try {
                conn.connectTimeout = timeoutMs
                conn.readTimeout = timeoutMs
                conn.instanceFollowRedirects = true
                conn.setRequestProperty("User-Agent", userAgent)
                conn.setRequestProperty("Accept", "application/json, application/rss+xml, application/xml, text/xml, */*")
                conn.setRequestProperty("Accept-Encoding", "gzip")
                val code = conn.responseCode
                // 206 — ba'zi OData serverlari $top bilan qisman javob qaytaradi.
                if (code != HttpURLConnection.HTTP_OK && code != HttpURLConnection.HTTP_PARTIAL) {
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
}
