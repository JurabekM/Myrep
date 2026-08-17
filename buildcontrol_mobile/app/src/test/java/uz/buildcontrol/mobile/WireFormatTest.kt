package uz.buildcontrol.mobile

import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.buildJsonObject
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test
import uz.buildcontrol.mobile.data.sync.Change
import uz.buildcontrol.mobile.data.sync.SyncCodec
import uz.buildcontrol.mobile.data.sync.SyncJson
import uz.buildcontrol.mobile.domain.RoleCode
import uz.buildcontrol.mobile.domain.computeRating
import uz.buildcontrol.mobile.domain.hasPerm
import uz.buildcontrol.mobile.domain.Perm

/** The transport envelope and timestamp format must match Python byte for byte. */
class WireFormatTest {

    @Test
    fun `timestamps round-trip through the python iso format`() {
        val millis = 1_785_000_123_000L
        val iso = SyncCodec.millisToIso(millis)
        assertTrue("expected ISO-8601 with T separator: $iso", iso.contains('T'))
        assertEquals(millis, SyncCodec.isoToMillis(iso))
    }

    @Test
    fun `python microsecond timestamps are accepted`() {
        // datetime.now().isoformat() emits six fractional digits.
        val parsed = SyncCodec.isoToMillis("2026-08-03T14:05:06.123456")
        assertTrue(parsed != null && parsed > 0)
    }

    @Test
    fun `python space separated timestamps are accepted`() {
        assertTrue(SyncCodec.isoToMillis("2026-08-03 14:05:06") != null)
    }

    @Test
    fun `change envelope carries the fields postgrest expects`() {
        val change = Change(
            entity = "Project",
            uid = "abc123",
            op = Change.OP_UPSERT,
            payload = buildJsonObject { put("name", JsonPrimitive("Uy")) },
            ts = "2026-08-03T10:00:00",
            device = "dev-1",
        )
        val wire = change.toWire("firma").jsonObject
        assertEquals("firma", wire["tenant"]!!.jsonPrimitive.content)
        assertEquals("dev-1", wire["device"]!!.jsonPrimitive.content)
        assertEquals("Project", wire["entity"]!!.jsonPrimitive.content)
        assertEquals("abc123", wire["uid"]!!.jsonPrimitive.content)
        assertEquals("upsert", wire["op"]!!.jsonPrimitive.content)
        assertEquals("2026-08-03T10:00:00", wire["ts"]!!.jsonPrimitive.content)
        assertTrue(wire["payload"] is JsonObject)
    }

    @Test
    fun `rows coming back from postgrest are parsed`() {
        val row = SyncJson.parseToJsonElement(
            """
            {"seq": 42, "device": "desk-9", "entity": "EstimateItem", "uid": "u9",
             "op": "upsert", "ts": "2026-08-03T10:00:00+00:00",
             "payload": {"name": "Beton", "sync_ts": {"__dt__": "2026-08-03T10:00:00"},
                         "quantity": 10.0, "section_id": "sec-uid"}}
            """.trimIndent()
        ).jsonObject
        val change = Change.fromWire(row, "42")
        assertEquals("EstimateItem", change.entity)
        assertEquals("u9", change.uid)
        assertEquals("42", change.cursor)
        assertEquals("desk-9", change.device)
        assertEquals("Beton", change.payload["name"]!!.jsonPrimitive.content)
        assertTrue(SyncCodec.payloadSyncTs(change.payload) > 0)
    }

    @Test
    fun `payload sent as a json string is still parsed`() {
        val row = SyncJson.parseToJsonElement(
            """{"seq": 7, "entity": "Project", "uid": "p1", "op": "upsert",
                "payload": "{\"name\":\"Ofis\"}", "ts": "2026-08-03T10:00:00", "device": "d"}"""
        ).jsonObject
        val change = Change.fromWire(row, "7")
        assertEquals("Ofis", change.payload["name"]!!.jsonPrimitive.content)
    }

    @Test
    fun `permission matrix matches the desktop`() {
        assertTrue(hasPerm(RoleCode.ADMIN, Perm.SETTINGS_MANAGE))
        assertTrue(hasPerm(RoleCode.MANAGER, Perm.EXPENSE_APPROVE))
        assertTrue(!hasPerm(RoleCode.ESTIMATOR, Perm.EXPENSE_APPROVE))
        assertTrue(!hasPerm(RoleCode.ESTIMATOR, Perm.ESTIMATE_APPROVE))
        assertTrue(hasPerm(RoleCode.ESTIMATOR, Perm.ESTIMATE_EDIT))
        assertTrue(hasPerm(RoleCode.STOREKEEPER, Perm.WAREHOUSE_EDIT))
        assertTrue(!hasPerm(RoleCode.STOREKEEPER, Perm.ESTIMATE_EDIT))
        assertTrue(hasPerm(RoleCode.VIEWER, Perm.REPORT_VIEW))
        assertTrue(!hasPerm(RoleCode.VIEWER, Perm.PROJECT_EDIT))
    }

    @Test
    fun `contractor rating matches the desktop formula`() {
        assertEquals(5.0, computeRating(0, 100.0, 100.0, 5.0, 0), 0.001)
        assertTrue(computeRating(60, 100.0, 140.0, 2.0, 4) < 2.5)
    }
}
