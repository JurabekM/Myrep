package uz.distribos.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.sqlite.db.SupportSQLiteDatabase

/**
 * Telefondagi lokal baza.
 *
 * Bu ham to'liq huquqli haqiqat manbai — desktopning nusxasi emas.
 * Internet bo'lmasa telefon mustaqil ishlaydi va hodisalarni o'zi
 * yaratadi.
 */
@Database(
    entities = [
        ProductEntity::class,
        CustomerEntity::class,
        OrderEntity::class,
        OrderLineEntity::class,
        WarehouseEntity::class,
        MovementEntity::class,
        StockEntity::class,
        PaymentEntity::class,
        VisitEntity::class,
        EventEntity::class,
        OutboxEntity::class,
        InboxEntity::class,
        PeerDeviceEntity::class,
        EpochKeyEntity::class,
        ReplayWindowEntity::class,
        DeviceSequenceEntity::class,
        DeadLetterEntity::class,
        ConflictEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class DistribosDatabase : RoomDatabase() {

    abstract fun products(): ProductDao
    abstract fun customers(): CustomerDao
    abstract fun orders(): OrderDao
    abstract fun inventory(): InventoryDao
    abstract fun payments(): PaymentDao
    abstract fun visits(): VisitDao
    abstract fun sync(): SyncDao

    companion object {
        const val NAME = "distribos.db"

        fun build(context: Context, name: String = NAME): DistribosDatabase =
            Room.databaseBuilder(context, DistribosDatabase::class.java, name)
                .addCallback(object : Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        // SQLite'da foreign key tekshiruvi DEFAULT O'CHIQ.
                        db.execSQL("PRAGMA foreign_keys = ON")
                        installImmutabilityTriggers(db)
                    }
                })
                // Migratsiyasiz halokatli qayta qurish TAQIQLANADI: u
                // foydalanuvchining yuborilmagan buyurtmalarini jimgina
                // o'chirib yuborardi.
                .build()

        fun buildInMemory(context: Context): DistribosDatabase =
            Room.inMemoryDatabaseBuilder(context, DistribosDatabase::class.java)
                .addCallback(object : Callback() {
                    override fun onOpen(db: SupportSQLiteDatabase) {
                        super.onOpen(db)
                        installImmutabilityTriggers(db)
                    }
                })
                .allowMainThreadQueries()
                .build()

        /**
         * O'zgarmaslik qulflari — BAZA darajasida.
         *
         * DAO qoidasini chetlab o'tish oson (xom SQL, boshqa kod yo'li).
         * Hodisa jurnali va ombor harakati "append-only" deyilsa, buni
         * bazaning o'zi majburlashi kerak. Desktop tomonida ham aynan shu
         * qulflar bor.
         */
        private fun installImmutabilityTriggers(db: SupportSQLiteDatabase) {
            db.execSQL("DROP TRIGGER IF EXISTS trg_event_log_no_delete")
            db.execSQL(
                """
                CREATE TRIGGER trg_event_log_no_delete
                BEFORE DELETE ON event_log
                BEGIN
                    SELECT RAISE(ABORT, 'event_log append-only: DELETE taqiqlanadi');
                END
                """.trimIndent()
            )

            db.execSQL("DROP TRIGGER IF EXISTS trg_event_log_immutable")
            db.execSQL(
                """
                CREATE TRIGGER trg_event_log_immutable
                BEFORE UPDATE ON event_log
                WHEN OLD.eventId IS NOT NEW.eventId
                  OR OLD.payload IS NOT NEW.payload
                  OR OLD.deviceId IS NOT NEW.deviceId
                  OR OLD.deviceSequence IS NOT NEW.deviceSequence
                  OR OLD.occurredAtMs IS NOT NEW.occurredAtMs
                BEGIN
                    SELECT RAISE(ABORT, 'event_log ozgarmas: faqat appliedAtMs yangilanadi');
                END
                """.trimIndent()
            )

            db.execSQL("DROP TRIGGER IF EXISTS trg_movement_no_update")
            db.execSQL(
                """
                CREATE TRIGGER trg_movement_no_update
                BEFORE UPDATE ON inventory_movement
                BEGIN
                    SELECT RAISE(ABORT, 'inventory_movement append-only: yangi harakat yarating');
                END
                """.trimIndent()
            )

            db.execSQL("DROP TRIGGER IF EXISTS trg_movement_no_delete")
            db.execSQL(
                """
                CREATE TRIGGER trg_movement_no_delete
                BEFORE DELETE ON inventory_movement
                BEGIN
                    SELECT RAISE(ABORT, 'inventory_movement append-only: DELETE taqiqlanadi');
                END
                """.trimIndent()
            )

            db.execSQL("DROP TRIGGER IF EXISTS trg_payment_immutable_amount")
            db.execSQL(
                """
                CREATE TRIGGER trg_payment_immutable_amount
                BEFORE UPDATE ON payment
                WHEN OLD.amount IS NOT NEW.amount
                  OR OLD.direction IS NOT NEW.direction
                  OR OLD.occurredAtMs IS NOT NEW.occurredAtMs
                BEGIN
                    SELECT RAISE(ABORT, 'tolov ozgarmas: reversal yozuvi yarating');
                END
                """.trimIndent()
            )

            db.execSQL("DROP TRIGGER IF EXISTS trg_payment_no_delete")
            db.execSQL(
                """
                CREATE TRIGGER trg_payment_no_delete
                BEFORE DELETE ON payment
                BEGIN
                    SELECT RAISE(ABORT, 'tolov ochirilmaydi: reversal yozuvi yarating');
                END
                """.trimIndent()
            )
        }
    }
}
