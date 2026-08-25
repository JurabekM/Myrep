package uz.distribos.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.lifecycle.ViewModelProvider
import uz.distribos.app.ui.DistribosApp
import uz.distribos.app.ui.DistribosTheme

/**
 * Yagona Activity — qolgani Compose.
 *
 * Ilova ishga tushishi UCHUN internet SHART EMAS: baza lokal, hodisalar
 * lokal yaratiladi, sinxronizatsiya esa fon vazifasi.
 */
class MainActivity : ComponentActivity() {

    private lateinit var viewModel: MainViewModel

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()

        viewModel = ViewModelProvider(
            this, MainViewModel.Factory(applicationContext)
        )[MainViewModel::class.java]

        setContent {
            DistribosTheme {
                val state by viewModel.state.collectAsState()
                DistribosApp(
                    role = state.role,
                    orders = state.orders,
                    customers = state.customers,
                    stock = state.stock,
                    payments = state.payments,
                    syncState = state.sync,
                    provisioned = state.provisioned,
                    joinState = state.join,
                    onQrScanned = viewModel::onQrScanned,
                    onManualCode = viewModel::onManualCode,
                    onStartScan = viewModel::startScan,
                    onCancelJoin = viewModel::cancelJoin,
                )
            }
        }
    }

    override fun onStart() {
        super.onStart()
        viewModel.startSync()
    }

    override fun onStop() {
        // Fon sinxronizatsiyasi WorkManager'da davom etadi; jonli
        // aylanishni to'xtatamiz — batareya bekorga sarflanmasin.
        viewModel.stopSync()
        super.onStop()
    }
}
