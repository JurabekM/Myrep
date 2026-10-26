package uz.sectorverify.analysis.sim

import kotlin.math.PI
import kotlin.math.abs
import kotlin.math.cos
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt
import kotlin.math.sin
import kotlin.math.sqrt
import kotlin.random.Random
import uz.sectorverify.analysis.Angles
import uz.sectorverify.analysis.Geo
import uz.sectorverify.analysis.LatLon
import uz.sectorverify.model.CauseCode
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.Sector
import uz.sectorverify.model.SitePlan

/**
 * Deterministik drive-test simulyatori (§6.11). RSRP = ref − 10·n·log10(d/300) + A(φ − α) + S + F, bunda
 * S — Gudmundson AR(1) soyalanishi, F — Rayleigh fadingi (4 ta eksponensialning o'rtachasi, dB da).
 */
class Simulator(private val scenario: SimScenario) {
    private val rnd = Random(scenario.seed)

    private class TxCell(
        val key: CellKey,
        val towerLat: Double,
        val towerLon: Double,
        val azimuthDeg: Double,
        val hpbwDeg: Double,
        val ownSite: Boolean,
    ) {
        var shadowIndividual = 0.0
    }

    private data class RoutePoint(val pos: LatLon, val headingDeg: Double, val stepM: Double)

    fun run(): SimResult {
        val sc = scenario
        val arfcns = ARFCNS.getValue(sc.rat).take(sc.nArfcn)
        val labels = List(sc.nSectors) { "S${it + 1}" }
        val planAz = List(sc.nSectors) { Angles.norm360(sc.azimuthOffsetDeg + it * 360.0 / sc.nSectors) }
        val pcis = arfcns.map { distinctPcis(sc.rat, sc.nSectors) }
        val sectors = arfcns.flatMapIndexed { a, (band, arfcn) ->
            List(sc.nSectors) { i -> Sector(labels[i], sc.rat, band, arfcn, pcis[a][i], planAz[i], sc.hpbwDeg, 2.0, 4.0, 30.0) }
        }
        val install = List(sc.nSectors) { gaussian() * sc.installErrorSigmaDeg }
        val trueAz = HashMap<CellKey, Double>()
        for (a in arfcns.indices) {
            for (i in 0 until sc.nSectors) {
                trueAz[sectors[a * sc.nSectors + i].key] =
                    Angles.norm360(planAz[i] + install[i])
            }
        }

        val st = FaultState(sectors)
        applyFault(st, Layout(sectors, labels, planAz, install, arfcns.size), trueAz)
        val off = st.off
        val planned = st.planned
        val neighbor = st.neighbor

        val cells = sectors.filter { it.key !in off }
            .map { TxCell(it.key, sc.siteLat, sc.siteLon, trueAz.getValue(it.key), it.hpbwDeg, ownSite = true) } +
            listOfNotNull(neighbor)
        val route = route()
        val plan = SitePlan("SIM-${sc.seed}", "Simulyatsiya ${sc.seed}", sc.siteLat, sc.siteLon, "43405", planned)
        val (samples, fixes) = walk(route, cells)
        return SimResult(
            scenario = sc,
            plan = plan,
            samples = samples,
            fixes = fixes,
            trueAzimuth = trueAz.filterKeys { it !in off },
            expected = Expectation(st.swap, st.causes, st.missing, st.unexpected),
            durationS = route.size * SAMPLE_INTERVAL_S,
        )
    }

    private class Layout(
        val sectors: List<Sector>,
        val labels: List<String>,
        val planAz: List<Double>,
        val install: List<Double>,
        val nArfcn: Int,
    ) {
        fun at(i: Int, a: Int) = sectors[a * labels.size + i]

        fun installedAz(i: Int) = Angles.norm360(planAz[i] + install[i])
    }

