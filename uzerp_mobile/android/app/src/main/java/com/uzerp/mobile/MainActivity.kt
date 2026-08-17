package com.uzerp.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import com.uzerp.mobile.ui.auth.AuthViewModel
import com.uzerp.mobile.ui.auth.LoginScreen
import com.uzerp.mobile.ui.nav.UzErpNavHost
import com.uzerp.mobile.ui.theme.UzErpTheme
import dagger.hilt.android.AndroidEntryPoint

/**
 * Yagona activity — butun ilova Jetpack Compose ichida ishlaydi.
 *
 * Tarmoq ruxsati (INTERNET) manifestda yo'q — ilova to'liq avtonom,
 * barcha ma'lumotlar shu qurilmadagi Room/SQLite bazasida saqlanadi.
 */
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            UzErpTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    UzErpApp()
                }
            }
        }
    }
}

@androidx.compose.runtime.Composable
private fun UzErpApp(authViewModel: AuthViewModel = hiltViewModel()) {
    val currentUser by authViewModel.currentUser.collectAsState()
    if (currentUser == null) {
        LoginScreen(authViewModel)
    } else {
        UzErpNavHost(authViewModel)
    }
}
