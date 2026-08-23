package uz.distribos.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import androidx.room.Update
import kotlinx.coroutines.flow.Flow

@Dao
interface ProductDao {
    @Query("SELECT * FROM product WHERE isActive = 1 ORDER BY name")
    fun observeAll(): Flow<List<ProductEntity>>

    @Query(
        "SELECT * FROM product WHERE isActive = 1 AND " +
            "(name LIKE '%' || :query || '%' OR sku LIKE '%' || :query || '%' " +
            "OR barcode LIKE '%' || :query || '%') ORDER BY name LIMIT 200"
    )
    fun search(query: String): Flow<List<ProductEntity>>

    @Query("SELECT * FROM product WHERE barcode = :barcode LIMIT 1")
    suspend fun findByBarcode(barcode: String): ProductEntity?

    @Query("SELECT * FROM product WHERE id = :id")
    suspend fun byId(id: String): ProductEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(product: ProductEntity)

    @Query("SELECT COUNT(*) FROM product")
    suspend fun count(): Int
}

@Dao
interface CustomerDao {
    @Query("SELECT * FROM customer WHERE isActive = 1 ORDER BY name")
    fun observeAll(): Flow<List<CustomerEntity>>

    @Query(
        "SELECT * FROM customer WHERE isActive = 1 AND " +
            "(name LIKE '%' || :query || '%' OR code LIKE '%' || :query || '%' " +
            "OR phone LIKE '%' || :query || '%') ORDER BY name LIMIT 200"
    )
    fun search(query: String): Flow<List<CustomerEntity>>

    @Query("SELECT * FROM customer WHERE id = :id")
    suspend fun byId(id: String): CustomerEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(customer: CustomerEntity)

    /**
     * Mijoz qarzi = buyurtmalar - sof to'lovlar.
     *
     * DIQQAT: `paidTotal` ISHLATILMAYDI. U faqat to'lov aniq buyurtmaga
     * biriktirilganda o'sadi, real savdoda esa mijoz ko'pincha "hisobga"
     * umumiy summa to'laydi. Desktop tomonida ham aynan shunday
     * hisoblanadi — ikkalasi bir xil raqam ko'rsatishi SHART.
     */
    @Query(
        """
        SELECT
          COALESCE((SELECT SUM(total) FROM sales_order
                    WHERE customerId = :customerId AND state != 'CANCELLED'), 0)
          -
          COALESCE((SELECT SUM(CASE WHEN direction = 'IN' THEN amount ELSE -amount END)
                    FROM payment WHERE customerId = :customerId), 0)
        """
    )
    suspend fun debt(customerId: String): Long
}

@Dao
interface OrderDao {
    @Query("SELECT * FROM sales_order ORDER BY orderedAtMs DESC LIMIT 300")
    fun observeRecent(): Flow<List<OrderEntity>>

    @Query("SELECT * FROM sales_order WHERE state = :state ORDER BY orderedAtMs DESC")
    fun observeByState(state: String): Flow<List<OrderEntity>>

    @Query("SELECT * FROM sales_order WHERE id = :id")
    suspend fun byId(id: String): OrderEntity?

    @Query("SELECT * FROM order_line WHERE orderId = :orderId")
    suspend fun lines(orderId: String): List<OrderLineEntity>

    @Query("SELECT * FROM order_line WHERE orderId = :orderId")
    fun observeLines(orderId: String): Flow<List<OrderLineEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(order: OrderEntity)

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertLines(lines: List<OrderLineEntity>)

    @Update
    suspend fun update(order: OrderEntity)

    @Query("SELECT COUNT(*) FROM sales_order WHERE number LIKE :prefix || '%'")
    suspend fun countWithPrefix(prefix: String): Int
}

@Dao
interface InventoryDao {
    @Query("SELECT * FROM warehouse WHERE isActive = 1 ORDER BY name")
    fun observeWarehouses(): Flow<List<WarehouseEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertWarehouse(warehouse: WarehouseEntity)

