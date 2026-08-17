package com.smartmoliya.app

import org.junit.Assert.assertEquals
import org.junit.Test

class ExampleUnitTest {
    @Test
    fun appPackageName_isCorrect() {
        assertEquals("com.smartmoliya.app", javaClass.`package`?.name)
    }
}
