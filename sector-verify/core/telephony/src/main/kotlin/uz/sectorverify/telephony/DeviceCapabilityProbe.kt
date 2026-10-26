package uz.sectorverify.telephony

import android.content.Context
import android.os.Build
import kotlinx.coroutines.withTimeoutOrNull
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.DeviceCapabilities
import uz.sectorverify.model.Rat

/** Pure evaluation of what a device reports, from samples collected for [durationS] seconds. */
object CapabilityEvaluator {
    private const val NANOS_PER_S = 1e9

    fun evaluate(samples: List<CellSample>, durationS: Int, device: DeviceInfo, nowUtcMs: Long): DeviceCapabilities {
        // One distinct CellInfo timestamp of the serving cell = one real measurement update.
        val serving = samples.filter { it.registered }.map { it.tNanos }.distinct().sorted()
        val rate = if (serving.size >= 2) {
            (serving.size - 1) / ((serving.last() - serving.first()) / NANOS_PER_S).coerceAtLeast(1.0)
        } else {
            serving.size.toDouble() / durationS.coerceAtLeast(1)
        }
        val neighbors = samples.filter { !it.registered }
        return DeviceCapabilities(
            deviceModel = device.model,
            manufacturer = device.manufacturer,
            apiLevel = device.apiLevel,
            chipset = device.chipset,
            baseband = device.baseband,
            probeDurationS = durationS,
            measuredRateHz = rate,
            neighborsReported = neighbors.isNotEmpty(),
            neighborRsrpReported = neighbors.any { it.rsrp != null },
            timingAdvanceReported = samples.any { it.registered && it.rat == Rat.LTE && it.ta != null },
            nrSaFieldsReported = samples.any { it.registered && it.rat == Rat.NR && it.rsrp != null },
            probedAtUtcMs = nowUtcMs,
        )
    }
}

data class DeviceInfo(val model: String, val manufacturer: String, val apiLevel: Int, val chipset: String?, val baseband: String?) {
    companion object {
        fun current(): DeviceInfo = DeviceInfo(
            model = Build.MODEL,
            manufacturer = Build.MANUFACTURER,
            apiLevel = Build.VERSION.SDK_INT,
            chipset = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) Build.SOC_MODEL else Build.HARDWARE,
            baseband = Build.getRadioVersion(),
        )
    }
}

/** §7 DeviceCapabilityProbe: listens for [durationS] seconds (default 60) and evaluates the reported fields. */
class DeviceCapabilityProbe(
    private val context: Context,
    private val subscriptionId: Int,
    private val durationS: Int = DEFAULT_DURATION_S,
) {
    suspend fun run(): DeviceCapabilities {
        val collected = ArrayList<CellSample>()
        withTimeoutOrNull(durationS * MS_PER_S) {
            CellCollector(context, subscriptionId).samples().collect { collected += it }
        }
        return CapabilityEvaluator.evaluate(collected, durationS, DeviceInfo.current(), System.currentTimeMillis())
    }

    companion object {
        const val DEFAULT_DURATION_S = 60
        private const val MS_PER_S = 1000L
    }
}
