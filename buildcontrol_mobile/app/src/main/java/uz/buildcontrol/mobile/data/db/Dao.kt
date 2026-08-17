package uz.buildcontrol.mobile.data.db

import androidx.room.Dao
import androidx.room.Delete
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Update
import androidx.room.Upsert
import kotlinx.coroutines.flow.Flow

/** Typed queries used by the interface; replication uses raw SQL instead. */
@Dao
interface BcDao {

    // -- users / roles ------------------------------------------------------ //
    @Query("SELECT * FROM users WHERE username = :username LIMIT 1")
    suspend fun userByUsername(username: String): UserRow?

    @Query("SELECT * FROM users WHERE id = :id")
    suspend fun user(id: Long): UserRow?

    @Query("SELECT * FROM users WHERE is_archived = 0 ORDER BY full_name")
    suspend fun users(): List<UserRow>

    @Query("SELECT COUNT(*) FROM users")
    suspend fun userCount(): Int

    @Query("SELECT * FROM roles WHERE code = :code LIMIT 1")
    suspend fun roleByCode(code: String): RoleRow?

    @Query("SELECT * FROM roles WHERE id = :id")
    suspend fun role(id: Long): RoleRow?

    @Query("SELECT COUNT(*) FROM roles")
    suspend fun roleCount(): Int

    @Upsert suspend fun upsert(row: RoleRow): Long
    @Upsert suspend fun upsert(row: UserRow): Long

    // -- projects ----------------------------------------------------------- //
    @Query(
        "SELECT * FROM projects WHERE (:includeArchived = 1 OR is_archived = 0) " +
            "ORDER BY created_at DESC"
    )
    fun observeProjects(includeArchived: Boolean): Flow<List<ProjectRow>>

    @Query("SELECT * FROM projects WHERE id = :id")
    fun observeProject(id: Long): Flow<ProjectRow?>

    @Query("SELECT * FROM projects WHERE id = :id")
    suspend fun project(id: Long): ProjectRow?

    @Query("SELECT * FROM projects WHERE is_archived = 0 ORDER BY name")
    suspend fun projects(): List<ProjectRow>

    @Query("SELECT COUNT(*) FROM projects")
    suspend fun projectCount(): Int

    @Insert(onConflict = OnConflictStrategy.ABORT) suspend fun insert(row: ProjectRow): Long
    @Update suspend fun update(row: ProjectRow)

    // -- estimate ----------------------------------------------------------- //
    @Query(
        "SELECT * FROM estimate_versions WHERE project_id = :projectId AND is_current = 1 " +
            "ORDER BY version_no DESC LIMIT 1"
    )
    suspend fun currentVersion(projectId: Long): EstimateVersionRow?

    @Query("SELECT * FROM estimate_versions WHERE project_id = :projectId ORDER BY version_no DESC")
    suspend fun versions(projectId: Long): List<EstimateVersionRow>

    @Query("SELECT * FROM estimate_versions WHERE id = :id")
    suspend fun version(id: Long): EstimateVersionRow?

    @Query("SELECT * FROM estimate_sections WHERE id = :id")
    suspend fun section(id: Long): EstimateSectionRow?

    @Insert suspend fun insert(row: EstimateVersionRow): Long
    @Update suspend fun update(row: EstimateVersionRow)

    @Query("SELECT * FROM estimate_sections WHERE version_id = :versionId ORDER BY order_index, id")
    fun observeSections(versionId: Long): Flow<List<EstimateSectionRow>>

    @Query("SELECT * FROM estimate_sections WHERE version_id = :versionId ORDER BY order_index, id")
    suspend fun sections(versionId: Long): List<EstimateSectionRow>

    @Insert suspend fun insert(row: EstimateSectionRow): Long
    @Update suspend fun update(row: EstimateSectionRow)
    @Delete suspend fun delete(row: EstimateSectionRow)

    @Query(
        "SELECT i.* FROM estimate_items i JOIN estimate_sections s ON i.section_id = s.id " +
            "WHERE s.version_id = :versionId ORDER BY i.order_index, i.id"
    )
    fun observeItems(versionId: Long): Flow<List<EstimateItemRow>>

    @Query(
        "SELECT i.* FROM estimate_items i JOIN estimate_sections s ON i.section_id = s.id " +
            "WHERE s.version_id = :versionId ORDER BY i.order_index, i.id"
    )
    suspend fun items(versionId: Long): List<EstimateItemRow>

    @Query("SELECT * FROM estimate_items WHERE id = :id")
    suspend fun item(id: Long): EstimateItemRow?

    @Query("SELECT COUNT(*) FROM estimate_items WHERE section_id = :sectionId")
    suspend fun itemCount(sectionId: Long): Int

