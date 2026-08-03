package uz.dehqonkomakchi.app.data.repo

import kotlinx.coroutines.flow.Flow
import uz.dehqonkomakchi.app.data.db.dao.ListingDao
import uz.dehqonkomakchi.app.data.db.dao.SellGroupDao
import uz.dehqonkomakchi.app.data.db.entity.ListingEntity
import uz.dehqonkomakchi.app.data.db.entity.ListingReportEntity
import uz.dehqonkomakchi.app.data.db.entity.SellGroupEntity
import java.util.UUID
import javax.inject.Inject
import javax.inject.Singleton

/** Reports auto-hide a listing once this many independent reports accumulate (simple moderation). */
private const val AUTO_HIDE_REPORT_THRESHOLD = 3

@Singleton
class MarketRepository @Inject constructor(
    private val listingDao: ListingDao,
    private val sellGroupDao: SellGroupDao,
) {
    fun observeActiveListings(): Flow<List<ListingEntity>> = listingDao.observeActive()
    fun observeGroups(): Flow<List<SellGroupEntity>> = sellGroupDao.observeAll()

    suspend fun createListing(
        variety: String,
        quantityKg: Double,
        priceSom: Double?,
        negotiable: Boolean,
        region: String,
        availabilityEpochDay: Long,
        photoPath: String?,
        contactMethod: String,
        contactValue: String,
        contactConsent: Boolean,
        ownerName: String,
        groupId: String?,
    ): String {
        val id = UUID.randomUUID().toString()
        listingDao.insert(
            ListingEntity(
                id = id,
                variety = variety,
                quantityKg = quantityKg,
                priceSom = priceSom,
                negotiable = negotiable,
                region = region,
                availabilityEpochDay = availabilityEpochDay,
                photoPath = photoPath,
                contactMethod = contactMethod,
                contactValue = contactValue,
                contactConsent = contactConsent,
                ownerName = ownerName,
                groupId = groupId,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        return id
    }

    suspend fun deleteListing(entity: ListingEntity) = listingDao.delete(entity)

    suspend fun reportListing(listingId: String, reason: String, note: String) {
        listingDao.insertReport(
            ListingReportEntity(
                id = UUID.randomUUID().toString(),
                listingId = listingId,
                reason = reason,
                note = note,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        val count = listingDao.reportCount(listingId)
        if (count >= AUTO_HIDE_REPORT_THRESHOLD) {
            listingDao.getById(listingId)?.let { listingDao.update(it.copy(reported = true)) }
        }
    }

    suspend fun createGroup(name: String, region: String, adminName: String): String {
        val id = UUID.randomUUID().toString()
        sellGroupDao.insert(
            SellGroupEntity(
                id = id,
                name = name,
                region = region,
                adminName = adminName,
                isAdmin = true,
                createdAtEpochMillis = System.currentTimeMillis(),
            ),
        )
        return id
    }

    suspend fun joinGroup(group: SellGroupEntity) {
        sellGroupDao.insert(group.copy(isAdmin = false))
    }

    /** Sums quantity of active listings tagged to [groupId] — the "aggregated group quantity". */
    suspend fun groupAggregatedQuantityKg(groupId: String, allListings: List<ListingEntity>): Double =
        allListings.filter { it.groupId == groupId }.sumOf { it.quantityKg }
}
