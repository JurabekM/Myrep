package uz.buildcontrol.mobile

import androidx.room.Room
import androidx.test.core.app.ApplicationProvider
import kotlinx.coroutines.runBlocking
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import org.robolectric.RobolectricTestRunner
import org.robolectric.annotation.Config
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.EstimateItemRow
import uz.buildcontrol.mobile.data.db.MaterialRow
import uz.buildcontrol.mobile.data.db.ProjectRow
import uz.buildcontrol.mobile.data.db.WarehouseTxRow
import uz.buildcontrol.mobile.data.repo.AuthRepository
import uz.buildcontrol.mobile.data.repo.EstimateRepository
import uz.buildcontrol.mobile.data.repo.ExpenseRepository
import uz.buildcontrol.mobile.data.repo.ProjectRepository
import uz.buildcontrol.mobile.data.repo.WarehouseRepository
import uz.buildcontrol.mobile.data.sync.Change
import uz.buildcontrol.mobile.data.sync.SyncEngine
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.data.sync.SyncTransport
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.RoleCode
import uz.buildcontrol.mobile.domain.TxKind

/**
 * Two in-memory installations exchanging data through a shared log — the same
 * flow the phone runs against Supabase, minus the network.
 */
@RunWith(RobolectricTestRunner::class)
@Config(sdk = [34], manifest = Config.NONE)
class ReplicationRoundTripTest {

    /** In-memory stand-in for the `bc_changes` table. */
    private class MemoryLog : SyncTransport {
        val rows = mutableListOf<Change>()
        override val key = "memory"
        override fun describe() = "memory"
        override fun check() = "OK"
        override fun push(changes: List<Change>): Int {
            changes.forEach { rows.add(it.copy(cursor = (rows.size + 1).toString())) }
            return changes.size
        }
        override fun pull(after: String, limit: Int): List<Change> {
            val from = after.toIntOrNull() ?: 0
            return rows.drop(from).take(limit)
        }
    }

    private class Device(name: String) {
        val db: BcDatabase = Room.inMemoryDatabaseBuilder(
            ApplicationProvider.getApplicationContext(),
            BcDatabase::class.java,
        ).allowMainThreadQueries().build()

        val recorder = SyncRecorder(db)
        val engine = SyncEngine(db)
        val auth = AuthRepository(db, recorder)
        val projects = ProjectRepository(db, recorder, auth)
        val estimates = EstimateRepository(db, recorder, auth)
        val warehouse = WarehouseRepository(db, recorder, estimates, auth)
        val expenses = ExpenseRepository(db, recorder, estimates, projects, auth)

        init {
            runBlocking {
                auth.ensureRoles()
                engine.setDeviceName(name)
            }
        }

        fun close() = db.close()
    }

    private lateinit var log: MemoryLog
    private lateinit var a: Device
    private lateinit var b: Device
    private lateinit var actorA: CurrentUser
    private lateinit var actorB: CurrentUser

    @Before
    fun setUp() = runBlocking {
        log = MemoryLog()
        a = Device("A")
        b = Device("B")
        actorA = a.auth.createUser("admin", "secret123", "Admin", RoleCode.ADMIN)
        actorB = b.auth.createUser("admin", "secret123", "Admin", RoleCode.ADMIN)
    }

    @After
    fun tearDown() {
        a.close()
        b.close()
    }

    private fun sync(device: Device): SyncEngine.Report =
        runBlocking { device.engine.synchronize(log) }

    @Test
    fun `project replicates with the same uid`() = runBlocking {
        val id = a.projects.save(
            actorA,
            ProjectRow(name = "Sinxron uy", plannedBudget = 50_000_000.0, status = "active"),
        )
        val uidA = a.db.dao().project(id)!!.uid

        assertTrue(sync(a).ok)
        val report = sync(b)
        assertTrue(report.errors.toString(), report.ok)

        val onB = b.db.dao().projects().single()
        assertEquals("Sinxron uy", onB.name)
        assertEquals(50_000_000.0, onB.plannedBudget, 0.01)
        assertEquals(uidA, onB.uid)
    }

    @Test
    fun `foreign keys are rebuilt from uids not copied`() = runBlocking {
        val projectId = a.projects.save(actorA, ProjectRow(name = "FK", plannedBudget = 1.0))
        val version = a.estimates.ensureVersion(projectId)
        val sectionId = a.estimates.addSection(actorA, version.id, "Beton", null, "1")
        a.estimates.saveItem(
            actorA,
            EstimateItemRow(sectionId = sectionId, name = "Beton quyish", quantity = 10.0, planUnitPrice = 500_000.0),
        )

        sync(a)
        assertTrue(sync(b).ok)

        val projectB = b.db.dao().projects().single()
        val versionB = b.db.dao().currentVersion(projectB.id)!!
        val sectionB = b.db.dao().sections(versionB.id).single()
        val itemB = b.db.dao().items(versionB.id).single()

        assertEquals("Beton quyish", itemB.name)
        // The local ids differ per device; the link must still be correct.
        assertEquals(sectionB.id, itemB.sectionId)
        assertEquals(5_000_000.0, itemB.planTotal, 0.01)
    }

