package uz.sectorverify.data.repo

import javax.inject.Inject
import uz.sectorverify.data.db.ReportDao
import uz.sectorverify.data.db.ReportEntity

interface ReportRepository {
    suspend fun save(report: ReportEntity): Long

    suspend fun latest(sessionId: String): ReportEntity?
}

class RoomReportRepository @Inject constructor(private val dao: ReportDao) : ReportRepository {
    override suspend fun save(report: ReportEntity): Long = dao.insert(report)

    override suspend fun latest(sessionId: String): ReportEntity? = dao.latest(sessionId)
}
