package uz.qarzsiz.app

import android.graphics.Color
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import uz.qarzsiz.app.ui.QarzsizApp
import uz.qarzsiz.app.ui.QarzsizTheme

class MainActivity : ComponentActivity() {
    private val vm: AppViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        // Holat yuklanguncha ham ekran himoyalangan (standart — yoqilgan).
        window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
        enableEdgeToEdge(
            statusBarStyle = SystemBarStyle.dark(Color.parseColor("#1F1E1D")),
            navigationBarStyle = SystemBarStyle.dark(Color.parseColor("#1F1E1D")),
        )
        super.onCreate(savedInstanceState)
        setContent {
            val state by vm.state.collectAsStateWithLifecycle()
            LaunchedEffect(state.secureScreen) {
                if (state.secureScreen) {
                    window.setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE)
                } else {
                    window.clearFlags(WindowManager.LayoutParams.FLAG_SECURE)
                }
            }
            QarzsizTheme { QarzsizApp(vm) }
        }
    }
}
