package uz.mpay.wallet.app

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.mpay.core.Txn
import javax.crypto.Mac
import javax.crypto.spec.SecretKeySpec

class FormatTest {
    @Test
    fun moneyPerLanguage() {
        assertEquals("12 500,00 so'm", Format.money(1_250_000, 860, Lang.UZ))
        assertEquals("12 500,00 сум", Format.money(1_250_000, 860, Lang.RU))
        assertEquals("12,500.00 UZS", Format.money(1_250_000, 860, Lang.EN))
        assertEquals("0,05 so'm", Format.money(5, 860, Lang.UZ))
        assertEquals("1 000 000,00 so'm", Format.money(100_000_000, 860, Lang.UZ))
        assertEquals("-7,00 so'm", Format.money(-700, 860, Lang.UZ))
        assertEquals("1.00 840", Format.money(100, 840, Lang.EN))
    }

    @Test
    fun cardInput() {
        assertEquals("9900 1200 0000 0014", Format.groupPan("9900120000000014"))
        assertEquals("9900 1", Format.groupPan("99001"))
        // Luhn: to'g'ri test PAN va bitta raqami o'zgargani.
        assertTrue(Format.luhnOk("4111111111111111"))
        assertFalse(Format.luhnOk("4111111111111112"))
        assertFalse(Format.luhnOk("41111"))
        assertFalse(Format.luhnOk("41111111111111a1"))
        assertEquals("3112", Format.mmyyToYymm("1231"))
        assertNull(Format.mmyyToYymm("1331"))
        assertNull(Format.mmyyToYymm("0031"))
        assertNull(Format.mmyyToYymm("123"))
        assertEquals("12/31", Format.expiry("3112"))
        assertEquals("•• 0014", Format.last4("990012******0014"))
    }

    @Test
    fun timeInTashkent() {
        // 2026-10-29 03:00:00 UTC = 08:00 Toshkent.
        assertEquals("08:00", Format.time(1_793_242_800, Lang.UZ))
        assertEquals("29.10.2026", Format.day(1_793_242_800))
    }
}

class PinPolicyTest {
    private val key = SecretKeySpec(ByteArray(32) { 3 }, "HmacSHA256")
    private val policy = PinPolicy { Mac.getInstance("HmacSHA256").run { init(key); doFinal(it) } }

    @Test
    fun rejectsTrivialPins() {
        listOf("111111", "123456", "654321", "12345", "1234567", "12a456").forEach { assertFalse(it, policy.valid(it)) }
        listOf("482915", "112233", "135790").forEach { assertTrue(it, policy.valid(it)) }
    }

    @Test
    fun verifierDoesNotContainPin() {
        val s = policy.create("482915", ByteArray(16) { 1 })
        assertFalse(String(s.verifier, Charsets.ISO_8859_1).contains("482915"))
        // Boshqa salt — boshqa tekshirgich.
        assertFalse(s.verifier.contentEquals(policy.create("482915", ByteArray(16) { 2 }).verifier))
    }

    @Test
    fun lockoutEscalatesAndResetsOnSuccess() {
        var s = policy.create("482915", ByteArray(16))
        var now = 1_000_000L
        repeat(4) {
            val (r, n) = policy.check(s, "000000", now)
            assertEquals(PinPolicy.Check.Wrong(it + 1, 0), r)
            s = n
        }
        val (r5, s5) = policy.check(s, "000000", now)
        assertEquals(PinPolicy.Check.Wrong(5, now + 30_000), r5)
        // Kutish paytida to'g'ri PIN ham qabul qilinmaydi.
        val (locked, _) = policy.check(s5, "482915", now + 10_000)
        assertEquals(PinPolicy.Check.Locked(now + 30_000), locked)
        now += 31_000
        val (r6, s6) = policy.check(s5, "000000", now)
        assertEquals(PinPolicy.Check.Wrong(6, now + 60_000), r6)
        now += 61_000
        val (ok, s7) = policy.check(s6, "482915", now)
        assertEquals(PinPolicy.Check.Ok, ok)
        assertEquals(0, s7.failures)
        assertEquals(15 * 60_000L, PinPolicy.lockout(12))
    }
}

class TxnWatcherTest {
    private fun t(id: String) = Txn(id, 1, 100, 860, "SHOP", "T1", "rrn", "APPROVED", "00", "APPROVED", false)

    @Test
    fun firstRunOnlySetsMarker() {
        val r = TxnWatcher.diff(listOf(t("c"), t("b"), t("a")), null)
        assertTrue(r.fresh.isEmpty())
        assertEquals("c", r.marker)
    }

    @Test
    fun newSinceMarker() {
        val r = TxnWatcher.diff(listOf(t("e"), t("d"), t("c"), t("b")), "c")
        assertEquals(listOf("e", "d"), r.fresh.map { it.id })
        assertEquals("e", r.marker)
        assertTrue(TxnWatcher.diff(listOf(t("e"), t("d")), "e").fresh.isEmpty())
        // Bo'sh sahifa — belgi saqlanadi.
        assertEquals("e", TxnWatcher.diff(emptyList(), "e").marker)
    }

    @Test
    fun markerOutOfPageIsCapped() {
        val page = (1..20).map { t("x$it") }
        val r = TxnWatcher.diff(page, "old")
        assertEquals(TxnWatcher.MAX, r.fresh.size)
        assertEquals("x1", r.marker)
    }
}
