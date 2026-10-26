package uz.sectorverify.data.di

import android.content.Context
import androidx.datastore.core.DataStore
import androidx.datastore.preferences.core.PreferenceDataStoreFactory
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.preferencesDataStoreFile
import androidx.room.Room
import dagger.Binds
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import java.io.File
import javax.inject.Singleton
import net.zetetic.database.sqlcipher.SupportOpenHelperFactory
import uz.sectorverify.data.db.SectorVerifyDatabase
import uz.sectorverify.data.repo.Clock
import uz.sectorverify.data.repo.PlanRepository
import uz.sectorverify.data.repo.RoomPlanRepository
import uz.sectorverify.data.repo.RoomSessionRepository
import uz.sectorverify.data.repo.SessionRepository
import uz.sectorverify.data.security.DatabaseKeyStore
import uz.sectorverify.data.security.KeystoreKeyWrapper
import uz.sectorverify.data.settings.DataStoreSettingsRepository
import uz.sectorverify.data.settings.SettingsRepository

object DatabaseFactory {
    /** SQLCipher-encrypted Room database; the passphrase comes from [DatabaseKeyStore]. */
    fun encrypted(context: Context): SectorVerifyDatabase {
        System.loadLibrary("sqlcipher")
        val keyFile = File(context.noBackupFilesDir, DatabaseKeyStore.FILE_NAME)
        val passphrase = DatabaseKeyStore(keyFile, KeystoreKeyWrapper()).passphrase()
        return Room.databaseBuilder(context, SectorVerifyDatabase::class.java, SectorVerifyDatabase.NAME)
            .openHelperFactory(SupportOpenHelperFactory(passphrase))
            .build()
    }
}

@Module
@InstallIn(SingletonComponent::class)
object DataProvidesModule {
    @Provides
    @Singleton
    fun database(@ApplicationContext context: Context): SectorVerifyDatabase = DatabaseFactory.encrypted(context)

    @Provides fun siteDao(db: SectorVerifyDatabase) = db.siteDao()

    @Provides fun sessionDao(db: SectorVerifyDatabase) = db.sessionDao()

    @Provides fun rawDao(db: SectorVerifyDatabase) = db.rawDao()

    @Provides fun resultDao(db: SectorVerifyDatabase) = db.resultDao()

    @Provides fun reportDao(db: SectorVerifyDatabase) = db.reportDao()

    @Provides
    @Singleton
    fun dataStore(@ApplicationContext context: Context): DataStore<Preferences> =
        PreferenceDataStoreFactory.create { context.preferencesDataStoreFile("settings") }

    @Provides fun clock(): Clock = Clock.SYSTEM
}

@Module
@InstallIn(SingletonComponent::class)
abstract class DataBindsModule {
    @Binds abstract fun plan(impl: RoomPlanRepository): PlanRepository

    @Binds abstract fun session(impl: RoomSessionRepository): SessionRepository

    @Binds abstract fun settings(impl: DataStoreSettingsRepository): SettingsRepository
}
