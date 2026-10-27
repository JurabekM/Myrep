package uz.sectorverify.data

import android.content.Context
import androidx.room.Room
import androidx.room.testing.MigrationTestHelper
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import java.io.File
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.runBlocking
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.runner.RunWith
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.di.DatabaseFactory
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.NewSession
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.data.security.KeystoreKeyWrapper
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.model.AnalysisConfig
import uz.sectorverify.model.CellSample
import uz.sectorverify.model.GnssFix
import uz.sectorverify.model.Rat
import uz.sectorverify.model.SessionMode
import uz.sectorverify.model.SessionStatus

@RunWith(AndroidJUnit4::class)
class EncryptedDatabaseTest {
    private val context: Context = ApplicationProvider.getApplicationContext()

    @get:Rule
    val migrations = MigrationTestHelper(InstrumentationRegistry.getInstrumentation(), SectorVerifyDatabase::class.java)

    @Test
    fun keystoreWrapperRoundTrips() {
        val w = KeystoreKeyWrapper("sv_test_wrap")
        val secret = ByteArray(32) { it.toByte() }
        val wrapped = w.wrap(secret)
        assertFalse(wrapped.contentEquals(secret))
        assertArrayEquals(secret, w.unwrap(wrapped))
    }

    @Test
    fun databaseFileIsEncrypted(): Unit = runBlocking {
        context.deleteDatabase(SectorVerifyDatabase.NAME)
        val db = DatabaseFactory.encrypted(context)
        RoomPlanRepository(db.siteDao(), Clock.SYSTEM).importCsv(
            PlanCsv.HEADER.joinToString(",") + "\nNAV-1,Navoiy,40.1,65.3,43405,S1,LTE,B3,1300,141,0,65,,,\n",
        )
        db.close()
        val header = context.getDatabasePath(SectorVerifyDatabase.NAME).readBytes().copyOf(16)
        assertFalse(String(header, Charsets.US_ASCII).startsWith("SQLite format 3"))
        val reopened = DatabaseFactory.encrypted(context)
        assertEquals("NAV-1", reopened.siteDao().byCode("NAV-1")!!.code)
        reopened.close()
    }

    /** 1-versiya sxemasi eksport qilingan JSON bilan mos; har bir keyingi versiya bu yerga migratsiya testini qo'shadi. */
    @Test
    fun schemaVersion1() {
        migrations.createDatabase("migration-test", 1).close()
        migrations.runMigrationsAndValidate("migration-test", 1, true).close()
    }

    /** AC-07: jarayon sessiya o'rtasida o'ladi; qayta ishga tushganda RUNNING sessiya topiladi, ≤ 2 s ma'lumot yo'qoladi. */
    @Test
    fun forcedStopLosesAtMostTwoSeconds(): Unit = runBlocking {
        System.loadLibrary("sqlcipher")
        val name = "ac07.db"
        context.deleteDatabase(name)
        val factory = SupportOpenHelperFactory("ac07-test-passphrase".toByteArray())
        fun open() = Room.databaseBuilder(context, SectorVerifyDatabase::class.java, name).openHelperFactory(factory).build()
        val db = open()
        val plans = RoomPlanRepository(db.siteDao(), Clock.SYSTEM)
        plans.importCsv(PlanCsv.HEADER.joinToString(",") + "\nNAV-7,N,40.1,65.3,43405,S1,LTE,B3,1300,141,0,65,,,\n")
        val repo = RoomSessionRepository(db.sessionDao(), db.rawDao(), db.resultDao(), db.siteDao(), Clock.SYSTEM)
        val id = repo.create(
            NewSession(plans.siteByCode("NAV-7")!!.id, SessionMode.FULL, "test", 35, null, "t", "t", AnalysisConfig(), null),
        )
        val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
        val writer = BufferedSampleWriter(repo.sink(id))
        writer.start(scope)
        val t0 = System.nanoTime()
        var lastProducedNanos = 0L
        scope.launch {
            while (true) {
                lastProducedNanos = System.nanoTime() - t0
                writer.addSamples(listOf(CellSample(lastProducedNanos, Rat.LTE, 1300, 141, true, -90.0)))
                writer.addFix(GnssFix(lastProducedNanos, 0, 40.1, 65.3, 4.0))
                delay(200)
            }
        }
        delay(6_300)
        scope.cancel() // o'ldirish imitatsiyasi: stop() yo'q, yakuniy flush yo'q
        db.close()

        val restarted = open()
        val again =
            RoomSessionRepository(restarted.sessionDao(), restarted.rawDao(), restarted.resultDao(), restarted.siteDao(), Clock.SYSTEM)
        val running = again.running()
        assertEquals(listOf(id), running.map { it.id })
        assertEquals(SessionStatus.RUNNING, running.single().status)
        val persisted = restarted.rawDao().lastSampleNanos(id)!!
        val lostMs = (lastProducedNanos - persisted) / 1_000_000
        assertTrue("lost $lostMs ms", lostMs <= 2_000)
        restarted.close()
        File(context.getDatabasePath(name).path).delete()
    }
}
