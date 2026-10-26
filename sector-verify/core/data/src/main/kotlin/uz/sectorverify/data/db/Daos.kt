package uz.sectorverify.data.db

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import androidx.room.Transaction
import kotlinx.coroutines.flow.Flow
import uz.sectorverify.model.SessionStatus
import uz.sectorverify.model.Verdict

data class SiteSummaryRow(
    val id: Long,
    val code: String,
    val name: String,
    val lat: Double,
    val lon: Double,
    val sectors: Int,
    val lastVerdict: Verdict?,
    val lastSessionAt: Long?,
)

@Dao
interface SiteDao {
    @Insert
    suspend fun insertSite(site: SiteEntity): Long

    @Insert
    suspend fun insertSectors(sectors: List<SectorEntity>)

    @Query("DELETE FROM sector WHERE site_id = :siteId")
    suspend fun deleteSectors(siteId: Long)

    @Query("UPDATE site SET name = :name, lat = :lat, lon = :lon, mcc_mnc = :mccMnc, imported_at = :importedAt WHERE id = :id")
    suspend fun updateSite(id: Long, name: String, lat: Double, lon: Double, mccMnc: String, importedAt: Long)

    @Query("SELECT * FROM site WHERE code = :code")
    suspend fun byCode(code: String): SiteEntity?

    @Query("SELECT * FROM site WHERE id = :id")
    suspend fun byId(id: Long): SiteEntity?

    @Query("SELECT * FROM sector WHERE site_id = :siteId ORDER BY rat, arfcn, label")
    suspend fun sectors(siteId: Long): List<SectorEntity>

    @Query(
        """
        SELECT s.id, s.code, s.name, s.lat, s.lon,
            (SELECT COUNT(*) FROM sector WHERE site_id = s.id) AS sectors,
            (SELECT verdict FROM session WHERE site_id = s.id AND status = 'DONE' ORDER BY started_at DESC LIMIT 1) AS lastVerdict,
            (SELECT MAX(started_at) FROM session WHERE site_id = s.id) AS lastSessionAt
        FROM site s
        WHERE s.code LIKE '%' || :query || '%' OR s.name LIKE '%' || :query || '%'
        ORDER BY s.code
        """,
    )
    fun observeSummaries(query: String): Flow<List<SiteSummaryRow>>

    /** Re-import replaces the sectors of an existing site (results keep their rows via sector_id SET NULL). */
    @Transaction
    suspend fun upsertWithSectors(site: SiteEntity, sectors: List<SectorEntity>): Long {
        val existing = byCode(site.code)
        val id = if (existing == null) {
            insertSite(site)
        } else {
            updateSite(existing.id, site.name, site.lat, site.lon, site.mccMnc, site.importedAt)
            deleteSectors(existing.id)
            existing.id
        }
        insertSectors(sectors.map { it.copy(id = 0, siteId = id) })
        return id
    }
}

@Dao
interface SessionDao {
    @Insert
    suspend fun insert(session: SessionEntity)

    @Query("SELECT * FROM session WHERE id = :id")
    suspend fun byId(id: String): SessionEntity?

    @Query("SELECT * FROM session WHERE id = :id")
    fun observe(id: String): Flow<SessionEntity?>

    @Query("SELECT * FROM session WHERE status = 'RUNNING' ORDER BY started_at DESC")
    suspend fun running(): List<SessionEntity>

    @Query("SELECT * FROM session WHERE site_id = :siteId ORDER BY started_at DESC")
    fun observeForSite(siteId: Long): Flow<List<SessionEntity>>

    @Query("UPDATE session SET status = :status, ended_at = :endedAt WHERE id = :id")
    suspend fun setStatus(id: String, status: SessionStatus, endedAt: Long?)

    @Query("UPDATE session SET measured_rate_hz = :rate WHERE id = :id")
    suspend fun setRate(id: String, rate: Double)

    @Query("UPDATE session SET verdict = :verdict, coverage_pct = :coveragePct, config_json = :configJson WHERE id = :id")
    suspend fun setResult(id: String, verdict: Verdict, coveragePct: Double, configJson: String)
}

/** Raw data: insert and read only (§5.2 — raw tables are never modified). */
@Dao
interface RawDao {
    @Insert
    suspend fun insertSamples(samples: List<CellSampleEntity>)

    @Insert
    suspend fun insertFixes(fixes: List<GnssFixEntity>)

    /** One Room transaction per 1-second buffer (§7). */
    @Transaction
    suspend fun insertBatch(samples: List<CellSampleEntity>, fixes: List<GnssFixEntity>) {
        if (samples.isNotEmpty()) insertSamples(samples)
        if (fixes.isNotEmpty()) insertFixes(fixes)
    }

    @Query("SELECT * FROM cell_sample WHERE session_id = :sessionId ORDER BY t_nanos, id")
    suspend fun samples(sessionId: String): List<CellSampleEntity>

    @Query("SELECT * FROM gnss_fix WHERE session_id = :sessionId ORDER BY t_nanos, id")
    suspend fun fixes(sessionId: String): List<GnssFixEntity>

    @Query("SELECT COUNT(*) FROM cell_sample WHERE session_id = :sessionId")
    suspend fun sampleCount(sessionId: String): Int

    @Query("SELECT MAX(t_nanos) FROM cell_sample WHERE session_id = :sessionId")
    suspend fun lastSampleNanos(sessionId: String): Long?
}

@Dao
interface ResultDao {
    @Query("DELETE FROM sector_result WHERE session_id = :sessionId")
    suspend fun deleteResults(sessionId: String)

    @Query("DELETE FROM finding WHERE session_id = :sessionId")
    suspend fun deleteFindings(sessionId: String)

    @Insert
    suspend fun insertResults(results: List<SectorResultEntity>)

    @Insert
    suspend fun insertFindings(findings: List<FindingEntity>)

    /** Results are derived data: re-analysis replaces them as a whole. */
    @Transaction
    suspend fun replace(sessionId: String, results: List<SectorResultEntity>, findings: List<FindingEntity>) {
        deleteResults(sessionId)
        deleteFindings(sessionId)
        insertResults(results)
        insertFindings(findings)
    }

    @Query("SELECT * FROM sector_result WHERE session_id = :sessionId ORDER BY rat, arfcn, pci")
    suspend fun results(sessionId: String): List<SectorResultEntity>

    @Query("SELECT * FROM finding WHERE session_id = :sessionId ORDER BY id")
    suspend fun findings(sessionId: String): List<FindingEntity>
}

@Dao
interface ReportDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(report: ReportEntity): Long

    @Query("SELECT * FROM report WHERE session_id = :sessionId ORDER BY created_at DESC LIMIT 1")
    suspend fun latest(sessionId: String): ReportEntity?
}
