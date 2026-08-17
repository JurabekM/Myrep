package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.EstimateVersionRow
import uz.buildcontrol.mobile.data.db.ProjectRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied
import uz.buildcontrol.mobile.domain.ProjectStatus
import uz.buildcontrol.mobile.domain.ProjectTotals
import uz.buildcontrol.mobile.domain.StageStatus

/** Projects and the aggregated figures shown on the overview. */
class ProjectRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    fun observeProjects(includeArchived: Boolean): Flow<List<ProjectRow>> =
        dao.observeProjects(includeArchived)

    fun observeProject(id: Long): Flow<ProjectRow?> = dao.observeProject(id)

    suspend fun project(id: Long): ProjectRow? = withContext(Dispatchers.IO) { dao.project(id) }

    suspend fun projects(): List<ProjectRow> = withContext(Dispatchers.IO) { dao.projects() }

    /** Same cost conventions as the desktop: committed + material issues. */
    suspend fun totals(projectId: Long): ProjectTotals = withContext(Dispatchers.IO) {
        val project = dao.project(projectId) ?: return@withContext ProjectTotals()
        val version = dao.currentVersion(projectId)
        val stages = dao.stages(projectId)
        ProjectTotals(
            plannedBudget = project.plannedBudget,
            estimateTotal = version?.let { dao.estimatePlanTotal(it.id) } ?: 0.0,
            committed = dao.committedCost(projectId),
            pending = dao.pendingCost(projectId),
            materialIssued = dao.materialIssuedValue(projectId),
            delayedStages = stages.count { it.status == StageStatus.DELAYED },
            totalStages = stages.size,
            doneStages = stages.count { it.status == StageStatus.DONE },
            pendingPurchases = dao.pendingRequests(projectId),
            overBudgetItems = version?.let { dao.overBudgetItems(it.id) } ?: 0,
            avgProgress = if (stages.isEmpty()) 0.0
            else stages.sumOf { it.progressPercent } / stages.size,
        )
    }

    suspend fun save(actor: CurrentUser, row: ProjectRow): Long = withContext(Dispatchers.IO) {
        if (!actor.can(Perm.PROJECT_EDIT)) throw PermissionDenied(Perm.PROJECT_EDIT)
        db.withTransaction {
            val stamped = row.copy(syncTs = now(), updatedAt = now())
            val id: Long
            if (stamped.id == 0L) {
                val code = stamped.code.ifBlank { nextCode() }
                val created = stamped.copy(code = code)
                id = dao.insert(created)
                recorder.upsert("Project", created.uid)
                // Every project starts with an editable estimate version.
                val version = EstimateVersionRow(projectId = id, versionNo = 1, isCurrent = true)
                dao.insert(version)
                recorder.upsert("EstimateVersion", version.uid)
            } else {
                dao.update(stamped)
                recorder.upsert("Project", stamped.uid)
                id = stamped.id
            }
            auth.audit(
                actor,
                if (row.id == 0L) "create" else "update",
                "Project", id, id, row.name,
            )
            id
        }
    }

    suspend fun archive(actor: CurrentUser, project: ProjectRow, archived: Boolean) =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.PROJECT_ARCHIVE)) throw PermissionDenied(Perm.PROJECT_ARCHIVE)
            db.withTransaction {
                val updated = project.copy(
                    isArchived = archived,
                    status = if (archived) ProjectStatus.ARCHIVED else ProjectStatus.ACTIVE,
                    syncTs = now(),
                    updatedAt = now(),
                )
                dao.update(updated)
                recorder.upsert("Project", updated.uid)
                auth.audit(actor, "archive", "Project", project.id, project.id, project.name)
            }
        }

    private suspend fun nextCode(): String = "PRJ-%04d".format(dao.projectCount() + 1)

    /** Portfolio headline used on the projects screen. */
    suspend fun portfolio(): Triple<Int, Double, Double> = withContext(Dispatchers.IO) {
        val projects = dao.projects()
        var budget = 0.0
        var actual = 0.0
        for (project in projects) {
            budget += project.plannedBudget
            actual += dao.committedCost(project.id) + dao.materialIssuedValue(project.id)
        }
        Triple(projects.size, budget, actual)
    }

    fun today(): String = Fmt.today()
}
