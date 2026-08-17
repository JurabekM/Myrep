package com.uzerp.mobile

import android.app.Application
import com.uzerp.mobile.data.repository.AccountingRepository
import dagger.hilt.android.HiltAndroidApp
import javax.inject.Inject
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * Ilova kirish nuqtasi (Hilt DI grafigini ishga tushiradi).
 *
 * [AccountingRepository.startListening] shu yerda darhol chaqiriladi —
 * Python `bootstrap.py`dagi "accounting servisini majburan yaratish"
 * tamoyili bilan bir xil: savdo/xarid tasdiqlanishi HAR DOIM avto
 * buxgalteriya o'tkazmasi bilan kuzatilishi kerak, foydalanuvchi
 * Buxgalteriya ekranini ochish-ochmasligidan qat'iy nazar.
 */
@HiltAndroidApp
class UzErpApplication : Application() {
    @Inject lateinit var accountingRepository: AccountingRepository

    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.IO)

    override fun onCreate() {
        super.onCreate()
        accountingRepository.startListening(applicationScope)
    }
}
