package uz.sectorverify.app

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import javax.inject.Inject
import uz.sectorverify.feature.plan.SessionResumer
import uz.sectorverify.feature.survey.SurveyController
import uz.sectorverify.feature.survey.SurveyLauncher

/** :feature:plan'ga :feature:survey'ga bog'lanmasdan sessiyani davom ettirish imkonini beradi. */
class LauncherResumer @Inject constructor(private val launcher: SurveyLauncher, private val controller: SurveyController) : SessionResumer {
    override fun resume(sessionId: String): Boolean = launcher.resume(sessionId)

    override fun isRecording(sessionId: String): Boolean = controller.state.value.let { it.running && it.sessionId == sessionId }

    override suspend fun abandon(sessionId: String) = launcher.abandon(sessionId)
}

@Module
@InstallIn(SingletonComponent::class)
abstract class AppModule {
    @Binds abstract fun resumer(impl: LauncherResumer): SessionResumer
}
