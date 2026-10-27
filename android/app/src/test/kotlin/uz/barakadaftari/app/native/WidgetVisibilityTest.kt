package uz.barakadaftari.app.native

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class WidgetVisibilityTest {
    @Test
    fun lockedHidesAmounts() {
        // 0 — ilova qulflangan yoki qayta ishga tushgan.
        assertFalse(WidgetVisibility.showAmounts(0L, 1_000L))
    }

    @Test
    fun visibleUntilTimeout() {
        val until = 10_000L
        assertTrue(WidgetVisibility.showAmounts(until, 9_999L))
        assertFalse(WidgetVisibility.showAmounts(until, 10_000L))
        assertFalse(WidgetVisibility.showAmounts(until, 20_000L))
    }

    @Test
    fun unlockedForeground() {
        assertTrue(WidgetVisibility.showAmounts(Long.MAX_VALUE, System.currentTimeMillis()))
    }
}
