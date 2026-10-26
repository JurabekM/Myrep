package uz.sectorverify.feature.survey

import io.kotest.matchers.shouldBe
import org.junit.jupiter.api.Test
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SitePlan
import uz.sectorverify.telephony.SimInfo

class PreCheckTest {
    private val plan = SitePlan("A", "A", 40.0, 65.0, "43405", listOf(Sector("S1", Rat.LTE, "B3", 1300, 141, 0.0)))
    private val caps = DeviceCapabilities("P", "G", 35, null, null, 60, 0.9, true, true, true, false, 0)
    private val good = PreCheckInput(
        plan = plan,
        locationGranted = true,
        phoneStateGranted = true,
        notificationsGranted = true,
        sims = listOf(SimInfo(3, "434", "05", "Ucell", 0)),
        gpsEnabled = true,
        gpsAccuracyM = 5.0,
        capabilities = caps,
        visibleCells = setOf(CellKey(Rat.LTE, 1300, 141)),
        servingRatsLte = true,
        trafficUrl = "https://example.com",
    )

    private fun PreCheckResult.status(id: CheckId) = items.first { it.id == id }.status

    @Test
    fun `all good enables start and picks the SIM`() {
        val r = PreCheck.evaluate(good)
        r.canStart shouldBe true
        r.subscription!!.subscriptionId shouldBe 3
        r.items.all { it.status == CheckStatus.OK } shouldBe true
    }

    @Test
    fun `blocking and warning problems`() {
        PreCheck.evaluate(good.copy(locationGranted = false)).canStart shouldBe false
        PreCheck.evaluate(good.copy(sims = emptyList())).let {
            it.canStart shouldBe false
            it.status(CheckId.SIM) shouldBe CheckStatus.BLOCK
        }
        PreCheck.evaluate(good.copy(gpsEnabled = false)).canStart shouldBe false
        val warn = PreCheck.evaluate(
            good.copy(
                notificationsGranted = false,
                gpsAccuracyM = 30.0,
                capabilities = caps.copy(measuredRateHz = 0.3),
                visibleCells = emptySet(),
                servingRatsLte = false,
                trafficUrl = "",
            ),
        )
        warn.canStart shouldBe true
        listOf(
            CheckId.NOTIFICATIONS,
            CheckId.GPS_ACCURACY,
            CheckId.CAPABILITIES,
            CheckId.PLANNED_CELLS,
            CheckId.NETWORK_MODE,
            CheckId.TRAFFIC,
        )
            .forEach { warn.status(it) shouldBe CheckStatus.WARN }
        // Thresholds follow the config, not constants.
        PreCheck.evaluate(
            good.copy(gpsAccuracyM = 12.0, config = AnalysisConfig(maxAccuracyM = 10.0)),
        ).status(CheckId.GPS_ACCURACY) shouldBe
            CheckStatus.WARN
        PreCheck.evaluate(good.copy(config = AnalysisConfig(minDeviceRateHz = 0.95))).status(CheckId.CAPABILITIES) shouldBe CheckStatus.WARN
        PreCheck.evaluate(good.copy(gpsAccuracyM = null, capabilities = null)).let {
            it.status(CheckId.GPS_ACCURACY) shouldBe CheckStatus.WARN
            it.status(CheckId.CAPABILITIES) shouldBe CheckStatus.WARN
        }
    }
}
