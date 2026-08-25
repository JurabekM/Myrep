package uz.distribos.app

import android.content.Context
import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.launch
import uz.distribos.app.ui.CustomerRow
import uz.distribos.app.ui.OrderRow
import uz.distribos.app.ui.PaymentRow
import uz.distribos.app.ui.StatusTone
import uz.distribos.app.ui.StockRow
import uz.distribos.app.ui.JoinUiState
import uz.distribos.app.ui.SyncState
import uz.distribos.sync.ProvisioningClient

/**
 * Asosiy ekran holati.
 *
 * Ma'lumot Room'dan `Flow` orqali oqadi: buyurtma yozilishi bilan ro'yxat
 * o'zi yangilanadi, qo'lda "refresh" kerak emas. Sinxronizatsiya kelgan
 * hodisalarni bazaga yozadi va UI shundayoq yangilanadi.
 */
class MainViewModel(private val container: AppContainer) : ViewModel() {

    data class UiState(
        val role: String = "agent",
        val orders: List<OrderRow> = emptyList(),
        val customers: List<CustomerRow> = emptyList(),
        val stock: List<StockRow> = emptyList(),
        val payments: List<PaymentRow> = emptyList(),
        val sync: SyncState = SyncState(
            connected = false, queued = 0, deadLetters = 0, devices = 0,
            publicPilot = true, protocolVersion = "5.1.0", epoch = 0,
        ),
        val provisioned: Boolean = true,
        val join: JoinUiState = JoinUiState.Idle,
    )

    private val _state = MutableStateFlow(UiState(role = container.role))
    val state: StateFlow<UiState> = _state.asStateFlow()

    private var syncJob: Job? = null

    init {
        observeData()
    }

    private fun observeData() {
        val database = container.database

        viewModelScope.launch {
            combine(
                database.orders().observeRecent(),
                database.customers().observeAll(),
            ) { orders, customers ->
                val byId = customers.associateBy { it.id }
                orders.map { order ->
                    OrderRow(
                        number = order.number,
                        customerName = byId[order.customerId]?.name ?: "—",
                        stateLabel = orderStateLabel(order.state),
                        tone = orderStateTone(order.state),
                        total = order.total,
                        syncLabel = "Telefonda saqlandi",
                    )
                }
            }.collect { rows -> _state.value = _state.value.copy(orders = rows) }
        }

        // DIQQAT: qarzdorlik mijozlar jadvalidan EMAS, buyurtma va
        // to'lovlardan hisoblanadi. Shuning uchun uchala oqimni ham
        // kuzatish SHART — faqat `observeAll()` ni kuzatsak, buyurtma
        // qo'shilganda qarz eskirgan holicha (0) qolib ketadi.
        viewModelScope.launch {
            combine(
                database.customers().observeAll(),
                database.orders().observeRecent(),
                database.payments().observeRecent(),
            ) { customers, _, _ -> customers }
                .collect { customers ->
                    val rows = customers.map { customer ->
                        val debt = database.customers().debt(customer.id)
                        CustomerRow(
                            code = customer.code,
                            name = customer.name,
                            phone = customer.phone,
                            debt = debt,
                            overLimit = customer.creditLimit > 0 && debt > customer.creditLimit,
                        )
                    }
                    _state.value = _state.value.copy(customers = rows)
                }
        }

        viewModelScope.launch {
            combine(
                database.inventory().observeStock(),
                database.products().observeAll(),
            ) { stock, products ->
                val byId = products.associateBy { it.id }
                stock.mapNotNull { row ->
                    val product = byId[row.productId] ?: return@mapNotNull null
                    StockRow(
                        sku = product.sku,
                        name = product.name,
                        quantity = row.quantity,
                        minStock = product.minStock,
                        belowMinimum = java.math.BigDecimal(row.quantity) <
                            java.math.BigDecimal(product.minStock),
                    )
                }
            }.collect { rows -> _state.value = _state.value.copy(stock = rows) }
        }

        viewModelScope.launch {
            combine(
                database.payments().observeRecent(),
                database.customers().observeAll(),
            ) { payments, customers ->
                val byId = customers.associateBy { it.id }
                payments.map { payment ->
                    PaymentRow(
                        number = payment.number,
                        customerName = byId[payment.customerId]?.name ?: "—",
                        amount = payment.amount,
                        direction = payment.direction,
                        isReversed = payment.isReversed,
                    )
                }
            }.collect { rows -> _state.value = _state.value.copy(payments = rows) }
        }

        viewModelScope.launch {
            database.sync().observeQueueDepth().collect { queued ->
                _state.value = _state.value.copy(
                    sync = _state.value.sync.copy(queued = queued)
                )
            }
        }

        // Ulanganlik holati: o'zimizdan boshqa faol qurilma bormi.
        viewModelScope.launch {
            container.observeProvisioned().collect { peers ->
                _state.value = _state.value.copy(provisioned = peers > 0)
            }
        }
    }

