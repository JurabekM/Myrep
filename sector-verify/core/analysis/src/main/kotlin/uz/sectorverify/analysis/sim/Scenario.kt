package uz.sectorverify.analysis.sim

import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SitePlan

enum class RouteShape { RING, SQUARE }

/** §6.11 nosozlik ssenariylari. Sektor va ARFCN argumentlari — yaratilgan plandagi indekslar. */
sealed interface Fault {
    data object None : Fault

    /** Har ARFCN'da siklik swap: [sectors][m] sektori [sectors][m+1] sektoriga nurlanadi. O'lchami 2 yoki 3. */
    data class FullSwap(val sectors: List<Int>) : Fault

    /** Faqat bitta ARFCN'da ikki sektor almashgan. */
    data class BandSwap(val arfcnIndex: Int, val a: Int, val b: Int) : Fault

    /** [sector] ning fizik antennasi [deg] ga burilgan (barcha ARFCN'lar). */
    data class Rotation(val sector: Int, val deg: Double) : Fault

    /** [sector] yacheykasi [arfcnIndex] da uzatmaydi (null = barcha ARFCN'lar). */
    data class SectorOff(val sector: Int, val arfcnIndex: Int? = null) : Fault

    /** Qo'shni sayt ([sector], [arfcnIndex]) ning PCI'sini qayta ishlatadi va bizning saytga qaragan. */
    data class NeighborPciReuse(val sector: Int, val arfcnIndex: Int, val distanceM: Double, val bearingDeg: Double) : Fault

    /** Yacheyka uzatadi, lekin RF planda u yo'q. */
    data class UnplannedCell(val sector: Int, val arfcnIndex: Int) : Fault
}

data class SimScenario(
    val seed: Long,
    val siteLat: Double = 40.1032,
    val siteLon: Double = 65.3685,
    val rat: Rat = Rat.LTE,
    val nSectors: Int = 3,
    val nArfcn: Int = 1,
    val azimuthOffsetDeg: Double = 0.0,
    /** Har bir antenna o'rnatilishidagi tasodifiy xatoning σ si (haqiqiy − plan). */
    val installErrorSigmaDeg: Double = 3.0,
    val hpbwDeg: Double = 65.0,
    val route: RouteShape = RouteShape.RING,
    val radiusM: Double = 275.0,
    val routeNoiseM: Double = 15.0,
    /** Yurilgan yo'nalishlar ulushi (bitta uzluksiz yoy kesib tashlanadi). */
    val coverage: Double = 1.0,
    val gapStartDeg: Double = 0.0,
    val speedMps: Double = 1.4,
    val shadowSigmaDb: Double = 7.0,
    val shadowDecorrM: Double = 50.0,
    /** Soyalanishning saytdagi barcha yacheykalar uchun umumiy bo'lgan ulushi. */
    val shadowSiteCorr: Double = 0.7,
    val gnssSigmaM: Double = 4.0,
    val pNeighbor: Double = 0.8,
    val hysteresisDb: Double = 3.0,
    val refRsrpDbm: Double = -80.0,
    val pathLossExponent: Double = 3.5,
    val sensitivityDbm: Double = -125.0,
    val staleProb: Double = 0.02,
    val nullRsrpProb: Double = 0.01,
    val fault: Fault = Fault.None,
) {
    init {
        require(nSectors in 1..MAX_SECTORS) { "nSectors in 1..6" }
        require(nArfcn in 1..MAX_ARFCN) { "nArfcn in 1..3" }
        require(coverage in 0.05..1.0) { "coverage in 0.05..1" }
    }

    companion object {
        const val MAX_SECTORS = 6
        const val MAX_ARFCN = 3
    }
}

/** Ssenariy uchun tahlil nimani topishi kutiladi. */
data class Expectation(
    /** Almashgan yacheykalar → ular haqiqatda nurlanadigan sektor yorlig'i. */
    val swapMapping: Map<CellKey, String> = emptyMap(),
    val causes: Map<CellKey, CauseCode> = emptyMap(),
    val missing: Set<CellKey> = emptySet(),
    val unexpected: Set<CellKey> = emptySet(),
) {
    val hasFault: Boolean get() = swapMapping.isNotEmpty() || causes.isNotEmpty() || missing.isNotEmpty()
}

data class SimResult(
    val scenario: SimScenario,
    val plan: SitePlan,
    val samples: List<CellSample>,
    val fixes: List<GnssFix>,
    /** Uzatayotgan har bir sayt yacheykasi haqiqatda nurlanadigan yo'nalish. */
    val trueAzimuth: Map<CellKey, Double>,
    val expected: Expectation,
    val durationS: Double,
)
