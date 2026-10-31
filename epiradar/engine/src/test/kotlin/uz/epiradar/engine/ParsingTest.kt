package uz.epiradar.engine

import uz.epiradar.engine.Fixtures.classifier
import uz.epiradar.engine.model.SignalFlag
import uz.epiradar.engine.parse.Html
import uz.epiradar.engine.parse.RssParser
import uz.epiradar.engine.sources.CdcTravelSource
import uz.epiradar.engine.sources.EcdcSource
import uz.epiradar.engine.sources.SignalFactory
import uz.epiradar.engine.sources.WhoDonSource
import java.time.Instant
import kotlin.test.Test
import kotlin.test.assertEquals
import kotlin.test.assertFailsWith
import kotlin.test.assertFalse
import kotlin.test.assertNull
import kotlin.test.assertTrue

class ParsingTest {
    private val factory = SignalFactory(classifier)

    @Test
    fun `rss parser reads CDC feed`() {
        val items = RssParser.parse(Fixtures.text("cdc_travel_notices.xml"))
        assertEquals(22, items.size)
        assertEquals("Level 1 - Ebola Bundibugyo Virus Disease in Kenya", items[0].title)
        assertEquals(Instant.parse("2026-10-19T04:00:00Z"), items[0].pubDate)
    }

    @Test
    fun `rss parser rejects doctype entities`() {
        val xxe =
            """<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]>""" +
                """<rss><channel><item><title>&x;</title><link>https://a</link></item></channel></rss>"""
        assertFailsWith<Exception> { RssParser.parse(xxe) }
    }

    @Test
    fun `html is reduced to text including double-encoded markup`() {
        assertEquals("Ebola & Marburg 'update'", Html.toText("<p>Ebola &amp;amp; Marburg &#39;update&#39;</p>"))
        assertEquals("a b", Html.toText("&lt;span&gt;a&lt;/span&gt; <b>b</b>"))
    }

    @Test
    fun `who don feed yields classified signals`() {
        val signals = WhoDonSource(factory).parse(Fixtures.text("who_don.json"))
        assertEquals(12, signals.size)
        val bvd = signals.first()
        assertEquals("who:2026-DON622", bvd.id)
        assertEquals("ebola", bvd.diseaseId)
        assertEquals(listOf("COD", "KEN", "NGA"), bvd.countries.take(3))
        assertTrue(SignalFlag.MULTI_COUNTRY in bvd.flags)
        assertTrue(SignalFlag.ESCALATING in bvd.flags, "summary says 'expanded geographically'")
        assertEquals("https://www.who.int/emergencies/disease-outbreak-news/item/2026-DON622", bvd.url)

        val pneumonia = signals.first { it.title.startsWith("Pneumonia of undetermined") }
        assertEquals("disease_x", pneumonia.diseaseId)
        assertEquals("RUS", pneumonia.countries.first())
        assertTrue(SignalFlag.UNKNOWN_ETIOLOGY in pneumonia.flags)

        val mers = signals.first { it.diseaseId == "mers" }
        assertEquals(listOf("SAU"), mers.countries.take(1))
    }

    @Test
    fun `cdc notices carry travel level and country list`() {
        val signals = CdcTravelSource(factory).parse(Fixtures.text("cdc_travel_notices.xml"))
        assertEquals(22, signals.size)
        val l4 = signals.first { it.travelLevel == 4 }
        assertEquals("ebola", l4.diseaseId)
        assertEquals(listOf("COD"), l4.countries)
        val dengue = signals.first { it.title == "Global Dengue" }
        assertEquals("dengue", dengue.diseaseId)
        assertTrue(dengue.countries.size >= 3, "country list: ${dengue.countries}")
        assertTrue(SignalFlag.MULTI_COUNTRY in dengue.flags)
        val yf = signals.first { it.title == "Yellow Fever in Ghana" }
        assertEquals(2, yf.travelLevel)
        assertEquals(listOf("GHA"), yf.countries)
    }

    @Test
    fun `ecdc epidemiological updates are parsed`() {
        val signals = EcdcSource(factory).parse(Fixtures.text("ecdc_epi_updates.xml"), requireDisease = false)
        assertTrue(signals.isNotEmpty())
        val ebola = signals.first()
        assertEquals("ebola", ebola.diseaseId)
        assertTrue("COD" in ebola.countries)
    }

    @Test
    fun `classifier prefers the most specific disease`() {
        assertEquals("avian_flu", classifier.disease("Avian Influenza A(H5N1) - Cambodia"))
        assertEquals("influenza", classifier.disease("Seasonal influenza update"))
        assertEquals("covid19", classifier.disease("Severe acute respiratory syndrome coronavirus 2 variant"))
        assertEquals("sars", classifier.disease("Severe acute respiratory syndrome (SARS) cluster"))
        assertEquals("cchf", classifier.disease("Crimean-Congo haemorrhagic fever - Iraq"))
        assertEquals("other", classifier.disease("Annual report on preparedness"))
    }

    @Test
    fun `country matching respects word and longest-name boundaries`() {
        assertEquals(listOf("PNG"), classifier.countries("Cholera - Papua New Guinea"))
        assertEquals(listOf("NGA", "NER"), classifier.countries("Cases in Nigeria and Niger"))
        assertEquals(listOf("COD", "COG"), classifier.countries("the Democratic Republic of the Congo and the Republic of the Congo"))
        assertEquals(listOf("CIV"), classifier.countries("Dengue in Côte d'Ivoire"))
        assertEquals(emptyList(), classifier.countries("Turkey farm outbreak in Somaliland region uk"))
        assertEquals(listOf("TUR"), classifier.countries("Türkiye"))
    }

    @Test
    fun `negated flags are ignored`() {
        val f = classifier.flags("There is no evidence of human-to-human transmission. Two deaths were reported.")
        assertFalse(SignalFlag.HUMAN_TO_HUMAN in f)
        assertTrue(SignalFlag.DEATHS in f)
        assertTrue(SignalFlag.HUMAN_TO_HUMAN in classifier.flags("Limited human-to-human transmission was observed"))
    }

    @Test
    fun `dates tolerate bad input`() {
        assertNull(uz.epiradar.engine.parse.Dates.rfc1123("yesterday"))
        assertNull(uz.epiradar.engine.parse.Dates.iso(""))
    }
}
