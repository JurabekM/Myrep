package uz.sectorverify.model

import org.junit.jupiter.api.Assertions.assertEquals
import org.junit.jupiter.api.Test

class SmokeTest {
    @Test
    fun moduleName() = assertEquals("model", ModuleInfo.NAME)
}
