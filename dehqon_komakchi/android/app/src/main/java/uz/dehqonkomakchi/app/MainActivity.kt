package uz.dehqonkomakchi.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import dagger.hilt.android.AndroidEntryPoint
import uz.dehqonkomakchi.app.core.prefs.UserPrefs
import uz.dehqonkomakchi.app.ui.nav.DehqonNavHost
import uz.dehqonkomakchi.app.ui.theme.DehqonTheme
import javax.inject.Inject

@AndroidEntryPoint
class MainActivity : ComponentActivity() {

    @Inject lateinit var userPrefs: UserPrefs

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val settings by userPrefs.settings.collectAsState(initial = null)
            val systemDark = isSystemInDarkTheme()
            val darkTheme = when (settings?.darkModeOverride) {
                "dark" -> true
                "light" -> false
                else -> systemDark
            }
            DehqonTheme(darkTheme = darkTheme) {
                DehqonNavHost(userPrefs = userPrefs)
            }
        }
    }
}
