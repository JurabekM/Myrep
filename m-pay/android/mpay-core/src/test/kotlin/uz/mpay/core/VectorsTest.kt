package uz.mpay.core

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Test
import java.io.File

/** Rust bilan umumiy vektorlar: `testvectors/tlv-vectors.json` va `testvectors/emv-kat.json`. */
class VectorsTest {
    private val dir = File(System.getenv("MPAY_TESTVECTORS") ?: "../../testvectors")

    private fun load(name: String) = JSONObject(File(dir, name).readText(Charsets.UTF_8))

    private fun node(j: JSONObject): Tlv {
        val tag = j.getString("tag").toInt(16)
        return if (j.has("children")) {
            val c = j.getJSONArray("children")
            Tlv.Constructed(tag, List(c.length()) { node(c.getJSONObject(it)) })
        } else {
            Tlv.Primitive(tag, Hex.decode(j.getString("value")))
        }
    }

    private fun repeat(j: JSONObject, prefix: String): ByteArray =
        Hex.decode(prefix) + ByteArray(j.getInt("count")) { Hex.decode(j.getString("byte"))[0] }

    @Test
    fun tlvVectorsMatchRust() {
        val d = load("tlv-vectors.json")
        val valid = d.getJSONArray("valid")
        for (i in 0 until valid.length()) {
            val c = valid.getJSONObject(i)
            val name = c.getString("name")
            val (bytes, want) = if (c.has("hex_repeat")) {
                val r = c.getJSONObject("hex_repeat"); val t = c.getJSONObject("tree_repeat")
                repeat(r, r.getString("prefix")) to listOf<Tlv>(Tlv.Primitive(t.getString("tag").toInt(16), repeat(t, "")))
            } else {
                val tree: JSONArray = c.getJSONArray("tree")
                Hex.decode(c.getString("hex")) to List(tree.length()) { node(tree.getJSONObject(it)) }
            }
            val got = Tlv.parseAll(bytes)
            assertEquals(name, want, got)
            val canonical = if (c.has("canonical")) Hex.decode(c.getString("canonical")) else bytes
            assertArrayEquals(name, canonical, Tlv.encodeAll(got))
        }
        val invalid = d.getJSONArray("invalid")
        for (i in 0 until invalid.length()) {
            val c = invalid.getJSONObject(i)
            try {
                Tlv.parseAll(Hex.decode(c.getString("hex")))
                fail("${c.getString("name")}: rad etilishi kerak edi")
            } catch (e: TlvException) {
                // kutilgan
            }
        }
        val dol = d.getJSONArray("dol").getJSONObject(0)
        val entries = Tlv.parseDol(Hex.decode(dol.getString("hex")))
        assertEquals(Emv.PDOL, entries)
        assertArrayEquals(Hex.decode(dol.getString("hex")), Tlv.encodeDol(entries))
    }

    @Test
    fun emvKatMatchesRustAndPython() {
        val cases = load("emv-kat.json").getJSONArray("cases")
        assertTrue(cases.length() >= 3)
        for (i in 0 until cases.length()) {
            val c = cases.getJSONObject(i)
            val name = c.getString("name")
            val mk = MpayScheme.tokenMasterKey(Hex.decode(c.getString("imk")), c.getString("dpan"), c.getInt("psn"))
            assertArrayEquals(name, Hex.decode(c.getString("token_master_key")), mk)
            val luk = MpayScheme.luk(mk, c.getLong("luk_seq"))
            assertArrayEquals(name, Hex.decode(c.getString("luk")), luk)
            val sk = MpayScheme.sessionKey(luk, c.getInt("atc"))
            assertArrayEquals(name, Hex.decode(c.getString("session_key")), sk)
            val t = c.getJSONObject("terminal")
            val td = TerminalData(
                amountMinor = t.getLong("amount_minor"),
                otherAmountMinor = t.getLong("other_amount_minor"),
                country = t.getInt("country"),
                tvr = Hex.decode(t.getString("tvr")),
                currency = t.getInt("currency"),
                date = Hex.decode(t.getString("date_yymmdd")),
                txnType = t.getInt("txn_type"),
                un = Hex.decode(t.getString("un")),
            )
            val pdol = td.toPdolData()
            assertArrayEquals(name, Hex.decode(c.getString("pdol_data")), pdol)
            val iad = Iad.parse(Hex.decode(c.getString("iad")))
            val cdol = Cdol.data(pdol, Emv.AIP, c.getInt("atc"), iad)
            assertArrayEquals(name, Hex.decode(c.getString("cdol")), cdol)
            val arqc = MpayScheme.arqc(sk, cdol)
            assertArrayEquals(name, Hex.decode(c.getString("arqc")), arqc)
            val arc = c.getString("arc").toByteArray(Charsets.US_ASCII)
            assertArrayEquals(name, Hex.decode(c.getString("arpc")), MpayScheme.arpc(sk, arqc, arc))
            assertTrue(MpayScheme.verifyIssuerAuth(sk, arqc, Hex.decode(c.getString("arpc")) + arc))
        }
    }

    @Test
    fun track2AndBcd() {
        val t2 = Track2.encode("9900770000001230", "2912")
        assertEquals(14, t2.size)
        assertEquals("9900770000001230" to "2912", Track2.decode(t2))
        assertArrayEquals(Hex.decode("000001250000"), Emv.toBcd(1_250_000, 6))
        assertEquals(860L, Emv.fromBcd(Hex.decode("0860")))
        assertEquals("990077******1230", maskPan("9900770000001230"))
    }
}
