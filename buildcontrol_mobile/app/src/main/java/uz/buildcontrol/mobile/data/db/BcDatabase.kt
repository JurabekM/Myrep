package uz.buildcontrol.mobile.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase

@Database(
    entities = [
        RoleRow::class, UserRow::class, RefItemRow::class, CompanySettingsRow::class,
        CounterpartyRow::class, MaterialRow::class, ProjectRow::class, ProjectMemberRow::class,
        EstimateVersionRow::class, EstimateSectionRow::class, EstimateItemRow::class,
        PurchaseRequestRow::class, SupplierQuoteRow::class, PurchaseOrderRow::class,
        WarehouseTxRow::class, WorkStageRow::class, SiteLogRow::class, ExpenseRow::class,
        PaymentRow::class, AttachmentRow::class, AuditLogRow::class,
        OutboxRow::class, SyncStateRow::class, UidAliasRow::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class BcDatabase : RoomDatabase() {
    abstract fun dao(): BcDao
    abstract fun syncDao(): SyncDao

    companion object {
        private const val NAME = "buildcontrol.db"

        @Volatile private var instance: BcDatabase? = null

        fun get(context: Context): BcDatabase = instance ?: synchronized(this) {
            instance ?: Room.databaseBuilder(context.applicationContext, BcDatabase::class.java, NAME)
                .fallbackToDestructiveMigration()
                .build()
                .also { instance = it }
        }
    }
}
