package uz.sectorverify.data

import io.kotest.matchers.shouldBe
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceTimeBy
import kotlinx.coroutines.test.currentTime
import kotlinx.coroutines.test.runTest
import org.junit.jupiter.api.Test
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat

@OptIn(ExperimentalCoroutinesApi::class)
class BufferedSampleWriterTest {
    private class MemorySink : BatchSink {
        val samples = ArrayList<CellSample>()
        val fixes = ArrayList<GnssFix>()
        var transactions = 0

        override suspend fun write(samples: List<CellSample>, fixes: List<GnssFix>) {
            this.samples += samples
            this.fixes += fixes
            transactions++
        }
    }

    private fun sample(tMs: Long) = CellSample(tMs * 1_000_000, Rat.LTE, 1300, 1, true, -90.0)

    @Test
    fun `AC-07 a killed collector loses at most two seconds`() = runTest {
        val sink = MemorySink()
        val worker = TestScope(testScheduler)
        val writer = BufferedSampleWriter(sink)
        writer.start(worker)
        val producer = worker.launch {
            var t = 0L
            while (true) {
                writer.addSamples(listOf(sample(t)))
                writer.addFix(GnssFix(t * 1_000_000, t, 40.0, 65.0, 4.0))
                kotlinx.coroutines.delay(1000)
                t += 1000
            }
        }
        advanceTimeBy(60_500)
        val killedAtMs = currentTime
        worker.cancel() // jarayon o'limi: yakuniy flush yo'q
        producer.isCancelled shouldBe true
        val lastPersistedMs = sink.samples.maxOf { it.tNanos } / 1_000_000
        (killedAtMs - lastPersistedMs <= 2000) shouldBe true
        sink.fixes.size shouldBe sink.samples.size
        // Har sample uchun emas, har soniyada bitta tranzaksiya.
        (sink.transactions in 59..61) shouldBe true
    }

    @Test
    fun `stop flushes the remainder and empty flushes do nothing`() = runTest {
        val sink = MemorySink()
        val writer = BufferedSampleWriter(sink)
        writer.flush()
        sink.transactions shouldBe 0
        writer.addSamples(listOf(sample(1), sample(2)))
        writer.stop()
        sink.samples.size shouldBe 2
        writer.written shouldBe 2
    }

    @Test
    fun `stop while a timed write is in progress loses nothing`() = runTest {
        val sink = object : BatchSink {
            val samples = ArrayList<CellSample>()

            override suspend fun write(samples: List<CellSample>, fixes: List<GnssFix>) {
                kotlinx.coroutines.delay(500) // sekin tranzaksiya
                this.samples += samples
            }
        }
        val worker = TestScope(testScheduler)
        val writer = BufferedSampleWriter(sink)
        writer.start(worker)
        writer.addSamples(listOf(sample(1)))
        advanceTimeBy(1_200) // taymer yozuvi boshlandi, hali tugamadi
        writer.addSamples(listOf(sample(2)))
        writer.stop()
        sink.samples.map { it.tNanos } shouldBe listOf(1_000_000L, 2_000_000L)
    }
}
