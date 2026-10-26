package uz.sectorverify.app

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import dagger.hilt.android.AndroidEntryPoint
import javax.inject.Inject
import uz.sectorverify.data.settings.AppTheme
import uz.sectorverify.data.settings.Settings
import uz.sectorverify.data.settings.SettingsRepository
import uz.sectorverify.feature.settings.LocaleStore
import uz.sectorverify.ui.theme.SectorVerifyTheme
import uz.sectorverify.ui.theme.ThemeMode

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    @Inject lateinit var settings: SettingsRepository

    override fun attachBaseContext(newBase: Context) {
        super.attachBaseContext(LocaleStore.wrap(newBase))
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            val s by settings.settings.collectAsStateWithLifecycle(Settings())
            SectorVerifyTheme(s.theme.toMode()) {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    androidx.compose.foundation.layout.Box(Modifier.safeDrawingPadding()) {
                        AppNavHost(onLanguageChanged = ::recreate)
                    }
                }
            }
        }
    }
}

private fun AppTheme.toMode() = when (this) {
    AppTheme.DARK -> ThemeMode.DARK
    AppTheme.LIGHT -> ThemeMode.LIGHT
    AppTheme.SUN -> ThemeMode.SUN
}