    @Test
    fun `stock movements and estimate actuals survive replication`() = runBlocking {
        val projectId = a.projects.save(actorA, ProjectRow(name = "Ombor", plannedBudget = 100_000_000.0))
        val version = a.estimates.ensureVersion(projectId)
        val sectionId = a.estimates.addSection(actorA, version.id, "Beton", null, "1")
        val itemId = a.estimates.saveItem(
            actorA,
            EstimateItemRow(sectionId = sectionId, name = "Sement", quantity = 100.0, planUnitPrice = 50_000.0),
        )
        val materialId = a.warehouse.saveMaterial(
            actorA,
            MaterialRow(sku = "S-1", name = "Sement", unit = "piece", standardPrice = 55_000.0),
        )
        a.warehouse.registerMove(
            actorA,
            WarehouseTxRow(materialId = materialId, kind = TxKind.IN, quantity = 100.0, unitPrice = 55_000.0),
        )
        a.warehouse.registerMove(
            actorA,
            WarehouseTxRow(
                materialId = materialId, kind = TxKind.OUT, quantity = 40.0, unitPrice = 55_000.0,
                projectId = projectId, estimateItemId = itemId,
            ),
        )

        sync(a)
        assertTrue(sync(b).ok)

        val materialB = b.db.dao().materialBySku("S-1")!!
        assertEquals(60.0, b.db.dao().stockBalance(materialB.id), 0.01)

        val projectB = b.db.dao().projects().single()
        b.estimates.recalcActuals(projectB.id)
        val totals = b.projects.totals(projectB.id)
        assertEquals(2_200_000.0, totals.materialIssued, 0.01)
        assertEquals(2_200_000.0, totals.actual, 0.01)
    }

    @Test
    fun `last write wins on conflicting edits`() = runBlocking {
        val id = a.projects.save(actorA, ProjectRow(name = "Konflikt", plannedBudget = 100.0))
        sync(a)
        sync(b)

        a.projects.save(actorA, a.db.dao().project(id)!!.copy(name = "A varianti"))
        Thread.sleep(5)
        val onB = b.db.dao().projects().single()
        b.projects.save(actorB, onB.copy(name = "B varianti"))

        sync(a)
        sync(b)
        sync(a)

        assertEquals("B varianti", a.db.dao().project(id)!!.name)
        assertEquals("B varianti", b.db.dao().projects().single().name)
    }

    @Test
    fun `rows created independently merge on their natural key`() = runBlocking {
        // Both devices already created an `admin` user in setUp().
        sync(a)
        sync(b)
        sync(a)
        assertEquals(1, a.db.dao().users().count { it.username == "admin" })
        assertEquals(1, b.db.dao().users().count { it.username == "admin" })
    }

    @Test
    fun `a device never re-applies its own changes`() = runBlocking {
        a.projects.save(actorA, ProjectRow(name = "Echo", plannedBudget = 1.0))
        val first = sync(a)
        assertTrue(first.pushed > 0)
        assertEquals(0, first.applied)
        assertEquals(first.pulled, first.skippedOwn)
        assertEquals(1, a.db.dao().projects().size)
    }

    @Test
    fun `deletes propagate`() = runBlocking {
        val projectId = a.projects.save(actorA, ProjectRow(name = "O'chirish", plannedBudget = 1.0))
        val version = a.estimates.ensureVersion(projectId)
        val sectionId = a.estimates.addSection(actorA, version.id, "Bo'lim", null, "1")
        val itemId = a.estimates.saveItem(
            actorA,
            EstimateItemRow(sectionId = sectionId, name = "Band", quantity = 1.0, planUnitPrice = 100.0),
        )
        sync(a)
        sync(b)
        val projectB = b.db.dao().projects().single()
        val versionB = b.db.dao().currentVersion(projectB.id)!!
        assertEquals(1, b.db.dao().items(versionB.id).size)

        a.estimates.deleteItem(actorA, a.db.dao().item(itemId)!!)
        sync(a)
        assertTrue(sync(b).ok)
        assertEquals(0, b.db.dao().items(versionB.id).size)
    }

    @Test
    fun `outbox payload uses uids for foreign keys and wrapped timestamps`() = runBlocking {
        val projectId = a.projects.save(actorA, ProjectRow(name = "Payload", plannedBudget = 5.0))
        val project = a.db.dao().project(projectId)!!
        val row = a.db.syncDao().outboxBatch(50).first { it.entity == "Project" && it.uid == project.uid }
        val payload = uz.buildcontrol.mobile.data.sync.SyncCodec.jsonToObject(row.payload)

        assertEquals("Payload", payload["name"]!!.jsonPrimitive.content)
        // sync_ts is wrapped the way Python encodes datetimes
        assertNotNull(payload["sync_ts"]!!.jsonObject["__dt__"])
        // start_date is null here, but the key must still travel
        assertTrue(payload.containsKey("start_date"))
        // manager_id is a foreign key: absent means JSON null, never a local id
        assertTrue(payload.containsKey("manager_id"))
        assertNull(payload["id"])
    }

    @Test
    fun `pending counter clears after a successful push`() = runBlocking {
        a.projects.save(actorA, ProjectRow(name = "Hisob", plannedBudget = 1.0))
        assertTrue(a.db.syncDao().pendingCount() > 0)
        sync(a)
        assertEquals(0, a.db.syncDao().pendingCount())
        assertTrue(a.engine.state().cursor.isNotEmpty())
    }
}
