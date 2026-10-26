package uz.sectorverify.data

import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.NonCancellable
import kotlinx.coroutines.cancelAndJoin
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix

/** Sample va fix'larning bitta buferini atomar saqlaydi. */
fun interface BatchSink {
    suspend fun write(samples: List<CellSample>, fixes: List<GnssFix>)
}

/**
 * §7: ikkala oqim [flushIntervalMs] (1 s) davomida buferlanadi va bitta Room tranzaksiyasida yoziladi.
 * Jarayon o'ldirilsa, ko'pi bilan bitta yozilmagan bufer yo'qoladi (AC-07: ≤ 2 s).
 */
class BufferedSampleWriter(private val sink: BatchSink, private val flushIntervalMs: Long = FLUSH_INTERVAL_MS) {
    private val mutex = Mutex()
    private var samples = ArrayList<CellSample>()
    private var fixes = ArrayList<GnssFix>()
    private var job: Job? = null

    /** Yozuvlarni ketma-ket qiladi: taymer va stop() bir vaqtda yozmaydi. */
    private val writeLock = Mutex()

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

    suspend fun flush() = writeLock.withLock {
        val (s, f) = mutex.withLock {
            val out = samples to fixes
            samples = ArrayList()
            fixes = ArrayList()
            out
        }
        if (s.isEmpty() && f.isEmpty()) return@withLock
        // Bufer allaqachon olib qo'yilgan: bekor qilish tranzaksiyani orqaga qaytarib, ma'lumotni yo'qotmasligi kerak.
        withContext(NonCancellable) { sink.write(s, f) }
        written += s.size
    }

    /** Taymerni to'xtatadi (boshlangan yozuv tugashini kutadi) va qolganini yozadi. */
    suspend fun stop() {
        job?.cancelAndJoin()
        job = null
        flush()
    }

    companion object {
        const val FLUSH_INTERVAL_MS = 1000L
    }
}
