package uz.epiradar.engine.parse

import org.w3c.dom.Element
import org.w3c.dom.Node
import java.io.StringReader
import java.time.Instant
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import java.time.format.DateTimeParseException
import javax.xml.parsers.DocumentBuilderFactory
import org.xml.sax.InputSource

data class RssItem(
    val title: String,
    val link: String,
    val description: String,
    val pubDate: Instant?,
    val guid: String,
)

/** RSS 2.0 o'quvchi. DTD/tashqi obyektlar o'chirilgan (XXE himoyasi). */
object RssParser {
    fun parse(xml: String): List<RssItem> {
        val factory = DocumentBuilderFactory.newInstance()
        // Android parseri ba'zi xususiyatlarni qo'llamaydi — har birini alohida, xatosiz sinaymiz.
        runCatching { factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true) }
        runCatching { factory.setFeature("http://xml.org/sax/features/external-general-entities", false) }
        runCatching { factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false) }
        runCatching { factory.isExpandEntityReferences = false }
        factory.isNamespaceAware = false
        val clean = xml.trimStart('﻿', ' ', '\n', '\r', '\t')
        val doc = factory.newDocumentBuilder().parse(InputSource(StringReader(clean)))
        val items = doc.getElementsByTagName("item")
        return (0 until items.length).mapNotNull { i ->
            val el = items.item(i) as? Element ?: return@mapNotNull null
            val title = el.child("title")
            val link = el.child("link")
            if (title.isBlank() || link.isBlank()) return@mapNotNull null
            RssItem(
                title = Html.toText(title),
                link = link.trim(),
                description = Html.toText(el.child("description")),
                pubDate = Dates.rfc1123(el.child("pubDate")),
                guid = el.child("guid").ifBlank { link }.trim(),
            )
        }
    }

    private fun Element.child(tag: String): String {
        var n: Node? = firstChild
        while (n != null) {
            if (n is Element && n.tagName == tag) return n.textContent.orEmpty()
            n = n.nextSibling
        }
        return ""
    }
}

object Dates {
    fun rfc1123(text: String): Instant? {
        val t = text.trim()
        if (t.isEmpty()) return null
        return try {
            ZonedDateTime.parse(t, DateTimeFormatter.RFC_1123_DATE_TIME).toInstant()
        } catch (_: DateTimeParseException) {
            null
        }
    }

    fun iso(text: String?): Instant? {
        if (text.isNullOrBlank()) return null
        return try {
            Instant.parse(text.trim())
        } catch (_: DateTimeParseException) {
            null
        }
    }
}

/** HTML parchalarini oddiy matnga aylantirish (RSS tavsiflari uchun). */
object Html {
    private val tags = Regex("<[^>]+>")
    private val spaces = Regex("\\s+")
    private val entities =
        mapOf(
            "&nbsp;" to " ",
            "&amp;" to "&",
            "&lt;" to "<",
            "&gt;" to ">",
            "&quot;" to "\"",
            "&#39;" to "'",
            "&#039;" to "'",
            "&apos;" to "'",
            "&rsquo;" to "'",
            "&lsquo;" to "'",
            "&ldquo;" to "\"",
            "&rdquo;" to "\"",
            "&ndash;" to "–",
            "&mdash;" to "—",
        )
    private val numeric = Regex("&#(\\d{1,6});")

    fun toText(html: String): String {
        var s = tags.replace(html, " ")
        // Ichma-ich kodlangan HTML (RSS ichida &lt;p&gt;) — ikki marta tozalaymiz.
        repeat(2) {
            entities.forEach { (k, v) -> s = s.replace(k, v) }
            s = numeric.replace(s) { m -> m.groupValues[1].toIntOrNull()?.let { String(Character.toChars(it)) } ?: "" }
            s = tags.replace(s, " ")
        }
        return spaces.replace(s, " ").trim()
    }
}