    @Query("SELECT * FROM warehouse WHERE id = :id")
    suspend fun warehouseById(id: String): WarehouseEntity?

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertMovement(movement: MovementEntity): Long

    @Query("SELECT * FROM inventory_movement WHERE id = :id")
    suspend fun movementById(id: String): MovementEntity?

    @Query(
        "SELECT movementType, quantity FROM inventory_movement " +
            "WHERE warehouseId = :warehouseId AND productId = :productId " +
            "ORDER BY occurredAtMs"
    )
    suspend fun movementsFor(warehouseId: String, productId: String): List<MovementRow>

    @Query("SELECT * FROM inventory_movement ORDER BY occurredAtMs DESC LIMIT :limit")
    fun observeMovements(limit: Int = 200): Flow<List<MovementEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertStock(stock: StockEntity)

    @Query("SELECT * FROM stock_snapshot")
    fun observeStock(): Flow<List<StockEntity>>

    @Query("SELECT * FROM stock_snapshot WHERE productId = :productId")
    suspend fun stockFor(productId: String): List<StockEntity>
}

data class MovementRow(val movementType: String, val quantity: String)

@Dao
interface PaymentDao {
    @Query("SELECT * FROM payment ORDER BY occurredAtMs DESC LIMIT 200")
    fun observeRecent(): Flow<List<PaymentEntity>>

    @Query("SELECT * FROM payment WHERE id = :id")
    suspend fun byId(id: String): PaymentEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(payment: PaymentEntity)

    @Update
    suspend fun update(payment: PaymentEntity)
}

@Dao
interface VisitDao {
    @Query("SELECT * FROM visit ORDER BY startedAtMs DESC LIMIT 200")
    fun observeRecent(): Flow<List<VisitEntity>>

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(visit: VisitEntity)

    @Query("SELECT * FROM visit WHERE id = :id")
    suspend fun byId(id: String): VisitEntity?
}

@Dao
interface SyncDao {

    // --- hodisa jurnali ---------------------------------------------------

    @Insert(onConflict = OnConflictStrategy.ABORT)
    suspend fun insertEvent(event: EventEntity): Long

    @Query("SELECT * FROM event_log WHERE eventId = :eventId")
    suspend fun eventById(eventId: String): EventEntity?

    @Query("SELECT * FROM event_log WHERE idempotencyKey = :key LIMIT 1")
    suspend fun eventByIdempotencyKey(key: String): EventEntity?

    @Query(
        "SELECT * FROM event_log WHERE appliedAtMs IS NULL " +
            "ORDER BY deviceId, deviceSequence LIMIT :limit"
    )
    suspend fun unappliedEvents(limit: Int = 200): List<EventEntity>

    @Update
    suspend fun updateEvent(event: EventEntity)

    @Query(
        "SELECT * FROM event_log WHERE deviceId = :deviceId " +
            "AND deviceSequence BETWEEN :start AND :end ORDER BY deviceSequence LIMIT :limit"
    )
    suspend fun eventsInRange(
        deviceId: ByteArray, start: Long, end: Long, limit: Int = 50,
    ): List<EventEntity>

    @Query("SELECT deviceId, MAX(deviceSequence) AS highest FROM event_log GROUP BY deviceId")
    suspend fun digest(): List<DigestRow>

    @Query("SELECT COUNT(*) FROM event_log")
    suspend fun eventCount(): Int

    // --- hisoblagich ------------------------------------------------------

    @Query("SELECT * FROM device_sequence WHERE deviceIdHex = :deviceIdHex")
    suspend fun sequenceRow(deviceIdHex: String): DeviceSequenceEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertSequence(row: DeviceSequenceEntity)

    /**
     * Monotonik hisoblagichni ATOMAR oshiradi.
     *
     * Bir tranzaksiya ichida: ikki coroutine bir vaqtda chaqirsa ham bir
     * xil raqam bermaydi. Takror `seq` DES-1 nonce'ni takrorlaydi — bu
     * AEAD uchun halokatli.
     */
    @Transaction
    suspend fun allocateSequence(deviceIdHex: String): Long {
        val row = sequenceRow(deviceIdHex)
        return if (row == null) {
            upsertSequence(DeviceSequenceEntity(deviceIdHex, 2L))
            1L
        } else {
            upsertSequence(row.copy(nextSequence = row.nextSequence + 1))
            row.nextSequence
        }
    }

