package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.EstimateItemRow
import uz.buildcontrol.mobile.data.db.EstimateSectionRow
import uz.buildcontrol.mobile.data.db.EstimateVersionRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.EstimateStatus
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied

class EstimateLocked : Exception("estimate_locked")

/** Estimate tree, plan/actual recalculation and the approval workflow. */
class EstimateRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    data class Node(
        val section: EstimateSectionRow,
        val children: MutableList<Node> = mutableListOf(),
        val items: MutableList<EstimateItemRow> = mutableListOf(),
    ) {
        val planTotal: Double
            get() = items.sumOf { it.planTotal } + children.sumOf { it.planTotal }
        val actualTotal: Double
            get() = items.sumOf { it.actualCost } + children.sumOf { it.actualTotal }
        val variance: Double get() = actualTotal - planTotal
    }

    data class Tree(
        val version: EstimateVersionRow?,
        val roots: List<Node> = emptyList(),
        val items: List<EstimateItemRow> = emptyList(),
    ) {
        val planTotal: Double get() = roots.sumOf { it.planTotal }
        val actualTotal: Double get() = roots.sumOf { it.actualTotal }
        val variance: Double get() = actualTotal - planTotal
        val editable: Boolean get() = version?.status in EstimateStatus.editable
    }

    suspend fun currentVersion(projectId: Long): EstimateVersionRow? =
        withContext(Dispatchers.IO) { dao.currentVersion(projectId) }

    /** Ensure the project has an editable version (older desktop data may lack one). */
    suspend fun ensureVersion(projectId: Long): EstimateVersionRow = withContext(Dispatchers.IO) {
        dao.currentVersion(projectId) ?: db.withTransaction {
            val row = EstimateVersionRow(projectId = projectId, versionNo = 1, isCurrent = true)
            val id = dao.insert(row)
            recorder.upsert("EstimateVersion", row.uid)
            row.copy(id = id)
        }
    }

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    fun observeTree(projectId: Long): Flow<Tree> = flow {
        emit(dao.currentVersion(projectId))
    }.flatMapLatest { version ->
        if (version == null) {
            flowOf(Tree(null))
        } else {
            combineSectionsAndItems(version)
        }
    }

    @OptIn(kotlinx.coroutines.ExperimentalCoroutinesApi::class)
    private fun combineSectionsAndItems(version: EstimateVersionRow): Flow<Tree> =
        kotlinx.coroutines.flow.combine(
            dao.observeSections(version.id),
            dao.observeItems(version.id),
        ) { sections, items -> buildTree(version, sections, items) }

    private fun buildTree(
        version: EstimateVersionRow,
        sections: List<EstimateSectionRow>,
        items: List<EstimateItemRow>,
    ): Tree {
        val nodes = sections.associate { it.id to Node(it) }
        items.forEach { item -> nodes[item.sectionId]?.items?.add(item) }
        val roots = mutableListOf<Node>()
        for (section in sections) {
            val node = nodes[section.id] ?: continue
            val parent = section.parentId?.let { nodes[it] }
            if (parent != null) parent.children.add(node) else roots.add(node)
        }
        return Tree(version, roots, items)
    }

    suspend fun addSection(
        actor: CurrentUser,
        versionId: Long,
        name: String,
        parentId: Long?,
        code: String,
    ): Long = withContext(Dispatchers.IO) {
        guard(actor, versionId)
        db.withTransaction {
            val siblings = dao.sections(versionId).count { it.parentId == parentId }
            val row = EstimateSectionRow(
                versionId = versionId,
                parentId = parentId,
                name = name.trim(),
                code = code.ifBlank { autoCode(parentId, siblings) },
                orderIndex = siblings,
            )
            val id = dao.insert(row)
            recorder.upsert("EstimateSection", row.uid)
            id
        }
    }

    private suspend fun autoCode(parentId: Long?, index: Int): String {
        if (parentId == null) return "${index + 1}"
        val base = dao.section(parentId)?.code?.ifBlank { "1" } ?: "1"
        return "$base.${index + 1}"
    }

    suspend fun saveItem(actor: CurrentUser, row: EstimateItemRow): Long =
        withContext(Dispatchers.IO) {
            val sectionId = row.sectionId ?: throw IllegalArgumentException("section required")
            val versionId = dao.section(sectionId)?.versionId
            if (versionId != null) guard(actor, versionId) else requireEdit(actor)
            db.withTransaction {
                val stamped = row.copy(syncTs = now())
                val id: Long
                if (stamped.id == 0L) {
                    val ordered = stamped.copy(orderIndex = dao.itemCount(sectionId))
                    id = dao.insert(ordered)
                    recorder.upsert("EstimateItem", ordered.uid)
                } else {
                    dao.update(stamped)
                    recorder.upsert("EstimateItem", stamped.uid)
                    id = stamped.id
                }
                id
            }
        }

    suspend fun deleteItem(actor: CurrentUser, row: EstimateItemRow) = withContext(Dispatchers.IO) {
        requireEdit(actor)
        db.withTransaction {
            recorder.delete("EstimateItem", row.uid)
            dao.delete(row)
        }
    }

    /**
     * Refresh cached `actual_cost` from approved expenses and material issues,
     * exactly like `estimate_service.recalc_item_actuals` on the desktop.
     */
    suspend fun recalcActuals(projectId: Long) = withContext(Dispatchers.IO) {
        val version = dao.currentVersion(projectId) ?: return@withContext
        db.withTransaction {
            for (item in dao.items(version.id)) {
                val total = dao.itemExpenseTotal(item.id) + dao.itemIssuedValue(item.id)
                val rounded = Math.round(total * 100.0) / 100.0
                if (rounded != item.actualCost) {
                    val updated = item.copy(actualCost = rounded, syncTs = now())
                    dao.update(updated)
                    recorder.upsert("EstimateItem", updated.uid)
                }
            }
        }
    }

    suspend fun setStatus(actor: CurrentUser, version: EstimateVersionRow, status: String) =
        withContext(Dispatchers.IO) {
            val permission =
                if (status == EstimateStatus.APPROVED) Perm.ESTIMATE_APPROVE else Perm.ESTIMATE_EDIT
            if (!actor.can(permission)) throw PermissionDenied(permission)
            db.withTransaction {
                val updated = version.copy(
                    status = status,
                    approvedById = if (status == EstimateStatus.APPROVED) actor.id else version.approvedById,
                    approvedAt = if (status == EstimateStatus.APPROVED) now() else version.approvedAt,
                    syncTs = now(),
                    updatedAt = now(),
                )
                dao.update(updated)
                recorder.upsert("EstimateVersion", updated.uid)
                auth.audit(
                    actor,
                    if (status == EstimateStatus.APPROVED) "approve" else "update",
                    "EstimateVersion", version.id, version.projectId,
                    "estimate v${version.versionNo}", version.status, status,
                )
            }
        }

    private fun requireEdit(actor: CurrentUser) {
        if (!actor.can(Perm.ESTIMATE_EDIT)) throw PermissionDenied(Perm.ESTIMATE_EDIT)
    }

    private suspend fun guard(actor: CurrentUser, versionId: Long) {
        requireEdit(actor)
        val status = dao.version(versionId)?.status ?: EstimateStatus.DRAFT
        if (status !in EstimateStatus.editable) throw EstimateLocked()
    }

    /** Items of the current version, used by pickers. */
    suspend fun items(projectId: Long): List<EstimateItemRow> = withContext(Dispatchers.IO) {
        val version = dao.currentVersion(projectId) ?: return@withContext emptyList()
        dao.items(version.id)
    }

    suspend fun sections(projectId: Long): List<EstimateSectionRow> = withContext(Dispatchers.IO) {
        val version = dao.currentVersion(projectId) ?: return@withContext emptyList()
        dao.sections(version.id)
    }
}
