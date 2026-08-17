package com.uzerp.mobile.data.repository

import androidx.room.withTransaction
import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.StateException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.core.d
import com.uzerp.mobile.data.local.AppDatabase
import com.uzerp.mobile.data.local.dao.EmployeeDao
import com.uzerp.mobile.data.local.dao.PayrollDao
import com.uzerp.mobile.data.local.dao.PayrollItemWithEmployee
import com.uzerp.mobile.data.local.entity.PayrollItemEntity
import com.uzerp.mobile.data.local.entity.PayrollRunEntity
import java.math.BigDecimal
import java.math.RoundingMode
import javax.inject.Inject
import javax.inject.Singleton

/** O'zbekiston: daromad solig'i 12%, INPS (pensiya) badali 0.1% — Python `config.yaml` standarti bilan bir xil. */
private val INCOME_TAX_RATE = BigDecimal("12")
private val PENSION_RATE = BigDecimal("0.1")

data class PayrollRunDetail(val run: PayrollRunEntity, val items: List<PayrollItemWithEmployee>)

/**
 * Ish haqi servisi — Python `PayrollService` bilan bir xil: draft ->
 * approved (Dt 9410 / Kt 6710+6410) -> paid (kassa/bank orqali).
 */
@Singleton
class PayrollRepository @Inject constructor(
    private val db: AppDatabase,
    private val payrollDao: PayrollDao,
    private val employeeDao: EmployeeDao,
    private val accountingRepository: AccountingRepository,
    private val paymentRepository: PaymentRepository,
) {
    suspend fun createRun(period: String, userId: Long?): Long {
        if (period.length != 7 || period[4] != '-') throw ValidationException("Davr formati YYYY-MM bo'lishi kerak.")
        if (payrollDao.getRunByPeriod(period) != null) throw StateException("$period davri uchun vedomost allaqachon mavjud.")
        val employees = employeeDao.activeWithSalary()
        if (employees.isEmpty()) throw ValidationException("Maoshi belgilangan faol xodimlar topilmadi.")

        var totalGross = BigDecimal.ZERO
        var totalTax = BigDecimal.ZERO
        var totalNet = BigDecimal.ZERO
        var runId = 0L
        db.withTransaction {
            runId = payrollDao.insertRun(
                PayrollRunEntity(period = period, status = "draft", createdBy = userId, createdAt = DateUtils.nowStr()),
            )
            for (employee in employees) {
                val gross = d(employee.salary)
                val incomeTax = d(gross.multiply(INCOME_TAX_RATE).divide(BigDecimal(100), 10, RoundingMode.HALF_UP))
                val pension = d(gross.multiply(PENSION_RATE).divide(BigDecimal(100), 10, RoundingMode.HALF_UP))
                val net = d(gross.subtract(incomeTax).subtract(pension))
                payrollDao.insertItem(
                    PayrollItemEntity(runId = runId, employeeId = employee.id, gross = gross, incomeTax = incomeTax, pension = pension, net = net),
                )
                totalGross = d(totalGross.add(gross))
                totalTax = d(totalTax.add(incomeTax).add(pension))
                totalNet = d(totalNet.add(net))
            }
            payrollDao.setTotals(runId, totalGross, totalTax, totalNet)
        }
        return runId
    }

    suspend fun getRun(runId: Long): PayrollRunDetail {
        val run = payrollDao.getRunById(runId) ?: throw NotFoundException("Vedomost topilmadi (id=$runId).")
        return PayrollRunDetail(run, payrollDao.itemsForRun(runId))
    }

    suspend fun listRuns(page: Int = 1): PageResult<PayrollRunEntity> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(payrollDao.page(PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun approve(runId: Long, userId: Long?) {
        val detail = getRun(runId)
        val run = detail.run
        if (run.status != "draft") throw StateException("Faqat qoralama vedomostni tasdiqlash mumkin.")
        val gross = d(run.totalGross)
        val tax = d(run.totalTax)
        val otherDeductions = d(detail.items.fold(BigDecimal.ZERO) { acc, item -> acc.add(item.otherDeductions) })
        val net = d(run.totalNet)

        accountingRepository.createEntry(
            "Ish haqi ${run.period}",
            listOf(
                JournalLineInput("9410", debit = gross),
                JournalLineInput("6710", credit = d(net.add(otherDeductions))),
                JournalLineInput("6410", credit = tax),
            ),
            "${run.period}-28", "payroll", runId, userId,
        )
        payrollDao.setStatus(runId, "approved")
    }

    suspend fun pay(runId: Long, method: String, userId: Long?): Long {
        val detail = getRun(runId)
        val run = detail.run
        if (run.status != "approved") throw StateException("Faqat tasdiqlangan vedomostni to'lash mumkin.")
        val paymentId = paymentRepository.createPayment(
            "out", d(run.totalNet), method, "6710", refType = "payroll", refId = runId,
            note = "Ish haqi ${run.period}", userId = userId,
        )
        payrollDao.setStatus(runId, "paid")
        return paymentId
    }
}
