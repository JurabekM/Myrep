package com.uzerp.mobile.data.local

import androidx.room.Database
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.uzerp.mobile.data.local.dao.AccountDao
import com.uzerp.mobile.data.local.dao.AssetDao
import com.uzerp.mobile.data.local.dao.AttendanceDao
import com.uzerp.mobile.data.local.dao.AuditDao
import com.uzerp.mobile.data.local.dao.CategoryDao
import com.uzerp.mobile.data.local.dao.CrmActivityDao
import com.uzerp.mobile.data.local.dao.CustomerDao
import com.uzerp.mobile.data.local.dao.DepartmentDao
import com.uzerp.mobile.data.local.dao.EmployeeDao
import com.uzerp.mobile.data.local.dao.InventoryCountDao
import com.uzerp.mobile.data.local.dao.JournalDao
import com.uzerp.mobile.data.local.dao.LeaveDao
import com.uzerp.mobile.data.local.dao.LeadDao
import com.uzerp.mobile.data.local.dao.PayrollDao
import com.uzerp.mobile.data.local.dao.PaymentDao
import com.uzerp.mobile.data.local.dao.ProductDao
import com.uzerp.mobile.data.local.dao.PurchaseDao
import com.uzerp.mobile.data.local.dao.PurchaseItemDao
import com.uzerp.mobile.data.local.dao.SalesDocDao
import com.uzerp.mobile.data.local.dao.SalesItemDao
import com.uzerp.mobile.data.local.dao.SequenceDao
import com.uzerp.mobile.data.local.dao.SettingsDao
import com.uzerp.mobile.data.local.dao.StockDao
import com.uzerp.mobile.data.local.dao.StockMoveDao
import com.uzerp.mobile.data.local.dao.SupplierDao
import com.uzerp.mobile.data.local.dao.UserDao
import com.uzerp.mobile.data.local.dao.WarehouseDao
import com.uzerp.mobile.data.local.entity.AccountEntity
import com.uzerp.mobile.data.local.entity.AssetEntity
import com.uzerp.mobile.data.local.entity.AttendanceEntity
import com.uzerp.mobile.data.local.entity.AuditLogEntity
import com.uzerp.mobile.data.local.entity.CategoryEntity
import com.uzerp.mobile.data.local.entity.CrmActivityEntity
import com.uzerp.mobile.data.local.entity.CustomerEntity
import com.uzerp.mobile.data.local.entity.DepartmentEntity
import com.uzerp.mobile.data.local.entity.EmployeeEntity
import com.uzerp.mobile.data.local.entity.InventoryCountEntity
import com.uzerp.mobile.data.local.entity.InventoryCountItemEntity
import com.uzerp.mobile.data.local.entity.JournalEntryEntity
import com.uzerp.mobile.data.local.entity.JournalLineEntity
import com.uzerp.mobile.data.local.entity.LeadEntity
import com.uzerp.mobile.data.local.entity.LeaveEntity
import com.uzerp.mobile.data.local.entity.PayrollItemEntity
import com.uzerp.mobile.data.local.entity.PayrollRunEntity
import com.uzerp.mobile.data.local.entity.PaymentEntity
import com.uzerp.mobile.data.local.entity.ProductEntity
import com.uzerp.mobile.data.local.entity.PurchaseEntity
import com.uzerp.mobile.data.local.entity.PurchaseItemEntity
import com.uzerp.mobile.data.local.entity.SalesDocEntity
import com.uzerp.mobile.data.local.entity.SalesItemEntity
import com.uzerp.mobile.data.local.entity.SequenceEntity
import com.uzerp.mobile.data.local.entity.SettingEntity
import com.uzerp.mobile.data.local.entity.StockEntity
import com.uzerp.mobile.data.local.entity.StockMoveEntity
import com.uzerp.mobile.data.local.entity.SupplierEntity
import com.uzerp.mobile.data.local.entity.UserEntity
import com.uzerp.mobile.data.local.entity.WarehouseEntity

/**
 * UzERP mahalliy ma'lumotlar bazasi (Room, SQLite).
 *
 * TO'LIQ AVTONOM: bu ilova hech qanday tarmoq so'rovi yubormaydi — barcha
 * ma'lumotlar shu qurilmadagi SQLite faylida saqlanadi (Python backend
 * bilan bir xil 30 jadval strukturasi).
 */
@Database(
    entities = [
        UserEntity::class, AuditLogEntity::class, SettingEntity::class, SequenceEntity::class,
        CategoryEntity::class, ProductEntity::class, WarehouseEntity::class, StockEntity::class,
        StockMoveEntity::class,
        CustomerEntity::class, SupplierEntity::class, LeadEntity::class,
        SalesDocEntity::class, SalesItemEntity::class, PurchaseEntity::class,
        PurchaseItemEntity::class,
        AccountEntity::class, JournalEntryEntity::class, JournalLineEntity::class,
        PaymentEntity::class, AssetEntity::class,
        DepartmentEntity::class, EmployeeEntity::class, AttendanceEntity::class,
        LeaveEntity::class, PayrollRunEntity::class, PayrollItemEntity::class,
        CrmActivityEntity::class, InventoryCountEntity::class, InventoryCountItemEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    abstract fun auditDao(): AuditDao
    abstract fun settingsDao(): SettingsDao
    abstract fun sequenceDao(): SequenceDao

    abstract fun categoryDao(): CategoryDao
    abstract fun productDao(): ProductDao
    abstract fun warehouseDao(): WarehouseDao
    abstract fun stockDao(): StockDao
    abstract fun stockMoveDao(): StockMoveDao

    abstract fun customerDao(): CustomerDao
    abstract fun supplierDao(): SupplierDao
    abstract fun leadDao(): LeadDao

    abstract fun salesDocDao(): SalesDocDao
    abstract fun salesItemDao(): SalesItemDao
    abstract fun purchaseDao(): PurchaseDao
    abstract fun purchaseItemDao(): PurchaseItemDao

    abstract fun accountDao(): AccountDao
    abstract fun journalDao(): JournalDao
    abstract fun paymentDao(): PaymentDao
    abstract fun assetDao(): AssetDao

    abstract fun departmentDao(): DepartmentDao
    abstract fun employeeDao(): EmployeeDao
    abstract fun attendanceDao(): AttendanceDao
    abstract fun leaveDao(): LeaveDao
    abstract fun payrollDao(): PayrollDao

    abstract fun crmActivityDao(): CrmActivityDao
    abstract fun inventoryCountDao(): InventoryCountDao

    companion object {
        const val DB_NAME = "uzerp.db"
    }
}
