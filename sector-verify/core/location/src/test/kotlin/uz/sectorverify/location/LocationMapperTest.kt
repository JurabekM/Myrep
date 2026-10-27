package uz.sectorverify.location

import android.location.Location
import io.kotest.matchers.shouldBe
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner

@RunWith(RobolectricTestRunner::class)
class LocationMapperTest {
    @Test
    fun mapsAllFields() {
        val l = Location("gps").apply {
            latitude = 40.1
            longitude = 65.3
            accuracy = 4.5f
            speed = 1.5f
            bearing = 90f
            time = 1_790_000_000_000
            elapsedRealtimeNanos = 123_000_000_000
        }
        val f = LocationMapper.toFix(l)
        f.tNanos shouldBe 123_000_000_000
        f.utcMs shouldBe 1_790_000_000_000
        f.lat shouldBe 40.1
        f.accM shouldBe 4.5
        f.speedMps shouldBe 1.5
        f.bearingDeg shouldBe 90.0
    }

    @Test
    fun missingOptionalFields() {
        val f = LocationMapper.toFix(Location("gps").apply { latitude = 1.0 })
        f.accM shouldBe LocationMapper.UNKNOWN_ACCURACY_M
        f.speedMps shouldBe null
        f.bearingDeg shouldBe null
    }
}
