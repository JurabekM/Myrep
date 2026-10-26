package uz.sectorverify.feature.survey

import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import uz.sectorverify.analysis.LiveAnalyzer
import uz.sectorverify.analysis.LiveSnapshot
import uz.sectorverify.data.BufferedSampleWriter
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellKey
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.SitePlan
import uz.sectorverify.telephony.TrafficStatus

/** One map point: position and the serving PCI at that moment (track colour). */
data class TrackPoint(val lat: Double, val lon: Double, val servingPci: Int?)

data class SurveyState(
    val sessionId: String? = null,
    val siteCode: String? = null,
    val running: Boolean = false,
    val samples: Int = 0,
    val fixes: Int = 0,
    /** Measured CellInfo update rate of the serving cell (distinct timestamps per second). */
    val rateHz: Double = 0.0,
    val lastFix: GnssFix? = null,
    val track: List<TrackPoint> = emptyList(),
    val visibleCells: List<CellKey> = emptyList(),
    val live: LiveSnapshot? = null,
    val traffic: TrafficStatus? = null,
    /** Set once when the live analysis first becomes ready ("Natija tayyor"). */
    val readyAtSamples: Int? = null,
    val finishedSessionId: String? = null,
)

/**
 * Survey pipeline without Android: collects both streams into the 1 s [writer] and an in-memory copy, and
 * re-runs the live analysis every `liveIntervalMs` (§6.10) off the main thread.
 */
class SurveyEngine(
    private val sessionId: String,
    private val plan: SitePlan,
    private val config: AnalysisConfig,
    private val writer: BufferedSampleWriter,
    private val analysisDispatcher: CoroutineDispatcher = Dispatchers.Default,
) {
    private val live = LiveAnalyzer(config)
    private val lock = Mutex()
    private val samples = ArrayList<CellSample>()
    private val fixes = ArrayList<GnssFix>()
    private val servingTimes = sortedSetOf<Long>()
    private val track = ArrayList<TrackPoint>()
    private var servingPci: Int? = null
    private val _state = MutableStateFlow(SurveyState(sessionId = sessionId, siteCode = plan.code, running = true))
    val state: StateFlow<SurveyState> = _state.asStateFlow()

    /** [restoredSamples]/[restoredFixes]: data already stored when a killed session is resumed. */
    fun start(
        scope: CoroutineScope,
        cells: Flow<List<CellSample>>,
        gnss: Flow<GnssFix>,
        traffic: Flow<TrafficStatus>,
        restoredSamples: List<CellSample> = emptyList(),
        restoredFixes: List<GnssFix> = emptyList(),
    ): Job = scope.launch {
        lock.withLock {
            samples += restoredSamples
            fixes += restoredFixes
            restoredSamples.filter { it.registered }.forEach { servingTimes += it.tNanos }
            servingPci = restoredSamples.lastOrNull { it.registered }?.pci
            restoredFixes.forEach { track += TrackPoint(it.lat, it.lon, null) }
        }
        writer.start(this)
        launch { cells.collect { onCells(it) } }
        launch { gnss.collect { onFix(it) } }
        launch { traffic.collect { t -> _state.update { it.copy(traffic = t) } } }
        launch {
            while (isActive) {
                refreshLive()
                delay(config.liveIntervalMs)
            }
        }
    }

    private suspend fun onCells(batch: List<CellSample>) {
        writer.addSamples(batch)
        val (count, rate) = lock.withLock {
            samples += batch
            batch.filter { it.registered }.forEach { servingTimes += it.tNanos }
            batch.lastOrNull { it.registered }?.let { servingPci = it.pci }
            samples.size to rate()
        }
        val visible = batch.map { it.key }.distinct().sorted()
        _state.update { it.copy(samples = count, rateHz = rate, visibleCells = visible) }
    }

    private suspend fun onFix(fix: GnssFix) {
        writer.addFix(fix)
        val (count, points) = lock.withLock {
            fixes += fix
            track += TrackPoint(fix.lat, fix.lon, servingPci)
            fixes.size to track.toList()
        }
        _state.update { it.copy(fixes = count, lastFix = fix, track = points) }
    }

    private fun rate(): Double {
        if (servingTimes.size < 2) return 0.0
        val spanS = (servingTimes.last() - servingTimes.first()) / NANOS_PER_S
        return if (spanS <= 0) 0.0 else (servingTimes.size - 1) / spanS
    }

    suspend fun refreshLive() {
        val (s, f) = lock.withLock { ArrayList(samples) to ArrayList(fixes) }
        val snapshot = withContext(analysisDispatcher) { live.snapshot(plan, s, f) }
        _state.update { st ->
            st.copy(live = snapshot, readyAtSamples = st.readyAtSamples ?: s.size.takeIf { snapshot.ready })
        }
    }

    /** Flushes the last buffer; the caller then marks the session DONE and runs the final analysis. */
    suspend fun stop() {
        writer.stop()
        _state.update { it.copy(running = false) }
    }

    val measuredRateHz: Double get() = _state.value.rateHz

    private companion object {
        const val NANOS_PER_S = 1e9
    }
}
