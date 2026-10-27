package uz.sectorverify.feature.survey

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent

@Module
@InstallIn(SingletonComponent::class)
abstract class SurveyModule {
    @Binds abstract fun launcher(impl: SurveyStarter): SurveyLauncher

    @Binds abstract fun preCheckSource(impl: AndroidPreCheckSource): PreCheckSource
}
