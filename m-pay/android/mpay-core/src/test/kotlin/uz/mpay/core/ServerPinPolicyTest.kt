package uz.mpay.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

class ServerPinPolicyTest {
    private val a = "a".repeat(64)
    private val b = "B".repeat(64)
    private val c = "c".repeat(64)

    @Test
    fun pinnedSetAcceptsAnyMemberCaseInsensitive() {
        val p = ServerPinPolicy(listOf(a, b), allowTofu = true)
        assertEquals(ServerPinPolicy.Accept(false), p.check(a, null))
        assertEquals(ServerPinPolicy.Accept(false), p.check(b.lowercase(), null))
        // Pin bor — TOFU e'tiborga olinmaydi, begona barmoq izi rad.
        assertThrows(PinException::class.java) { p.check(c, c) }
    }

    @Test
    fun tofuOnlyWhenAllowed() {
        val tofu = ServerPinPolicy(emptyList(), allowTofu = true)
        assertEquals(ServerPinPolicy.Accept(true), tofu.check(a, null))
        assertEquals(ServerPinPolicy.Accept(false), tofu.check(a, a))
        assertThrows(PinException::class.java) { tofu.check(c, a) }

        val strict = ServerPinPolicy(emptyList(), allowTofu = false)
        assertThrows(PinException::class.java) { strict.check(a, null) }
    }

    @Test
    fun buildConfigListParsingAndValidation() {
        assertEquals(listOf(a, b), ServerPinPolicy.parseList(" $a, $b ,"))
        assertEquals(emptyList<String>(), ServerPinPolicy.parseList(""))
        assertThrows(IllegalArgumentException::class.java) { ServerPinPolicy(listOf("abc"), false) }
        assertThrows(IllegalArgumentException::class.java) { ServerPinPolicy(listOf("z".repeat(64)), false) }
    }
}
