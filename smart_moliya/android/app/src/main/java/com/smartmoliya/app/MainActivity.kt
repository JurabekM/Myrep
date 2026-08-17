package com.smartmoliya.app

import android.os.Bundle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.fragment.app.FragmentActivity
import androidx.hilt.navigation.compose.hiltViewModel
import com.smartmoliya.app.app.AppRootViewModel
import com.smartmoliya.app.app.SmartMoliyaNavHost
import com.smartmoliya.app.ui.theme.SmartMoliyaTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * FragmentActivity'dan meros olinadi (ComponentActivity emas) - androidx.biometric.BiometricPrompt
 * FragmentActivity/Fragment talab qiladi (PIN/Face/Fingerprint autentifikatsiyasi uchun).
 */
@AndroidEntryPoint
class MainActivity : FragmentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            val rootViewModel: AppRootViewModel = hiltViewModel()
            val themeId by rootViewModel.theme.collectAsState()

            SmartMoliyaTheme(appThemeId = themeId) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    SmartMoliyaNavHost(activity = this)
                }
            }
        }
    }
}
