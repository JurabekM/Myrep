package com.aetherq.messenger

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import com.aetherq.messenger.ui.nav.AppNav
import com.aetherq.messenger.ui.theme.AetherMessengerTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as MessengerApp).container
        setContent {
            AetherMessengerTheme {
                AppNav(container)
            }
        }
    }
}
