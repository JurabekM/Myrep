package uz.buildcontrol.mobile.data.sync

import kotlinx.serialization.json.JsonObject
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.OutboxRow

/**
 * Records local writes so replication can replay them elsewhere.
 *
 * Repositories call [upsert] right after a write inside the same transaction —
 * the desktop achieves the same through SQLAlchemy session events.
 */
class SyncRecorder(private val db: BcDatabase) {

    private val syncDao = db.syncDao()

    /** Queue the current state of [uid] in [entity]. */
    suspend fun upsert(entity: String, uid: String) {
        val spec = SPEC_BY_ENTITY[entity] ?: return
        val raw = db.openHelper.writableDatabase
        val payload = SyncCodec.serialise(raw, spec, uid) ?: return
        syncDao.addOutbox(
            OutboxRow(
                entity = entity,
                uid = uid,
                op = Change.OP_UPSERT,
                payload = SyncJson.encodeToString(JsonObject.serializer(), payload),
            )
        )
    }

    /** Queue a deletion; must be called *before* the row disappears. */
    suspend fun delete(entity: String, uid: String) {
        if (!SPEC_BY_ENTITY.containsKey(entity)) return
        syncDao.addOutbox(
            OutboxRow(entity = entity, uid = uid, op = Change.OP_DELETE, payload = "")
        )
    }
}
