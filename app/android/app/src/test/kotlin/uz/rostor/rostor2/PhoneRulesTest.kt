package uz.rostor.rostor2

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.rostor.rostor2.call.CallPolicy
import uz.rostor.rostor2.call.PhoneIndex
import uz.rostor.rostor2.call.PhoneNumbers
import uz.rostor.rostor2.call.PhoneRules
import java.io.File

/** Qo'ng'iroq Qalqoni: umumiy KAT (Dart bilan bir xil) va haqiqiy registry bo'yicha qoidalar. */
class PhoneRulesTest {
    private val kat = JSONObject(File("../../test/fixtures/phone_kat.json").readText())
    private val registry = File("../../../registry/registry.json").readText()
    private val idx = PhoneIndex.fromPayload(registry)
    private val policy = CallPolicy()

    private fun pairs(name: String): List<Pair<String, String?>> {
        val a = kat.getJSONArray(name)
        return (0 until a.length()).map { val p = a.getJSONArray(it); p.getString(0) to (if (p.isNull(1)) null else p.getString(1)) }
    }

    private fun codes(raw: String?, hidden: Boolean = false, verification: Int = 0, p: CallPolicy = policy, i: PhoneIndex = idx) =
        PhoneRules.evaluate(raw, hidden, verification, i, p).findings.map { it.code }

    @Test fun normalizeMatchesSharedKat() {
        for ((input, expected) in pairs("normalize")) assertEquals("normalize($input)", expected, PhoneNumbers.normalize(input))
    }

    @Test fun lookupMatchesSharedKat() {
        for ((n, org) in pairs("lookup")) assertEquals("lookup($n)", org, idx.official[n]?.firstOrNull()?.orgId)
    }

    @Test fun displayMatchesSharedKat() {
        for ((n, shown) in pairs("display")) assertEquals(shown, PhoneNumbers.display(n))
    }

    @Test fun officialNumberIsInfoWithSpoofingWarning() {
        val v = PhoneRules.evaluate("+998712310880", false, 0, idx, policy)
        assertEquals(listOf("call.official"), v.findings.map { it.code })
        assertEquals("info", v.severity)
        assertTrue(v.findings[0].explain.contains("soxtalashtirish"))
        assertFalse(v.block)
        assertTrue(PhoneRules.shouldNotify(v, policy))
        assertFalse(PhoneRules.shouldNotify(v, policy.copy(notifyOfficial = false)))
    }

    @Test fun officialNumberFailingVerificationIsCritical() {
        val v = PhoneRules.evaluate("+998712310880", false, PhoneRules.VERIFY_FAILED, idx, policy)
        assertEquals(listOf("call.official_spoofed"), v.findings.map { it.code })
        assertEquals("critical", v.severity)
    }

    @Test fun unknownLocalNumberIsSilent() {
        val v = PhoneRules.evaluate("901234567", false, 0, idx, policy)
        assertEquals(listOf("call.no_signal"), v.findings.map { it.code })
        assertFalse(PhoneRules.shouldNotify(v, policy))
        assertEquals("+998901234567", v.normalized)
    }

    @Test fun internationalWarnsAndOptionallySilences() {
        assertEquals(listOf("call.international"), codes("+79123456789"))
        val v = PhoneRules.evaluate("+79123456789", false, 0, idx, policy.copy(silenceInternational = true))
        assertTrue(v.silence)
        assertFalse(v.block)
        assertEquals("Rossiya", PhoneNumbers.country("+79123456789"))
        assertEquals("Qozog'iston", PhoneNumbers.country("+77011234567"))
    }

    @Test fun hiddenNumber() {
        assertEquals(listOf("call.hidden"), codes("+998901234567", hidden = true))
        assertEquals(listOf("call.hidden"), codes(null))
    }

    @Test fun maliciousAndUserBlockedAreRejected() {
        val mal = JSONObject(registry).apply {
            getJSONObject("malicious").put("phones", JSONArray().put("+998 90 000 00 01").put(JSONObject().put("number", "998900000002")))
        }
        val i = PhoneIndex.fromPayload(mal.toString())
        val v = PhoneRules.evaluate("900000001", false, 0, i, policy)
        assertEquals("critical", v.severity)
        assertTrue(v.block)
        assertTrue(PhoneRules.evaluate("+998900000002", false, 0, i, policy).block)
        assertFalse(PhoneRules.evaluate("900000001", false, 0, i, policy.copy(blockFlagged = false)).block)

        val u = PhoneRules.evaluate("+998931112233", false, 0, idx, policy.copy(userBlocked = setOf("+998931112233")))
        assertEquals(listOf("call.user_blocked"), u.findings.map { it.code })
        assertTrue(u.block)
        // Bloklangan bo'lsa, ovozsiz qilish emas — rad etish.
        val both = PhoneRules.evaluate("+79123456789", false, 0, idx, CallPolicy(silenceInternational = true, userBlocked = setOf("+79123456789")))
        assertTrue(both.block)
        assertFalse(both.silence)
    }

    @Test fun emptyIndexStillWorks() {
        assertEquals(listOf("call.no_signal"), codes("+998712310880", i = PhoneIndex.EMPTY))
        assertNull(PhoneRules.evaluate("abc", false, 0, idx, policy).normalized)
    }
}
