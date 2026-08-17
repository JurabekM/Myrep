package com.uzerp.mobile.data.repository

import com.uzerp.mobile.core.DateUtils
import com.uzerp.mobile.core.NotFoundException
import com.uzerp.mobile.core.StateException
import com.uzerp.mobile.core.ValidationException
import com.uzerp.mobile.data.local.dao.CrmActivityDao
import com.uzerp.mobile.data.local.dao.LeadDao
import com.uzerp.mobile.data.local.entity.CrmActivityEntity
import com.uzerp.mobile.data.local.entity.LeadEntity
import javax.inject.Inject
import javax.inject.Singleton

val LEAD_STATUSES = setOf("new", "contacted", "qualified", "won", "lost")
val ACTIVITY_TYPES = setOf("call", "email", "meeting", "reminder", "note", "task")

/** CRM servisi — Python `CrmService` bilan bir xil: lead voronkasi, faoliyatlar, eslatmalar. */
@Singleton
class CrmRepository @Inject constructor(
    private val leadDao: LeadDao,
    private val activityDao: CrmActivityDao,
    private val customerRepository: CustomerRepository,
) {
    suspend fun listLeads(page: Int = 1, status: String? = null): PageResult<LeadEntity> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(leadDao.search(status, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    suspend fun getLead(id: Long): LeadEntity = leadDao.getById(id) ?: throw NotFoundException("Lead topilmadi (id=$id).")

    suspend fun createLead(name: String, phone: String = "", email: String = "", source: String = ""): Long {
        val trimmed = name.trim()
        if (trimmed.isBlank()) throw ValidationException("Lead nomi bo'sh bo'lishi mumkin emas.")
        val now = DateUtils.nowStr()
        return leadDao.insert(LeadEntity(name = trimmed, phone = phone, email = email, source = source, status = "new", createdAt = now, updatedAt = now))
    }

    /** Lead holatini o'zgartiradi; `won` bo'lsa avtomatik mijoz yaratadi va uning id'sini qaytaradi. */
    suspend fun changeLeadStatus(leadId: Long, status: String): Long? {
        if (status !in LEAD_STATUSES) throw ValidationException("Noma'lum lead holati: $status")
        val lead = getLead(leadId)
        if (lead.status in setOf("won", "lost") && status !in setOf("won", "lost")) {
            throw StateException("Yakunlangan leadni orqaga qaytarib bo'lmaydi.")
        }
        var customerId = lead.customerId
        if (status == "won" && customerId == null) {
            customerId = customerRepository.create(name = lead.name, phone = lead.phone, email = lead.email)
        }
        leadDao.update(lead.copy(status = status, customerId = customerId, updatedAt = DateUtils.nowStr()))
        return customerId
    }

    suspend fun addActivity(
        subject: String,
        activityType: String = "note",
        customerId: Long? = null,
        leadId: Long? = null,
        details: String = "",
        dueAt: String? = null,
        userId: Long? = null,
    ): Long {
        val trimmed = subject.trim()
        if (trimmed.isBlank()) throw ValidationException("Faoliyat mavzusi bo'sh bo'lishi mumkin emas.")
        if (activityType !in ACTIVITY_TYPES) throw ValidationException("Noma'lum faoliyat turi: $activityType")
        return activityDao.insert(
            CrmActivityEntity(
                activityType = activityType, customerId = customerId, leadId = leadId, subject = trimmed,
                details = details, dueAt = dueAt, status = "open", assignedTo = userId, createdBy = userId,
                createdAt = DateUtils.nowStr(),
            ),
        )
    }

    suspend fun completeActivity(id: Long) {
        val activity = activityDao.getById(id) ?: throw NotFoundException("Faoliyat topilmadi (id=$id).")
        if (activity.status != "open") throw StateException("Faoliyat allaqachon yakunlangan.")
        activityDao.markDone(id, DateUtils.nowStr())
    }

    suspend fun listActivities(page: Int = 1, status: String? = null): PageResult<CrmActivityEntity> {
        val offset = (page - 1) * PAGE_SIZE
        return PageResult(activityDao.search(status, PAGE_SIZE, offset), page, PAGE_SIZE, Int.MAX_VALUE)
    }

    fun dueReminders(limit: Int = 20) = activityDao.observeDueReminders(DateUtils.nowStr(), limit)
}
