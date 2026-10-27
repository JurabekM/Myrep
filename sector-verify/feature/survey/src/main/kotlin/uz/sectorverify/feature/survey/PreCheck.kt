package uz.sectorverify.feature.survey

import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.SitePlan
import uz.sectorverify.telephony.SimInfo
import uz.sectorverify.telephony.SubscriptionSelector
import uz.sectorverify.telephony.TrafficGenerator

enum class CheckId { PERMISSIONS, NOTIFICATIONS, SIM, NETWORK_MODE, GPS, GPS_ACCURACY, CAPABILITIES, PLANNED_CELLS, TRAFFIC }

enum class CheckStatus { OK, WARN, BLOCK }

data class CheckItem(val id: CheckId, val status: CheckStatus, val args: List<String> = emptyList())

data class PreCheckInput(
    val plan: SitePlan,
    val locationGranted: Boolean,
    val phoneStateGranted: Boolean,
    val notificationsGranted: Boolean,
    val sims: List<SimInfo>,
    val gpsEnabled: Boolean,
    val gpsAccuracyM: Double?,
    val capabilities: DeviceCapabilities?,
    val visibleCells: Set<CellKey>,
    val servingRatsLte: Boolean,
    val trafficUrl: String,
    /** GPS aniqligi va qurilma chastotasi chegaralari shu config'dan (§11). */
    val config: AnalysisConfig = AnalysisConfig(),
)

data class PreCheckResult(val items: List<CheckItem>, val subscription: SimInfo?) {
    /** "Boshlash" faqat hech narsa to'smaganda yoqiladi. */
    val canStart: Boolean get() = items.none { it.status == CheckStatus.BLOCK }
}

/** §8.1 3-ekran mantig'i: qaysi muammolar o'lchovni to'sadi, qaysilari faqat ogohlantiradi. */
object PreCheck {
    fun evaluate(i: PreCheckInput): PreCheckResult {
        val sim = SubscriptionSelector.select(i.sims, i.plan.mccMnc)
        val planned = i.plan.sectors.map { it.key }.toSet()
        val seen = planned.intersect(i.visibleCells)
        val caps = i.capabilities
        val accuracy = i.gpsAccuracyM?.let { "%.0f".format(it) } ?: "—"
        val rate = caps?.measuredRateHz?.let { "%.2f".format(it) } ?: "—"
        val items = listOf(
            CheckItem(CheckId.PERMISSIONS, block(i.locationGranted && i.phoneStateGranted)),
            CheckItem(CheckId.NOTIFICATIONS, warn(i.notificationsGranted)),
            CheckItem(CheckId.SIM, block(sim != null), listOf(i.plan.mccMnc, sim?.carrierName.orEmpty())),
            CheckItem(CheckId.NETWORK_MODE, warn(i.servingRatsLte)),
            CheckItem(CheckId.GPS, block(i.gpsEnabled)),
            CheckItem(
                CheckId.GPS_ACCURACY,
                warn(i.gpsAccuracyM != null && i.gpsAccuracyM <= i.config.maxAccuracyM),
                listOf(accuracy, "%.0f".format(i.config.maxAccuracyM)),
            ),
            CheckItem(CheckId.CAPABILITIES, warn(capabilitiesOk(caps, i.config.minDeviceRateHz)), listOf(rate)),
            CheckItem(CheckId.PLANNED_CELLS, warn(seen.isNotEmpty()), listOf("${seen.size}", "${planned.size}")),
            CheckItem(CheckId.TRAFFIC, warn(TrafficGenerator.isValidUrl(i.trafficUrl))),
        )
        return PreCheckResult(items, sim)
    }

    private fun capabilitiesOk(c: DeviceCapabilities?, minRateHz: Double) =
        c != null && c.measuredRateHz >= minRateHz && c.neighborRsrpReported

    private fun block(ok: Boolean) = if (ok) CheckStatus.OK else CheckStatus.BLOCK

    private fun warn(ok: Boolean) = if (ok) CheckStatus.OK else CheckStatus.WARN
}
