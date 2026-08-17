package uz.buildcontrol.mobile.data.repo

import androidx.room.withTransaction
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.db.BcDatabase
import uz.buildcontrol.mobile.data.db.MaterialRow
import uz.buildcontrol.mobile.data.db.WarehouseTxRow
import uz.buildcontrol.mobile.data.db.now
import uz.buildcontrol.mobile.data.sync.SyncRecorder
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.domain.Perm
import uz.buildcontrol.mobile.domain.PermissionDenied
import uz.buildcontrol.mobile.domain.TxKind

class StockException(val key: String) : Exception(key)

/** Material catalogue and stock movements. */
class WarehouseRepository(
    private val db: BcDatabase,
    private val recorder: SyncRecorder,
    private val estimates: EstimateRepository,
    private val auth: AuthRepository,
) {
    private val dao = db.dao()

    data class StockRow(
        val material: MaterialRow,
        val balance: Double,
    ) {
        val value: Double get() = balance * material.standardPrice
        val isLow: Boolean get() = balance < material.minStock
    }

    fun observeStock(): Flow<List<StockRow>> = dao.observeMaterials().map { materials ->
        materials.map { StockRow(it, dao.stockBalance(it.id)) }
    }

    suspend fun stock(): List<StockRow> = withContext(Dispatchers.IO) {
        dao.materials().map { StockRow(it, dao.stockBalance(it.id)) }
    }

    suspend fun materials(): List<MaterialRow> = withContext(Dispatchers.IO) { dao.materials() }

    suspend fun balance(materialId: Long): Double =
        withContext(Dispatchers.IO) { dao.stockBalance(materialId) }

    fun observeMoves(limit: Int = 200): Flow<List<WarehouseTxRow>> = dao.observeStockMoves(limit)

    fun observeMovesForProject(projectId: Long): Flow<List<WarehouseTxRow>> =
        dao.observeStockMovesForProject(projectId)

    suspend fun saveMaterial(actor: CurrentUser, row: MaterialRow): Long =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.WAREHOUSE_EDIT)) throw PermissionDenied(Perm.WAREHOUSE_EDIT)
            db.withTransaction {
                val stamped = row.copy(syncTs = now(), updatedAt = now())
                if (stamped.id == 0L) {
                    if (dao.materialBySku(stamped.sku) != null) throw StockException("sku_exists")
                    val id = dao.insert(stamped)
                    recorder.upsert("Material", stamped.uid)
                    id
                } else {
                    dao.update(stamped)
                    recorder.upsert("Material", stamped.uid)
                    stamped.id
                }
            }
        }

    /**
     * Register a movement. Issues, losses and negative adjustments are refused
     * when the balance is insufficient, so stock can never go negative.
     */
    suspend fun registerMove(actor: CurrentUser, row: WarehouseTxRow): Long =
        withContext(Dispatchers.IO) {
            if (!actor.can(Perm.WAREHOUSE_EDIT)) throw PermissionDenied(Perm.WAREHOUSE_EDIT)
            val materialId = row.materialId ?: throw StockException("required_field")
            if (row.quantity <= 0) throw StockException("quantity_positive")
            if (row.kind !in TxKind.positive && dao.stockBalance(materialId) < row.quantity) {
                throw StockException("not_enough_stock")
            }
            val id = db.withTransaction {
                val stamped = row.copy(userId = actor.id, syncTs = now(), updatedAt = now())
                val newId = dao.insert(stamped)
                recorder.upsert("WarehouseTransaction", stamped.uid)
                auth.audit(
                    actor, "stock", "WarehouseTransaction", newId, stamped.projectId,
                    "${stamped.kind}: ${dao.material(materialId)?.name.orEmpty()}",
                    newValue = "${stamped.quantity} x ${stamped.unitPrice}",
                )
                newId
            }
            row.projectId?.let { estimates.recalcActuals(it) }
            id
        }
}