    // --- outbox / inbox ---------------------------------------------------

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertOutbox(entry: OutboxEntity)

    @Update
    suspend fun updateOutbox(entry: OutboxEntity)

    @Query(
        "SELECT * FROM outbox WHERE state IN ('LOCAL_COMMITTED','SEALED','QUEUED') " +
            "AND (nextAttemptAtMs IS NULL OR nextAttemptAtMs <= :now) ORDER BY rowId LIMIT :limit"
    )
    suspend fun pendingOutbox(now: Long, limit: Int = 50): List<OutboxEntity>

    @Query("SELECT * FROM outbox WHERE eventId IN (:eventIds)")
    suspend fun outboxFor(eventIds: List<String>): List<OutboxEntity>

    @Query("SELECT COUNT(*) FROM outbox WHERE state NOT IN ('PEER_APPLIED','DEAD_LETTER')")
    fun observeQueueDepth(): Flow<Int>

    @Query("SELECT COUNT(*) FROM outbox WHERE state NOT IN ('PEER_APPLIED','DEAD_LETTER')")
    suspend fun queueDepth(): Int

    @Query("SELECT * FROM inbox WHERE eventId = :eventId")
    suspend fun inboxEntry(eventId: String): InboxEntity?

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertInbox(entry: InboxEntity)

    @Update
    suspend fun updateInbox(entry: InboxEntity)

    // --- qurilmalar va kalitlar -------------------------------------------

    @Query("SELECT * FROM peer_device ORDER BY displayName")
    fun observePeers(): Flow<List<PeerDeviceEntity>>

    @Query("SELECT * FROM peer_device WHERE deviceIdHex = :deviceIdHex")
    suspend fun peer(deviceIdHex: String): PeerDeviceEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertPeer(peer: PeerDeviceEntity)

    @Query("SELECT * FROM epoch_key WHERE isCurrent = 1 LIMIT 1")
    suspend fun currentEpochKey(): EpochKeyEntity?

    @Query("SELECT * FROM epoch_key WHERE epoch = :epoch AND keyId = :keyId")
    suspend fun epochKey(epoch: Int, keyId: Long): EpochKeyEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertEpochKey(key: EpochKeyEntity)

    @Query("UPDATE epoch_key SET isCurrent = 0")
    suspend fun clearCurrentEpochKeys()

    // --- replay oynasi ----------------------------------------------------

    @Query("SELECT * FROM replay_window WHERE epoch = :epoch AND deviceIdHex = :deviceIdHex")
    suspend fun replayWindow(epoch: Int, deviceIdHex: String): ReplayWindowEntity?

    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsertReplayWindow(window: ReplayWindowEntity)

    // --- diagnostika ------------------------------------------------------

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertDeadLetter(entry: DeadLetterEntity)

    @Query("SELECT * FROM dead_letter WHERE resolvedAtMs IS NULL ORDER BY occurredAtMs DESC LIMIT 100")
    fun observeDeadLetters(): Flow<List<DeadLetterEntity>>

    @Query("SELECT COUNT(*) FROM dead_letter WHERE resolvedAtMs IS NULL")
    suspend fun deadLetterCount(): Int

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun insertConflict(entry: ConflictEntity)

    @Query("SELECT * FROM conflict WHERE status = 'NEEDS_REVIEW' ORDER BY detectedAtMs DESC")
    fun observeConflicts(): Flow<List<ConflictEntity>>
}

data class DigestRow(val deviceId: ByteArray, val highest: Long) {
    override fun equals(other: Any?): Boolean =
        this === other || (other is DigestRow && deviceId.contentEquals(other.deviceId))

    override fun hashCode(): Int = deviceId.contentHashCode()
}