    private class FaultState(var planned: List<Sector>) {
        val swap = HashMap<CellKey, String>()
        val causes = HashMap<CellKey, CauseCode>()
        val missing = HashSet<CellKey>()
        val unexpected = HashSet<CellKey>()
        val off = HashSet<CellKey>()
        var neighbor: TxCell? = null
    }

    /** [SimScenario.fault] ni haqiqiy azimutlarga qo'llaydi va tahlil nimani topishi kerakligini yozib qo'yadi. */
    private fun applyFault(st: FaultState, l: Layout, trueAz: MutableMap<CellKey, Double>) {
        val sc = scenario
        fun swapInto(i: Int, j: Int, a: Int, cause: CauseCode) {
            val k = l.at(i, a).key
            trueAz[k] = l.installedAz(j)
            st.swap[k] = l.labels[j]
            st.causes[k] = cause
        }
        when (val f = sc.fault) {
            Fault.None -> Unit
            is Fault.FullSwap -> for (a in 0 until l.nArfcn) {
                f.sectors.forEachIndexed { m, i -> swapInto(i, f.sectors[(m + 1) % f.sectors.size], a, CauseCode.CELL_CONFIG_SWAP) }
            }
            is Fault.BandSwap -> {
                val cause = if (l.nArfcn > 1) CauseCode.BAND_PORT_SWAP else CauseCode.CELL_CONFIG_SWAP
                swapInto(f.a, f.b, f.arfcnIndex, cause)
                swapInto(f.b, f.a, f.arfcnIndex, cause)
            }
            is Fault.Rotation -> for (a in 0 until l.nArfcn) {
                val k = l.at(f.sector, a).key
                trueAz[k] = Angles.norm360(l.installedAz(f.sector) + f.deg)
                st.causes[k] = CauseCode.ANTENNA_ROTATED
            }
            is Fault.SectorOff -> for (a in 0 until l.nArfcn) {
                if (f.arfcnIndex != null && f.arfcnIndex != a) continue
                val k = l.at(f.sector, a).key
                st.off += k
                st.missing += k
                st.causes[k] = CauseCode.PCI_MISSING
            }
            is Fault.NeighborPciReuse -> {
                val tower = Geo.destination(sc.siteLat, sc.siteLon, f.bearingDeg, f.distanceM)
                val towardsUs = Geo.bearingDeg(tower.lat, tower.lon, sc.siteLat, sc.siteLon)
                st.neighbor = TxCell(l.at(f.sector, f.arfcnIndex).key, tower.lat, tower.lon, towardsUs, sc.hpbwDeg, ownSite = false)
            }
            is Fault.UnplannedCell -> {
                val k = l.at(f.sector, f.arfcnIndex).key
                st.planned = l.sectors.filter { it.key != k }
                st.unexpected += k
            }
        }
    }

