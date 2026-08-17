package com.uzerp.mobile.core

import java.math.BigDecimal
import javax.inject.Inject
import javax.inject.Singleton
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * Ilova ichidagi hodisalar (Python `core/events.py` — Observer pattern
 * bilan bir xil tamoyil): savdo/ombor modullari buxgalteriya modulini
 * bilishi shart emas — buxgalteriya shu hodisalarga obuna bo'lib, avto
 * jurnal o'tkazmalarini yozadi (A3 bosqichida ulanadi).
 */
sealed class AppEvent {
    data class SaleConfirmed(val docId: Long, val docType: String, val userId: Long?) : AppEvent()
    data class PurchaseReceived(val purchaseId: Long, val userId: Long?) : AppEvent()
    data class PaymentCreated(val paymentId: Long, val paymentType: String, val amount: BigDecimal) : AppEvent()
}

@Singleton
class AppEventBus @Inject constructor() {
    private val _events = MutableSharedFlow<AppEvent>(extraBufferCapacity = 16)
    val events: SharedFlow<AppEvent> = _events

    suspend fun emit(event: AppEvent) {
        _events.emit(event)
    }
}
