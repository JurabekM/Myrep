package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.SiteLogRow
import uz.buildcontrol.mobile.data.db.WorkStageRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied
import uz.buildcontrol.mobile.domain.StageStatus

/** Work stages, automatic delay detection and the daily site log. */
class WorkRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    fun observeStages(projectId: Long): Flow<List<WorkStageRow>> = dao.observeStages(projectId)

    fun observeLogs(projectId: Long): Flow<List<SiteLogRow>> = dao.observeSiteLogs(projectId)

    suspend fun stages(projectId: Long): List<WorkStageRow> =
        withContext(Dispatchers.IO) { dao.stages(projectId) }

    /**
     * Mark stages whose planned finish has passed while progress is below 100%.
     * Returns how many statuses changed.
     */
    suspend fun refreshDelays(projectId: Long): Int = withContext(Dispatchers.IO) {
        var changed = 0
        db.withTransaction {
            for (stage in dao.stages(projectId)) {
                if (stage.status in StageStatus.terminal) continue
                val overdue = Fmt.isPast(stage.planEnd)
                val incomplete = stage.progressPercent < 100.0
                val next = when {
                    overdue && incomplete && stage.status != StageStatus.DELAYED ->
                        StageStatus.DELAYED
                    !overdue && stage.status == StageStatus.DELAYED ->
                        if (stage.progressPercent > 0) StageStatus.IN_PROGRESS
                        else StageStatus.NOT_STARTED
                    else -> null
                }
                if (next != null) {
                    val updated = stage.copy(status = next, syncTs = now(), updatedAt = now())
                    dao.update(updated)
                    recorder.upsert("WorkStage", updated.uid)
                    changed++
                }
            }
        }
        changed
    }

    suspend fun saveStage(actor: CurrentUser, row: WorkStageRow): Long =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.STAGE_EDIT)) throw PermissionDenied(Perm.STAGE_EDIT)
            val id = db.withTransaction {
                val stamped = row.copy(syncTs = now(), updatedAt = now())
                val newId: Long
                if (stamped.id == 0L) {
                    val ordered = stamped.copy(
                        orderIndex = dao.stages(stamped.projectId ?: 0L).size
                    )
                    newId = dao.insert(ordered)
                    recorder.upsert("WorkStage", ordered.uid)
                } else {
                    dao.update(stamped)
                    recorder.upsert("WorkStage", stamped.uid)
                    newId = stamped.id
                }
                auth.audit(
                    actor, if (row.id == 0L) "create" else "update",
                    "WorkStage", newId, stamped.projectId, stamped.name,
                    newValue = "${stamped.status}/${stamped.progressPercent}",
                )
                newId
            }
            row.projectId?.let { refreshDelays(it) }
            id
        }

    /** Site log entry; progress is propagated to the linked stage. */
    suspend fun saveLog(actor: CurrentUser, row: SiteLogRow): Long = withContext(Dispatchers.IO) {
        if (!actor.can(Perm.STAGE_EDIT)) throw PermissionDenied(Perm.STAGE_EDIT)
        val id = db.withTransaction {
            val stamped = row.copy(authorId = actor.id, syncTs = now(), updatedAt = now())
            val newId = dao.insert(stamped)
            recorder.upsert("DailySiteLog", stamped.uid)

            val stage = stamped.stageId?.let { dao.stage(it) }
            if (stage != null && stamped.progressPercent > stage.progressPercent) {
                var updated = stage.copy(
                    progressPercent = stamped.progressPercent,
                    syncTs = now(),
                    updatedAt = now(),
                )
                updated = when {
                    updated.progressPercent >= 100 -> updated.copy(
                        status = StageStatus.DONE,
                        actualEnd = updated.actualEnd ?: stamped.logDate,
                    )
                    updated.status == StageStatus.NOT_STARTED -> updated.copy(
                        status = StageStatus.IN_PROGRESS,
                        actualStart = updated.actualStart ?: stamped.logDate,
                    )
                    else -> updated
                }
                dao.update(updated)
                recorder.upsert("WorkStage", updated.uid)
            }
            auth.audit(
                actor, "create", "DailySiteLog", newId, stamped.projectId,
                Fmt.short(stamped.workDone, 80),
            )
            newId
        }
        row.projectId?.let { refreshDelays(it) }
        id
    }
}
