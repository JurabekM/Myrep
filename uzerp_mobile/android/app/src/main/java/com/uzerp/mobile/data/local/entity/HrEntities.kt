package com.uzerp.mobile.data.local.entity

import androidx.room.Entity
import androidx.room.Index
import androidx.room.PrimaryKey
import java.math.BigDecimal

@Entity(tableName = "departments")
data class DepartmentEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val name: String,
    val parentId: Long? = null,
    val isActive: Boolean = true,
)

@Entity(tableName = "employees", indices = [Index(value = ["fullName"])])
data class EmployeeEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val code: String = "",
    val fullName: String,
    val departmentId: Long? = null,
    val position: String = "",
    val phone: String = "",
    val email: String = "",
    val hireDate: String = "",
    val birthDate: String? = null,
    val salary: BigDecimal = BigDecimal.ZERO,
    val status: String = "active", // active|leave|terminated
    val tin: String = "",
    val address: String = "",
    val userId: Long? = null,
    val createdAt: String = "",
    val updatedAt: String = "",
)

@Entity(
    tableName = "attendance",
    indices = [Index(value = ["employeeId", "workDate"], unique = true)],
)
data class AttendanceEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val employeeId: Long,
    val workDate: String,
    val checkIn: String = "",
    val checkOut: String = "",
    val hours: BigDecimal = BigDecimal.ZERO,
    val status: String = "present", // present|absent|late|leave|holiday
    val note: String = "",
)

@Entity(tableName = "leaves")
data class LeaveEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val employeeId: Long,
    val leaveType: String = "annual",
    val dateFrom: String,
    val dateTo: String,
    val days: Int = 1,
    val status: String = "pending", // pending|approved|rejected
    val approvedBy: Long? = null,
    val note: String = "",
    val createdAt: String = "",
)

@Entity(tableName = "payroll_runs", indices = [Index(value = ["period"], unique = true)])
data class PayrollRunEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val period: String, // YYYY-MM
    val status: String = "draft", // draft|approved|paid
    val totalGross: BigDecimal = BigDecimal.ZERO,
    val totalTax: BigDecimal = BigDecimal.ZERO,
    val totalNet: BigDecimal = BigDecimal.ZERO,
    val createdBy: Long? = null,
    val createdAt: String = "",
)

@Entity(tableName = "payroll_items", indices = [Index(value = ["runId"])])
data class PayrollItemEntity(
    @PrimaryKey(autoGenerate = true) val id: Long = 0,
    val runId: Long,
    val employeeId: Long,
    val gross: BigDecimal = BigDecimal.ZERO,
    val incomeTax: BigDecimal = BigDecimal.ZERO,
    val pension: BigDecimal = BigDecimal.ZERO,
    val otherDeductions: BigDecimal = BigDecimal.ZERO,
    val net: BigDecimal = BigDecimal.ZERO,
    val note: String = "",
)
