package uz.sectorverify.telephony

import io.kotest.matchers.nulls.shouldBeNull
import io.kotest.matchers.nulls.shouldNotBeNull
import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import uz.sectorverify.model.Rat
import uz.sectorverify.telephony.CellNormalizer.UNAVAILABLE
import uz.sectorverify.telephony.CellNormalizer.UNAVAILABLE_LONG

class CellNormalizerTest {
    private val lte = RawCell(Rat.LTE, true, 5_000, 1300, 141, -95, -11, 12, 4, 123_456, 101)
    private val nr = RawCell(Rat.NR, false, 6_000, 636_666, 900, -100, -12, 10, UNAVAILABLE, 99, 7)

    @Test
    fun `valid LTE and NR cells are copied`() {
        val s = CellNormalizer.normalize(lte, 9_000).shouldNotBeNull()
        s.tNanos shouldBe 5_000
        s.rxNanos shouldBe 9_000
        s.rsrp shouldBe -95.0
        s.rsrq shouldBe -11.0
        s.sinr shouldBe 12.0
        s.ta shouldBe 4
        s.ci shouldBe 123_456
        s.tac shouldBe 101
        s.registered shouldBe true
        val n = CellNormalizer.normalize(nr, 9_000).shouldNotBeNull()
        n.pci shouldBe 900
        n.rsrp shouldBe -100.0
        n.ta.shouldBeNull()
    }

    @Test
    fun `UNAVAILABLE and out of range values become null`() {
        val s = CellNormalizer.normalize(
            lte.copy(rsrp = UNAVAILABLE, rsrq = 10, sinr = UNAVAILABLE, ta = 2000, ci = UNAVAILABLE_LONG, tac = UNAVAILABLE),
            0,
        )!!
        s.rsrp.shouldBeNull()
        s.rsrq.shouldBeNull()
        s.sinr.shouldBeNull()
        s.ta.shouldBeNull()
        s.ci.shouldBeNull()
        s.tac.shouldBeNull()
        CellNormalizer.normalize(lte.copy(rsrp = -141), 0)!!.rsrp.shouldBeNull()
        CellNormalizer.normalize(lte.copy(rsrp = -44), 0)!!.rsrp shouldBe -44.0
        CellNormalizer.normalize(nr.copy(rsrp = -156), 0)!!.rsrp shouldBe -156.0
        CellNormalizer.normalize(nr.copy(rsrp = -30), 0)!!.rsrp.shouldBeNull()
    }

    @Test
    fun `invalid PCI or ARFCN drops the sample`() {
        CellNormalizer.normalize(lte.copy(pci = 504), 0).shouldBeNull()
        CellNormalizer.normalize(lte.copy(pci = UNAVAILABLE), 0).shouldBeNull()
        CellNormalizer.normalize(lte.copy(pci = -1), 0).shouldBeNull()
        CellNormalizer.normalize(nr.copy(pci = 1008), 0).shouldBeNull()
        CellNormalizer.normalize(nr.copy(pci = 1007), 0).shouldNotBeNull()
        CellNormalizer.normalize(lte.copy(arfcn = UNAVAILABLE), 0).shouldBeNull()
    }

    @Test
    fun `deduplicator drops repeated scans and forgets old ones`() {
        val d = Deduplicator(windowNanos = 10)
        val s = CellNormalizer.normalize(lte, 0)!!
        d.filter(listOf(s), 0).size shouldBe 1
        d.filter(listOf(s, s.copy(tNanos = 6_000)), 1).size shouldBe 1
        d.filter(listOf(s), 100).size shouldBe 1 // window expired
    }

    @Test
    fun `subscription is chosen by plan MCC MNC`() {
        val sims = listOf(SimInfo(1, "434", "05", "Ucell", 0), SimInfo(2, "434", "07", "Mobiuz", 1), SimInfo(3, null, null, null, 2))
        SubscriptionSelector.select(sims, "43407")!!.subscriptionId shouldBe 2
        SubscriptionSelector.select(sims, " 43405 ")!!.subscriptionId shouldBe 1
        SubscriptionSelector.select(sims, "43404").shouldBeNull()
        sims[2].mccMnc.shouldBeNull()
    }
}
