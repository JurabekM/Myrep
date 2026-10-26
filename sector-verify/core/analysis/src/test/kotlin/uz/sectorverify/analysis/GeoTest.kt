package uz.sectorverify.analysis

import io.kotest.matchers.doubles.plusOrMinus
import io.kotest.matchers.shouldBe
import io.kotest.property.Arb
import io.kotest.property.arbitrary.double
import io.kotest.property.checkAll
import kotlinx.coroutines.runBlocking
import org.junit.jupiter.api.Test

class GeoTest {
    @Test
    fun `distance and bearing of known coordinates`() {
        // Land's End → John o'Groats (Movable Type reference: 968.9 km, 009°07′11″).
        Geo.distanceM(50.06639, -5.71472, 58.64389, -3.07) shouldBe (968_854.9 plusOrMinus 1.0)
        Geo.bearingDeg(50.06639, -5.71472, 58.64389, -3.07) shouldBe (9.1197 plusOrMinus 0.1)
        // Tashkent → Samarkand.
        Geo.distanceM(41.2995, 69.2401, 39.6542, 66.9597) shouldBe (265_826.5 plusOrMinus 1.0)
        Geo.bearingDeg(41.2995, 69.2401, 39.6542, 66.9597) shouldBe (227.259 plusOrMinus 0.1)
        // One degree of longitude on the equator.
        Geo.distanceM(0.0, 0.0, 0.0, 1.0) shouldBe (111_195.08 plusOrMinus 1.0)
        Geo.bearingDeg(0.0, 0.0, 0.0, 1.0) shouldBe (90.0 plusOrMinus 0.1)
        Geo.bearingDeg(0.0, 0.0, 1.0, 0.0) shouldBe (0.0 plusOrMinus 0.1)
        Geo.bearingDeg(0.0, 0.0, -1.0, 0.0) shouldBe (180.0 plusOrMinus 0.1)
        // A survey-scale point near a site.
        Geo.distanceM(40.1032, 65.3685, 40.1059, 65.3712) shouldBe (377.979 plusOrMinus 1.0)
        Geo.bearingDeg(40.1032, 65.3685, 40.1059, 65.3712) shouldBe (37.4104 plusOrMinus 0.1)
    }

    @Test
    fun `destination inverts distance and bearing`() = runBlocking {
        checkAll(Arb.double(0.0, 359.99), Arb.double(50.0, 2000.0)) { b, d ->
            val p = Geo.destination(40.1032, 65.3685, b, d)
            Geo.distanceM(40.1032, 65.3685, p.lat, p.lon) shouldBe (d plusOrMinus 0.01)
            Angles.diff(Geo.bearingDeg(40.1032, 65.3685, p.lat, p.lon), b) shouldBe (0.0 plusOrMinus 1e-6)
        }
    }

    @Test
    fun `angle helpers`() {
        Angles.norm360(-10.0) shouldBe 350.0
        Angles.norm360(720.0) shouldBe 0.0
        Angles.norm360(-1e-18) shouldBe 0.0
        Angles.wrap180(190.0) shouldBe -170.0
        Angles.wrap180(180.0) shouldBe -180.0
        Angles.diff(10.0, 350.0) shouldBe 20.0
        Angles.diff(350.0, 10.0) shouldBe -20.0
        Geo.destination(0.0, 179.9999, 90.0, 1000.0).lon shouldBe (-179.991 plusOrMinus 0.001)
    }
}
