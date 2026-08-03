package uz.dehqonkomakchi.app.di

import dagger.Binds
import dagger.Module
import dagger.hilt.InstallIn
import dagger.hilt.components.SingletonComponent
import uz.dehqonkomakchi.app.data.remote.auth.AuthOtpProvider
import uz.dehqonkomakchi.app.data.remote.auth.DemoAuthOtpProvider
import uz.dehqonkomakchi.app.data.remote.diagnosis.CropDiagnosisProvider
import uz.dehqonkomakchi.app.data.remote.diagnosis.MockCropDiagnosisProvider
import uz.dehqonkomakchi.app.data.remote.weather.MockWeatherProvider
import uz.dehqonkomakchi.app.data.remote.weather.WeatherProvider
import javax.inject.Singleton

/**
 * Binds every third-party-service interface to its zero-API-key mock implementation. To wire in
 * a real provider (a real ML model server, a weather API, a real SMS gateway) later, replace the
 * `@Binds` target class here only — no other file needs to change.
 */
@Module
@InstallIn(SingletonComponent::class)
abstract class ProviderModule {

    @Binds
    @Singleton
    abstract fun bindCropDiagnosisProvider(impl: MockCropDiagnosisProvider): CropDiagnosisProvider

    @Binds
    @Singleton
    abstract fun bindWeatherProvider(impl: MockWeatherProvider): WeatherProvider

    @Binds
    @Singleton
    abstract fun bindAuthOtpProvider(impl: DemoAuthOtpProvider): AuthOtpProvider
}
