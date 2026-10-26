package uz.sectorverify.data

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix

/** Persists one buffer of samples and fixes atomically. */
fun interface BatchSink {
    suspend fun write(samples: List<CellSample>, fixes: List<GnssFix>)
}

/**
 * §7: both streams are buffered for [flushIntervalMs] (1 s) and written in one Room transaction.
 * If the process is killed, at most one unflushed buffer is lost (AC-07: ≤ 2 s).
 */
class BufferedSampleWriter(private val sink: BatchSink, private val flushIntervalMs: Long = FLUSH_INTERVAL_MS) {
    private val mutex = Mutex()
    private var samples = ArrayList<CellSample>()
    private var fixes = ArrayList<GnssFix>()
    private var job: Job? = null

    var written: Long = 0
        private set

    fun start(scope: CoroutineScope) {
        job = scope.launch {
            while (isActive) {
                delay(flushIntervalMs)
                flush()
            }
        }
    }

    suspend fun addSamples(batch: List<CellSample>) = mutex.withLock { samples.addAll(batch) }

    suspend fun addFix(fix: GnssFix) = mutex.withLock { fixes.add(fix) }

    suspend fun flush() {
        val (s, f) = mutex.withLock {
            val out = samples to fixes
            samples = ArrayList()
            fixes = ArrayList()
            out
        }
        if (s.isEmpty() && f.isEmpty()) return
        sink.write(s, f)
        written += s.size
    }

    /** Stops the timer and writes what is left. */
    suspend fun stop() {
        job?.cancel()
        job = null
        flush()
    }

    companion object {
        const val FLUSH_INTERVAL_MS = 1000L
    }
}