    /** Marshrutni 1 Hz da yuradi; yacheyka namunalari va GNSS fix'larini umumiy elapsed-realtime soatida qaytaradi. */
    private fun walk(route: List<RoutePoint>, cells: List<TxCell>): Pair<List<CellSample>, List<GnssFix>> {
        val sc = scenario
        val samples = ArrayList<CellSample>(route.size * cells.size)
        val fixes = ArrayList<GnssFix>(route.size)
        var siteShadow = gaussian() * sc.shadowSigmaDb
        val neighborShadow = DoubleArray(cells.size) { gaussian() * sc.shadowSigmaDb }
        cells.forEach { it.shadowIndividual = gaussian() * sc.shadowSigmaDb }
        var serving: CellKey? = null
        val common = sqrt(sc.shadowSiteCorr)
        val own = sqrt(1 - sc.shadowSiteCorr)
        for ((k, p) in route.withIndex()) {
            val rho = exp(-p.stepM / sc.shadowDecorrM)
            val innov = sqrt(1 - rho * rho) * sc.shadowSigmaDb
            siteShadow = rho * siteShadow + innov * gaussian()
            cells.forEachIndexed { idx, c ->
                c.shadowIndividual = rho * c.shadowIndividual + innov * gaussian()
                neighborShadow[idx] = rho * neighborShadow[idx] + innov * gaussian()
            }
            val tCell = T0_NANOS + k * NANOS_PER_S

            // Har yacheyka uchun sekin (soyalangan) daraja, so'ng har kalitga eng kuchli uzatkich (PCI to'qnashuvi → kuchlisi dekodlanadi).
            data class Level(val cell: TxCell, val slow: Double, val distM: Double)
            val levels = cells.mapIndexed { idx, c ->
                val d = max(1.0, Geo.distanceM(c.towerLat, c.towerLon, p.pos.lat, p.pos.lon))
                val phi = Geo.bearingDeg(c.towerLat, c.towerLon, p.pos.lat, p.pos.lon)
                val shadow = if (c.ownSite) common * siteShadow + own * c.shadowIndividual else neighborShadow[idx]
                Level(
                    c,
                    sc.refRsrpDbm - 10 * sc.pathLossExponent * log10(d / REF_DIST_M) + pattern(phi - c.azimuthDeg, c.hpbwDeg) + shadow,
                    d,
                )
            }.groupBy { it.cell.key }.mapValues { (_, l) -> l.maxBy { it.slow } }

            val best = levels.values.maxBy { it.slow }
            val current = serving?.let { levels[it] }
            if (current == null || best.slow > current.slow + sc.hysteresisDb) serving = best.cell.key

            for ((key, lv) in levels) {
                val isServing = key == serving
                val rsrp = lv.slow + fading()
                // Sezgirlikdan past bo'lsa hech narsa dekodlanmaydi; qo'shnilar faqat pNeighbor ehtimol bilan xabar qilinadi.
                if (rsrp < sc.sensitivityDbm || (!isServing && rnd.nextDouble() >= sc.pNeighbor)) continue
                samples += sampleOf(key, tCell, rsrp, isServing, lv.distM)
            }
            val north = gaussian() * sc.gnssSigmaM
            val east = gaussian() * sc.gnssSigmaM
            val noisy = offset(p.pos, north, east)
            fixes += GnssFix(
                tNanos = tCell + GNSS_OFFSET_NANOS,
                utcMs = UTC0_MS + k * 1000L + GNSS_OFFSET_NANOS / NANOS_PER_MS,
                lat = noisy.lat,
                lon = noisy.lon,
                accM = 3.0 + rnd.nextDouble() * 3.0,
                speedMps = sc.speedMps,
                bearingDeg = p.headingDeg,
            )
        }
        return samples to fixes
    }

    private fun sampleOf(key: CellKey, tCell: Long, rsrp: Double, isServing: Boolean, distM: Double): CellSample {
        val sc = scenario
        val age = if (rnd.nextDouble() < sc.staleProb) STALE_AGE_MS + rnd.nextLong(STALE_EXTRA_MS) else rnd.nextLong(FRESH_AGE_MS)
        return CellSample(
            tNanos = tCell,
            rat = key.rat,
            arfcn = key.arfcn,
            pci = key.pci,
            registered = isServing,
            rsrp = if (rnd.nextDouble() < sc.nullRsrpProb) null else rsrp.roundToInt().toDouble(),
            rsrq = -10.0,
            sinr = (rsrp + 110).coerceIn(-10.0, 30.0),
            ta = if (isServing && key.rat == Rat.LTE) (distM / TA_STEP_M).roundToInt() else null,
            ci = if (isServing) 1_000L + key.pci else null,
            tac = if (isServing) 101 else null,
            rxNanos = tCell + age * NANOS_PER_MS,
        )
    }

