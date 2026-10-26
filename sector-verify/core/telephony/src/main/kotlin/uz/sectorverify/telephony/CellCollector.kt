package uz.sectorverify.telephony

import android.annotation.SuppressLint
import android.content.Context
import android.os.Build
import android.os.SystemClock
import android.telephony.CellInfo
import android.telephony.TelephonyCallback
import android.telephony.TelephonyManager
import androidx.annotation.RequiresApi
import java.util.concurrent.Executor
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.callbackFlow
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import uz.sectorverify.model.CellSample

/**
 * §7 CellCollector: tanlangan subscription'da har [intervalMs] da `requestCellInfoUpdate()` va API 31+ da
 * `TelephonyCallback.CellInfoListener`. Ikkala oqim birlashtiriladi va (cell, timestamp) bo'yicha takrorlar olib tashlanadi.
 * Chaqiruvchida ACCESS_FINE_LOCATION bo'lishi shart (servis boshlanishidan oldin pre-check ekrani tekshiradi).
 */
class CellCollector(
    private val context: Context,
    private val subscriptionId: Int,
    private val intervalMs: Long = DEFAULT_INTERVAL_MS,
    private val clock: () -> Long = SystemClock::elapsedRealtimeNanos,
) {
    @SuppressLint("MissingPermission")
    fun samples(): Flow<List<CellSample>> = callbackFlow {
        val tm = context.getSystemService(TelephonyManager::class.java).createForSubscriptionId(subscriptionId)
        val executor = Executor { it.run() }
        val dedup = Deduplicator()
        fun emit(infos: List<CellInfo>) {
            val rx = clock()
            val batch = infos.mapNotNull { CellInfoReader.read(it) }.mapNotNull { CellNormalizer.normalize(it, rx) }
            val fresh = dedup.filter(batch, rx)
            if (fresh.isNotEmpty()) trySend(fresh)
        }
        val listener = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) registerListener(tm, executor, ::emit) else null
        val poller = launch {
            while (isActive) {
                tm.requestCellInfoUpdate(
                    executor,
                    object : TelephonyManager.CellInfoCallback() {
                        override fun onCellInfo(cellInfo: MutableList<CellInfo>) = emit(cellInfo)
                    },
                )
                delay(intervalMs)
            }
        }
        awaitClose {
            poller.cancel()
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S && listener is TelephonyCallback) tm.unregisterTelephonyCallback(listener)
        }
    }

    @RequiresApi(Build.VERSION_CODES.S)
    @SuppressLint("MissingPermission")
    private fun registerListener(tm: TelephonyManager, executor: Executor, onInfo: (List<CellInfo>) -> Unit): Any {
        val cb = object : TelephonyCallback(), TelephonyCallback.CellInfoListener {
            override fun onCellInfoChanged(cellInfo: MutableList<CellInfo>) = onInfo(cellInfo)
        }
        tm.registerTelephonyCallback(executor, cb)
        return cb
    }

    companion object {
        const val DEFAULT_INTERVAL_MS = 1000L
    }
}

/** Avval ko'rilgan sample'larni tashlaydi (bir xil cell va CellInfo timestamp) — poll va listener ko'pincha bir skanni beradi. */
class Deduplicator(private val windowNanos: Long = WINDOW_NANOS) {
    private val seen = LinkedHashMap<Triple<Any, Int, Long>, Long>()

    @Synchronized
    fun filter(batch: List<CellSample>, nowNanos: Long): List<CellSample> {
        val it = seen.entries.iterator()
        while (it.hasNext() && nowNanos - it.next().value > windowNanos) it.remove()
        return batch.filter { s -> seen.putIfAbsent(Triple(s.key, 0, s.tNanos), nowNanos) == null }
    }

    private companion object {
        const val WINDOW_NANOS = 30_000_000_000L
    }
}
