package uz.sectorverify.analysis

import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SitePlan

object Fixtures {
    const val LAT = 40.1032
    const val LON = 65.3685
    const val SEC = 1_000_000_000L

    fun plan(vararg az: Double, arfcn: Int = 1300) = SitePlan(
        "NAV-0123",
        "Navoiy Markaz",
        LAT,
        LON,
        "43405",
        az.mapIndexed { i, a -> Sector("S${i + 1}", Rat.LTE, "B3", arfcn, 141 + i, a) },
    )

    fun fix(t: Long, bearing: Double, dist: Double, acc: Double = 4.0, speed: Double? = 1.4): GnssFix {
        val p = Geo.destination(LAT, LON, bearing, dist)
        return GnssFix(t, 1_790_000_000_000L + t / 1_000_000, p.lat, p.lon, acc, speed, null)
    }

    fun sample(t: Long, pci: Int = 141, rsrp: Double? = -90.0, ta: Int? = null, rx: Long? = t, registered: Boolean = false) =
        CellSample(t, Rat.LTE, 1300, pci, registered, rsrp, -10.0, 5.0, ta, null, null, rx)
}
