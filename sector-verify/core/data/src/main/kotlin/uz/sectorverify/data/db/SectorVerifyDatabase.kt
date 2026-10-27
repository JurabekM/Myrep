package uz.sectorverify.data.db

import androidx.room.Database
import androidx.room.RoomDatabase

@Database(
    entities = [
        SiteEntity::class,
        SectorEntity::class,
        SessionEntity::class,
        GnssFixEntity::class,
        CellSampleEntity::class,
        SectorResultEntity::class,
        FindingEntity::class,
        ReportEntity::class,
    ],
    version = 1,
    exportSchema = true,
)
abstract class SectorVerifyDatabase : RoomDatabase() {
    abstract fun siteDao(): SiteDao

    abstract fun sessionDao(): SessionDao

    abstract fun rawDao(): RawDao

    abstract fun resultDao(): ResultDao

    abstract fun reportDao(): ReportDao

    companion object {
        const val NAME = "sector-verify.db"
    }
}