    @Insert suspend fun insert(row: EstimateItemRow): Long
    @Update suspend fun update(row: EstimateItemRow)
    @Delete suspend fun delete(row: EstimateItemRow)

    @Query(
        "SELECT COALESCE(SUM(i.quantity * i.plan_unit_price), 0) FROM estimate_items i " +
            "JOIN estimate_sections s ON i.section_id = s.id WHERE s.version_id = :versionId"
    )
    suspend fun estimatePlanTotal(versionId: Long): Double

    @Query(
        "SELECT COUNT(*) FROM estimate_items i JOIN estimate_sections s ON i.section_id = s.id " +
            "WHERE s.version_id = :versionId AND i.actual_cost > 0 " +
            "AND i.actual_cost > i.quantity * i.plan_unit_price"
    )
    suspend fun overBudgetItems(versionId: Long): Int

    // -- materials / warehouse ---------------------------------------------- //
    @Query("SELECT * FROM materials WHERE is_archived = 0 ORDER BY name")
    fun observeMaterials(): Flow<List<MaterialRow>>

    @Query("SELECT * FROM materials WHERE is_archived = 0 ORDER BY name")
    suspend fun materials(): List<MaterialRow>

    @Query("SELECT * FROM materials WHERE id = :id")
    suspend fun material(id: Long): MaterialRow?

    @Query("SELECT * FROM materials WHERE sku = :sku LIMIT 1")
    suspend fun materialBySku(sku: String): MaterialRow?

    @Insert suspend fun insert(row: MaterialRow): Long
    @Update suspend fun update(row: MaterialRow)

    @Query(
        "SELECT COALESCE(SUM(CASE WHEN kind IN ('in','return','adjust') THEN quantity " +
            "ELSE -quantity END), 0) FROM warehouse_transactions WHERE material_id = :materialId"
    )
    suspend fun stockBalance(materialId: Long): Double

    @Query("SELECT * FROM warehouse_transactions ORDER BY tx_date DESC, id DESC LIMIT :limit")
    fun observeStockMoves(limit: Int): Flow<List<WarehouseTxRow>>

    @Query(
        "SELECT * FROM warehouse_transactions WHERE project_id = :projectId " +
            "ORDER BY tx_date DESC, id DESC"
    )
    fun observeStockMovesForProject(projectId: Long): Flow<List<WarehouseTxRow>>

    @Insert suspend fun insert(row: WarehouseTxRow): Long

    @Query(
        "SELECT COALESCE(SUM(quantity * unit_price), 0) FROM warehouse_transactions " +
            "WHERE project_id = :projectId AND kind = 'out'"
    )
    suspend fun materialIssuedValue(projectId: Long): Double

    @Query(
        "SELECT COALESCE(SUM(quantity * unit_price), 0) FROM warehouse_transactions " +
            "WHERE estimate_item_id = :itemId AND kind = 'out'"
    )
    suspend fun itemIssuedValue(itemId: Long): Double

    // -- stages ------------------------------------------------------------- //
    @Query(
        "SELECT * FROM work_stages WHERE project_id = :projectId AND is_archived = 0 " +
            "ORDER BY order_index, id"
    )
    fun observeStages(projectId: Long): Flow<List<WorkStageRow>>

    @Query("SELECT * FROM work_stages WHERE project_id = :projectId AND is_archived = 0")
    suspend fun stages(projectId: Long): List<WorkStageRow>

    @Query("SELECT * FROM work_stages WHERE id = :id")
    suspend fun stage(id: Long): WorkStageRow?

    @Insert suspend fun insert(row: WorkStageRow): Long
    @Update suspend fun update(row: WorkStageRow)

    @Query("SELECT * FROM daily_site_logs WHERE project_id = :projectId ORDER BY log_date DESC, id DESC")
    fun observeSiteLogs(projectId: Long): Flow<List<SiteLogRow>>

    @Insert suspend fun insert(row: SiteLogRow): Long

    // -- purchases ---------------------------------------------------------- //
    @Query(
        "SELECT * FROM purchase_requests WHERE is_archived = 0 " +
            "AND (:projectId IS NULL OR project_id = :projectId) ORDER BY created_at DESC"
    )
    fun observeRequests(projectId: Long?): Flow<List<PurchaseRequestRow>>

    @Query("SELECT * FROM purchase_requests WHERE id = :id")
    suspend fun request(id: Long): PurchaseRequestRow?

    @Query("SELECT COUNT(*) FROM purchase_requests WHERE project_id = :projectId AND status = 'submitted' AND is_archived = 0")
    suspend fun pendingRequests(projectId: Long): Int

    @Query("SELECT COUNT(*) FROM purchase_requests")
    suspend fun requestCount(): Int