    /** Sayt atrofidagi halqa yoki kvadrat: kesilgan yoyning oxiridan boshlanadi, [SimScenario.speedMps] tezlikda yuriladi. */
    private fun route(): List<RoutePoint> {
        val sc = scenario
        val sweep = sc.coverage * 360.0
        val start = sc.gapStartDeg + (1 - sc.coverage) * 360.0
        val step = sc.speedMps * SAMPLE_INTERVAL_S
        val corr = exp(-step / ROUTE_NOISE_CORR_M)
        var noise = gaussian() * sc.routeNoiseM
        val out = ArrayList<RoutePoint>()
        var theta = 0.0
        var prev: LatLon? = null
        while (theta < sweep) {
            val bearing = start + theta
            val r = when (sc.route) {
                RouteShape.RING -> sc.radiusM
                RouteShape.SQUARE -> sc.radiusM / max(abs(cos(Math.toRadians(bearing))), abs(sin(Math.toRadians(bearing))))
            }
            noise = corr * noise + sqrt(1 - corr * corr) * sc.routeNoiseM * gaussian()
            val pos = Geo.destination(sc.siteLat, sc.siteLon, bearing, r + noise)
            val heading = prev?.let { Geo.bearingDeg(it.lat, it.lon, pos.lat, pos.lon) } ?: Angles.norm360(bearing + 90)
            out += RoutePoint(pos, heading, step)
            prev = pos
            theta += Math.toDegrees(step / r)
        }
        return out
    }

    private fun pattern(deltaDeg: Double, hpbwDeg: Double): Double {
        val r = Angles.wrap180(deltaDeg) / hpbwDeg
        return -min(PATTERN_COEF * r * r, PATTERN_MAX_ATT_DB)
    }

    /** 4 ta resurs elementi bo'yicha o'rtachalangan Rayleigh fadingi: 10·log10(4 ta Exp(1) ning o'rtachasi). */
    private fun fading(): Double {
        var s = 0.0
        repeat(FADING_TERMS) { s += -ln(1.0 - rnd.nextDouble()) }
        return 10 * log10(s / FADING_TERMS)
    }

    private fun gaussian(): Double {
        val u1 = 1.0 - rnd.nextDouble()
        val u2 = rnd.nextDouble()
        return sqrt(-2.0 * ln(u1)) * cos(2 * PI * u2)
    }

    private fun offset(p: LatLon, northM: Double, eastM: Double): LatLon {
        val dLat = Math.toDegrees(northM / Geo.EARTH_RADIUS_M)
        val dLon = Math.toDegrees(eastM / (Geo.EARTH_RADIUS_M * cos(Math.toRadians(p.lat))))
        return LatLon(p.lat + dLat, p.lon + dLon)
    }

    private fun distinctPcis(rat: Rat, n: Int): List<Int> {
        val base = rnd.nextInt((rat.maxPci + 1) / 3 - n) * 3
        return List(n) { base + it } // LTE odati: har saytga bitta PCI guruhi, sektor = PCI mod 3
    }

    companion object {
        private val ARFCNS = mapOf(
            Rat.LTE to listOf("B3" to 1300, "B7" to 3100, "B20" to 6300),
            Rat.NR to listOf("n78" to 636_666, "n1" to 428_000, "n28" to 152_600),
        )
        const val T0_NANOS = 1_000_000_000_000L
        const val UTC0_MS = 1_790_000_000_000L
        private const val NANOS_PER_S = 1_000_000_000L
        private const val NANOS_PER_MS = 1_000_000L
        private const val GNSS_OFFSET_NANOS = 300_000_000L
        private const val SAMPLE_INTERVAL_S = 1.0
        private const val REF_DIST_M = 300.0
        private const val TA_STEP_M = 78.12
        private const val PATTERN_COEF = 12.0
        private const val PATTERN_MAX_ATT_DB = 30.0
        private const val FADING_TERMS = 4
        private const val ROUTE_NOISE_CORR_M = 30.0
        private const val FRESH_AGE_MS = 900L
        private const val STALE_AGE_MS = 3500L
        private const val STALE_EXTRA_MS = 2500L

        fun run(scenario: SimScenario): SimResult = Simulator(scenario).run()
    }
}
