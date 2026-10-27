package uz.sectorverify.model

import kotlinx.serialization.Serializable

@Serializable
enum class Rat {
    LTE,
    NR,
    ;

    /** Maksimal yaroqli PCI (LTE 0..503, NR 0..1007). */
    val maxPci: Int get() = if (this == LTE) LTE_MAX_PCI else NR_MAX_PCI

    companion object {
        const val LTE_MAX_PCI = 503
        const val NR_MAX_PCI = 1007
    }
}

/** Bitta nurlanadigan yacheykani aniqlaydi: (RAT, ARFCN, PCI). */
@Serializable
data class CellKey(val rat: Rat, val arfcn: Int, val pci: Int) : Comparable<CellKey> {
    override fun compareTo(other: CellKey): Int = compareValuesBy(this, other, { it.rat }, { it.arfcn }, { it.pci })

    override fun toString(): String = "$rat/$arfcn/$pci"
}

/** RF plandagi bitta rejalashtirilgan sektor-tashuvchi. */
@Serializable
data class Sector(
    val label: String,
    val rat: Rat,
    val band: String,
    val arfcn: Int,
    val pci: Int,
    val azimuthDeg: Double,
    val hpbwDeg: Double = DEFAULT_HPBW_DEG,
    val mechTiltDeg: Double? = null,
    val elecTiltDeg: Double? = null,
    val heightM: Double? = null,
) {
    val key: CellKey get() = CellKey(rat, arfcn, pci)

    companion object {
        const val DEFAULT_HPBW_DEG = 65.0
    }
}

@Serializable
data class SitePlan(
    val code: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    val mccMnc: String,
    val sectors: List<Sector>,
) {
    fun sectorFor(key: CellKey): Sector? = sectors.firstOrNull { it.key == key }

    val arfcns: List<Pair<Rat, Int>> get() = sectors.map { it.rat to it.arfcn }.distinct()
}

/**
 * Bitta xom yacheyka o'lchovi. [tNanos] — CellInfo vaqt belgisi, [rxNanos] — ilova uni qabul qilgan
 * payt; ikkalasi ham elapsedRealtimeNanos soatida ([GnssFix.tNanos] bilan bir xil soat).
 */
@Serializable
data class CellSample(
    val tNanos: Long,
    val rat: Rat,
    val arfcn: Int,
    val pci: Int,
    val registered: Boolean,
    val rsrp: Double? = null,
    val rsrq: Double? = null,
    val sinr: Double? = null,
    val ta: Int? = null,
    val ci: Long? = null,
    val tac: Int? = null,
    val rxNanos: Long? = null,
) {
    val key: CellKey get() = CellKey(rat, arfcn, pci)
}

@Serializable
data class GnssFix(
    val tNanos: Long,
    val utcMs: Long,
    val lat: Double,
    val lon: Double,
    val accM: Double,
    val speedMps: Double? = null,
    val bearingDeg: Double? = null,
)

/** DeviceCapabilityProbe natijasi (§7), DataStore'da saqlanadi va capabilities.json sifatida eksport qilinadi. */
@Serializable
data class DeviceCapabilities(
    val deviceModel: String,
    val manufacturer: String,
    val apiLevel: Int,
    val chipset: String? = null,
    val baseband: String? = null,
    val probeDurationS: Int,
    val measuredRateHz: Double,
    val neighborsReported: Boolean,
    val neighborRsrpReported: Boolean,
    val timingAdvanceReported: Boolean,
    val nrSaFieldsReported: Boolean,
    val probedAtUtcMs: Long,
)
