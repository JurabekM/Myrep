package uz.sectorverify.analysis.sim

import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SitePlan

enum class RouteShape { RING, SQUARE }

/** Fault scenarios of §6.11. Sector and ARFCN arguments are indices into the generated plan. */
sealed interface Fault {
    data object None : Fault

    /** Cyclic swap on every ARFCN: sector [sectors][m] radiates into sector [sectors][m+1]. Size 2 or 3. */
    data class FullSwap(val sectors: List<Int>) : Fault

    /** Two sectors swapped on one ARFCN only. */
    data class BandSwap(val arfcnIndex: Int, val a: Int, val b: Int) : Fault

    /** Physical antenna of [sector] rotated by [deg] (all ARFCNs). */
    data class Rotation(val sector: Int, val deg: Double) : Fault

    /** Cell of [sector] does not transmit on [arfcnIndex] (null = all ARFCNs). */
    data class SectorOff(val sector: Int, val arfcnIndex: Int? = null) : Fault

    /** A neighbour site reuses the PCI of ([sector], [arfcnIndex]) and points at our site. */
    data class NeighborPciReuse(val sector: Int, val arfcnIndex: Int, val distanceM: Double, val bearingDeg: Double) : Fault

    /** The cell transmits but the RF plan omits it. */
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
    /** σ of the random installation error of every antenna (truth − plan). */
    val installErrorSigmaDeg: Double = 3.0,
    val hpbwDeg: Double = 65.0,
    val route: RouteShape = RouteShape.RING,
    val radiusM: Double = 275.0,
    val routeNoiseM: Double = 15.0,
    /** Fraction of bearings walked (one contiguous arc is cut out). */
    val coverage: Double = 1.0,
    val gapStartDeg: Double = 0.0,
    val speedMps: Double = 1.4,
    val shadowSigmaDb: Double = 7.0,
    val shadowDecorrM: Double = 50.0,
    /** Share of the shadowing that is common to all cells of the site. */
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

/** What the analysis is expected to find for a scenario. */
data class Expectation(
    /** Swapped cells → label of the sector they really radiate into. */
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
    /** Direction each transmitting site cell actually radiates into. */
    val trueAzimuth: Map<CellKey, Double>,
    val expected: Expectation,
    val durationS: Double,
)
