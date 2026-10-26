package uz.sectorverify.app

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Inject
import uz.sectorverify.feature.plan.SessionResumer
import uz.sectorverify.feature.survey.SurveyLauncher

/** Lets :feature:plan resume a session without depending on :feature:survey. */
class LauncherResumer @Inject constructor(private val launcher: SurveyLauncher) : SessionResumer {
    override fun resume(sessionId: String): Boolean = launcher.resume(sessionId)

    override suspend fun abandon(sessionId: String) = launcher.abandon(sessionId)
}

@Module
@InstallIn(SingletonComponent::class)
abstract class AppModule {
    @Binds abstract fun resumer(impl: LauncherResumer): SessionResumer
}
