package uz.sectorverify.data.repo

import javax.inject.Inject
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import uz.sectorverify.data.db.SectorEntity
import uz.sectorverify.data.db.SiteDao
import uz.sectorverify.data.toEntity
import uz.sectorverify.data.toModel
import uz.sectorverify.format.PlanCsv
import uz.sectorverify.format.PlanImport
import uz.sectorverify.model.SitePlan
import uz.sectorverify.model.Verdict

data class SiteSummary(
    val id: Long,
    val code: String,
    val name: String,
    val sectors: Int,
    val lastVerdict: Verdict?,
    val lastSessionAt: Long?,
)

data class StoredSite(val id: Long, val plan: SitePlan, val sectorIds: Map<SectorEntity, Long>) {
    fun sectorId(rat: uz.sectorverify.model.Rat, arfcn: Int, pci: Int): Long? =
        sectorIds.entries.firstOrNull { it.key.rat == rat && it.key.arfcn == arfcn && it.key.pci == pci }?.value
}

interface PlanRepository {
    /** Parse qiladi va tekshiradi; barcha saytlarni faqat butun fayl to'g'ri bo'lsagina saqlaydi. */
    suspend fun importCsv(text: String): PlanImport

    fun observeSites(query: String = ""): Flow<List<SiteSummary>>

    suspend fun site(id: Long): StoredSite?

    suspend fun siteByCode(code: String): StoredSite?
}

class RoomPlanRepository @Inject constructor(private val dao: SiteDao, private val clock: Clock) : PlanRepository {
    override suspend fun importCsv(text: String): PlanImport {
        val parsed = PlanCsv.parse(text)
        if (parsed.ok) {
            val now = clock.nowUtcMs()
            for (site in parsed.sites) dao.upsertWithSectors(site.toEntity(now), site.sectors.map { it.toEntity(0) })
        }
        return parsed
    }

    override fun observeSites(query: String): Flow<List<SiteSummary>> = dao.observeSummaries(query.trim()).map { rows ->
        rows.map { SiteSummary(it.id, it.code, it.name, it.sectors, it.lastVerdict, it.lastSessionAt) }
    }

    override suspend fun site(id: Long): StoredSite? = dao.byId(id)?.let { load(it.id) }

    override suspend fun siteByCode(code: String): StoredSite? = dao.byCode(code)?.let { load(it.id) }

    private suspend fun load(id: Long): StoredSite? {
        val site = dao.byId(id) ?: return null
        val sectors = dao.sectors(id)
        return StoredSite(id, site.toModel(sectors), sectors.associateWith { it.id })
    }
}

fun interface Clock {
    fun nowUtcMs(): Long

    companion object {
        val SYSTEM = Clock { System.currentTimeMillis() }
    }
}