    // --- qurilmani ulash --------------------------------------------------

    fun startScan() {
        _state.value = _state.value.copy(join = JoinUiState.Scanning)
    }

    fun cancelJoin() {
        container.provisioning.cancel()
        _state.value = _state.value.copy(join = JoinUiState.Idle)
    }

    /** QR kod baytlari (binar CBOR). */
    fun onQrScanned(payload: ByteArray) = join(payload)

    /**
     * Qo'lda kiritilgan kod — QR payload'ining o'n oltilik ko'rinishi.
     *
     * Kamera ishlamasa yoki ruxsat berilmasa zaxira yo'l. Omborda
     * telefon kamerasi ko'pincha ishlamaydi, shuning uchun bu zaxira
     * emas, to'liq huquqli yo'l.
     */
    fun onManualCode(code: String) {
        val cleaned = code.filter { !it.isWhitespace() }
        val bytes = try {
            require(cleaned.length % 2 == 0 && cleaned.all { it.isDigit() || it.lowercaseChar() in 'a'..'f' })
            cleaned.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
        } catch (_: Exception) {
            _state.value = _state.value.copy(
                join = JoinUiState.Failed("Kod noto'g'ri. Kompyuterdagi kodni to'liq nusxalang.")
            )
            return
        }
        join(bytes)
    }

    private fun join(payload: ByteArray) {
        viewModelScope.launch {
            val invitation = try {
                ProvisioningClient.Invitation.fromQrPayload(payload)
            } catch (exception: Exception) {
                _state.value = _state.value.copy(
                    join = JoinUiState.Failed(exception.message ?: "Kod o'qilmadi")
                )
                return@launch
            }

            try {
                container.provisioning.requestJoin(invitation)
                _state.value = _state.value.copy(join = JoinUiState.Waiting)
            } catch (exception: Exception) {
                _state.value = _state.value.copy(
                    join = JoinUiState.Failed(exception.message ?: "Yuborilmadi")
                )
            }
        }
    }

    /** Jonli sinxronizatsiya aylanishi (ilova ekranda turganda). */
    fun startSync() {
        if (syncJob != null) return
        syncJob = viewModelScope.launch {
            while (true) {
                runCatching { container.runSyncCycle() }
                    .onSuccess { snapshot ->
                        _state.value = _state.value.copy(sync = snapshot)
                        // Ulash javobi asinxron keladi — aylanishda tekshiramiz.
                        when (val result = container.lastJoinResult) {
                            is ProvisioningClient.Result.Joined -> {
                                container.lastJoinResult = null
                                _state.value = _state.value.copy(
                                    join = JoinUiState.Joined(result.role)
                                )
                            }
                            is ProvisioningClient.Result.Failed -> {
                                container.lastJoinResult = null
                                _state.value = _state.value.copy(
                                    join = JoinUiState.Failed(result.reason)
                                )
                            }
                            null -> Unit
                        }
                    }
                delay(SYNC_INTERVAL_MS)
            }
        }
    }

    fun stopSync() {
        syncJob?.cancel()
        syncJob = null
    }

    override fun onCleared() {
        stopSync()
        super.onCleared()
    }

    class Factory(private val context: Context) : ViewModelProvider.Factory {
        @Suppress("UNCHECKED_CAST")
        override fun <T : ViewModel> create(modelClass: Class<T>): T =
            MainViewModel(AppContainer.get(context)) as T
    }

    companion object {
        const val SYNC_INTERVAL_MS = 8_000L

        /** Texnik holat emas, foydalanuvchi tili (desktop bilan bir xil). */
        fun orderStateLabel(state: String): String = when (state) {
            "DRAFT" -> "Qoralama"
            "CONFIRMED" -> "Tasdiqlangan"
            "APPROVED" -> "Ma'qullangan"
            "ALLOCATED" -> "Ajratilgan"
            "PICKED" -> "Yig'ilgan"
            "SHIPPED" -> "Jo'natilgan"
            "DELIVERED" -> "Yetkazilgan"
            "PARTIALLY_RETURNED" -> "Qisman qaytarilgan"
            "RETURNED" -> "Qaytarilgan"
            "CANCELLED" -> "Bekor qilingan"
            else -> state
        }

        fun orderStateTone(state: String): StatusTone = when (state) {
            "DELIVERED" -> StatusTone.OK
            "CANCELLED", "RETURNED" -> StatusTone.ERROR
            "PARTIALLY_RETURNED" -> StatusTone.WARNING
            else -> StatusTone.PROGRESS
        }
    }
}
