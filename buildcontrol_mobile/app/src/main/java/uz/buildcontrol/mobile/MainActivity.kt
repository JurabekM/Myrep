package uz.buildcontrol.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import uz.buildcontrol.mobile.ui.AppRoot
import uz.buildcontrol.mobile.ui.theme.BcColors
import uz.buildcontrol.mobile.ui.theme.BuildControlTheme

class MainActivity : ComponentActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        enableEdgeToEdge()
        super.onCreate(savedInstanceState)
        setContent {
            BuildControlTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = BcColors.Background,
                ) { AppRoot() }
            }
        }
    }

    override fun onResume() {
        super.onResume()
        // Pick up whatever the team changed while the app was in the background.
        BuildControlApp.container.sync.syncIfAuto()
    }
}