    @Insert suspend fun insert(row: PurchaseRequestRow): Long
    @Update suspend fun update(row: PurchaseRequestRow)

    @Query("SELECT * FROM supplier_quotes WHERE request_id = :requestId ORDER BY unit_price")
    fun observeQuotes(requestId: Long): Flow<List<SupplierQuoteRow>>

    @Query("SELECT * FROM supplier_quotes WHERE request_id = :requestId ORDER BY unit_price")
    suspend fun quotes(requestId: Long): List<SupplierQuoteRow>

    @Insert suspend fun insert(row: SupplierQuoteRow): Long
    @Update suspend fun update(row: SupplierQuoteRow)

    // -- counterparties ----------------------------------------------------- //
    @Query(
        "SELECT * FROM counterparties WHERE is_archived = 0 " +
            "AND (:kind = '' OR kind = :kind) ORDER BY name"
    )
    fun observeCounterparties(kind: String): Flow<List<CounterpartyRow>>

    @Query("SELECT * FROM counterparties WHERE is_archived = 0 ORDER BY name")
    suspend fun counterparties(): List<CounterpartyRow>

    @Query("SELECT * FROM counterparties WHERE id = :id")
    suspend fun counterparty(id: Long): CounterpartyRow?

    @Insert suspend fun insert(row: CounterpartyRow): Long
    @Update suspend fun update(row: CounterpartyRow)

    // -- expenses ----------------------------------------------------------- //
    @Query(
        "SELECT * FROM expenses WHERE is_archived = 0 " +
            "AND (:projectId IS NULL OR project_id = :projectId) " +
            "AND (:status = '' OR status = :status) ORDER BY pay_date DESC, id DESC"
    )
    fun observeExpenses(projectId: Long?, status: String): Flow<List<ExpenseRow>>

    @Query("SELECT * FROM expenses WHERE id = :id")
    suspend fun expense(id: Long): ExpenseRow?

    @Insert suspend fun insert(row: ExpenseRow): Long
    @Update suspend fun update(row: ExpenseRow)

    @Query(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE project_id = :projectId " +
            "AND is_archived = 0 AND status IN ('approved','paid')"
    )
    suspend fun committedCost(projectId: Long): Double

    @Query(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE project_id = :projectId " +
            "AND is_archived = 0 AND status = 'pending'"
    )
    suspend fun pendingCost(projectId: Long): Double

    @Query(
        "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE estimate_item_id = :itemId " +
            "AND is_archived = 0 AND status IN ('approved','paid')"
    )
    suspend fun itemExpenseTotal(itemId: Long): Double

    @Query("SELECT COALESCE(SUM(amount), 0) FROM payments WHERE expense_id = :expenseId")
    suspend fun paidTotal(expenseId: Long): Double

    @Insert suspend fun insert(row: PaymentRow): Long

    // -- audit -------------------------------------------------------------- //
    @Query(
        "SELECT * FROM audit_logs WHERE (:projectId IS NULL OR project_id = :projectId) " +
            "ORDER BY ts DESC LIMIT :limit"
    )
    fun observeAudit(projectId: Long?, limit: Int): Flow<List<AuditLogRow>>

    @Insert suspend fun insert(row: AuditLogRow): Long

    // -- company ------------------------------------------------------------ //
    @Query("SELECT * FROM company_settings LIMIT 1")
    suspend fun company(): CompanySettingsRow?

    @Upsert suspend fun upsert(row: CompanySettingsRow): Long
}

/** Replication bookkeeping. */
@Dao
interface SyncDao {

    @Insert suspend fun addOutbox(row: OutboxRow): Long

    @Query("SELECT * FROM sync_outbox ORDER BY id LIMIT :limit")
    suspend fun outboxBatch(limit: Int): List<OutboxRow>

    @Query("DELETE FROM sync_outbox WHERE id IN (:ids)")
    suspend fun clearOutbox(ids: List<Long>)

    @Query("DELETE FROM sync_outbox")
    suspend fun clearAllOutbox()

    @Query("SELECT COUNT(*) FROM sync_outbox")
    suspend fun pendingCount(): Int

    @Query("SELECT COUNT(*) FROM sync_outbox")
    fun observePendingCount(): Flow<Int>

    @Query("SELECT * FROM sync_state WHERE id = 1")
    suspend fun state(): SyncStateRow?

    @Query("SELECT * FROM sync_state WHERE id = 1")
    fun observeState(): Flow<SyncStateRow?>

    @Upsert suspend fun upsertState(row: SyncStateRow)

    @Query("SELECT local_uid FROM sync_uid_alias WHERE entity = :entity AND foreign_uid = :uid LIMIT 1")
    suspend fun aliasOf(entity: String, uid: String): String?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun putAlias(row: UidAliasRow)
}
