package uz.mpay.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class CardBookTest {
    private fun card(id: String, dpan: String) =
        CardProfile(id, dpan, "3112", 1, mutableListOf(CardLuk(1, ByteArray(16) { 7 }, 4_000_000_000, 10)), 3, 5_000_000, 1_900_000_000)

    private fun token(id: String, state: String, by: String? = null) =
        WalletToken(id, state, "990077******1111", "990012******0014", "3112", 1, 2, by)

    @Test
    fun firstCardIsDefaultAndTapSkipsSuspended() {
        val b = CardBook()
        b.put(card("tok_a", "9900770000000011"))
        b.put(card("tok_b", "9900770000000029"))
        assertEquals("tok_a", b.defaultId)
        assertEquals("tok_a", b.tapCard()!!.tokenId)
        assertEquals("tok_b", b.tapCard("tok_b")!!.tokenId)
        b.setDefault("tok_b")
        assertEquals("tok_b", b.tapCard()!!.tokenId)

        b.applyServer(listOf(token("tok_a", "ACTIVE"), token("tok_b", "SUSPENDED", "BANK")))
        // Asosiy to'xtatilgan — tap'da karta yo'q (boshqasiga jim o'tmaydi), tanlangan faoli — ishlaydi.
        assertNull(b.tapCard())
        assertEquals("tok_a", b.tapCard("tok_a")!!.tokenId)
        assertNull(b.tapCard("tok_b"))
        val v = b.view(nowUnix = 1)
        assertEquals(listOf("ACTIVE", "SUSPENDED"), v.map { it.state })
        assertEquals(listOf(false, true), v.map { it.isDefault })
        assertEquals(listOf(true, false), v.map { it.payable })
        assertEquals("990077******0011", v[0].dpanMasked)
        assertEquals(1, v[0].luksLeft)
    }

    @Test
    fun serverSyncReportsChangesAndRemovesDeleted() {
        val b = CardBook()
        b.put(card("tok_a", "9900770000000011"))
        b.put(card("tok_b", "9900770000000029"))
        // Birinchi moslash: B ni bank to'xtatgan — o'zgarish (ACTIVE → SUSPENDED); qurilmada yo'q C — ro'yxatda.
        val c1 = b.applyServer(listOf(token("tok_a", "ACTIVE"), token("tok_b", "SUSPENDED", "BANK"), token("tok_c", "ACTIVE")))
        assertEquals(listOf<CardChange>(CardChange.State("tok_b", "ACTIVE", "SUSPENDED", "BANK")), c1)
        assertEquals(listOf(true, true, false), b.view().map { it.onDevice })
        // Takroriy moslash — o'zgarish yo'q.
        assertTrue(b.applyServer(listOf(token("tok_a", "ACTIVE"), token("tok_b", "SUSPENDED", "BANK"))).isEmpty())
        // Bank A ni o'chirdi (ro'yxatda yo'q) — qurilmadan ham o'chadi, asosiy B ga o'tadi.
        val c2 = b.applyServer(listOf(token("tok_b", "ACTIVE")))
        assertEquals(
            listOf(CardChange.Removed("tok_a", "990077******0011"), CardChange.State("tok_b", "SUSPENDED", "ACTIVE", null)),
            c2,
        )
        assertEquals("tok_b", b.defaultId)
        assertEquals(listOf("tok_b"), b.view().map { it.tokenId })
        // Foydalanuvchi o'chirdi — server javobi DELETED.
        b.applyServer(token("tok_b", "DELETED"))
        assertEquals(0, b.size)
        assertNull(b.defaultId)
        assertNull(b.tapCard())
    }

    @Test
    fun jsonRoundTripAndV1Migration() {
        val b = CardBook()
        b.put(card("tok_a", "9900770000000011"))
        b.put(card("tok_b", "9900770000000029"))
        b.setDefault("tok_b")
        b.applyServer(listOf(token("tok_a", "SUSPENDED", "DEVICE"), token("tok_b", "ACTIVE")))
        val r = CardBook.fromJson(b.toJson())
        assertEquals(b.view(1), r.view(1))
        assertEquals("tok_b", r.defaultId)
        val p = r.profile("tok_a")!!
        assertEquals(3, p.atc)
        assertEquals(1_900_000_000L, p.renewAfter)
        assertTrue(p.luks[0].key.contentEquals(ByteArray(16) { 7 }))

        // 1-versiya: bitta profil — yagona va asosiy karta bo'ladi.
        val v1 = """{"token_id":"tok_old","dpan":"9900770000000037","expiry":"2912","psn":1,"atc":9,"cvm":100,
            "renew_after":null,"luks":[{"seq":4,"key":"00112233445566778899aabbccddeeff","exp":5,"uses":2}]}"""
        val m = CardBook.fromJson(v1)
        assertEquals("tok_old", m.defaultId)
        assertEquals(9, m.profile("tok_old")!!.atc)
        assertNull(m.profile("tok_old")!!.renewAfter)
        assertFalse(m.server("tok_old") != null)
    }
}
