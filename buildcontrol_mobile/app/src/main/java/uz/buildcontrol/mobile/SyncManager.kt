package uz.buildcontrol.mobile

import android.util.Log
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import uz.buildcontrol.mobile.data.Prefs
import uz.buildcontrol.mobile.data.SyncSettings
import uz.buildcontrol.mobile.data.sync.DisabledTransport
import uz.buildcontrol.mobile.data.sync.MqttTransport
import uz.buildcontrol.mobile.data.sync.SupabaseTransport
import uz.buildcontrol.mobile.data.sync.SyncEngine
import uz.buildcontrol.mobile.data.sync.SyncTransport
import uz.buildcontrol.mobile.data.sync.TransportException

/** Drives replication rounds and exposes their state to the interface. */
class SyncManager(
    private val engine: SyncEngine,
    private val prefs: Prefs,
    private val scope: CoroutineScope,
) {
    data class UiState(
        val running: Boolean = false,
        val lastReport: SyncEngine.Report? = null,
        val lastMessage: String = "",
        val failed: Boolean = false,
    )

    private val _state = MutableStateFlow(UiState())
    val state: StateFlow<UiState> = _state.asStateFlow()

    private val mutex = Mutex()

    fun buildTransport(settings: SyncSettings): SyncTransport = when (settings.backend) {
        "mqtt" -> MqttTransport(
            host = settings.mqttHost,
            port = settings.mqttPort,
            tenant = settings.tenant,
            prefix = settings.mqttPrefix,
            useTls = settings.mqttTls,
            username = settings.mqttUser,
            password = settings.mqttPassword,
            passphrase = settings.passphrase,
        )
        "supabase" -> SupabaseTransport(settings.url, settings.apiKey, settings.tenant)
        else -> DisabledTransport
    }

    /**
     * Verify the configuration without touching local data.
     *
     * Runs off the main thread: OkHttp refuses network calls there and the
     * resulting [android.os.NetworkOnMainThreadException] carries no message.
     */
    suspend fun test(settings: SyncSettings): String = withContext(Dispatchers.IO) {
        val transport = buildTransport(settings)
        try {
            transport.check()
        } finally {
            (transport as? MqttTransport)?.close()
        }
    }

    fun syncNow(onFinished: ((SyncEngine.Report) -> Unit)? = null) {
        scope.launch(Dispatchers.IO) {
            if (mutex.isLocked) return@launch
            mutex.withLock {
                val settings = prefs.currentSync()
                if (!settings.enabled) {
                    _state.value = UiState(lastMessage = "sync_disabled")
                    return@withLock
                }
                _state.value = _state.value.copy(running = true, lastMessage = "sync_running")
                val transport = buildTransport(settings)
                val report = try {
                    engine.synchronize(transport)
                } catch (exc: Exception) {
                    Log.e("SyncManager", "sync failed", exc)
                    SyncEngine.Report().apply { errors.add(exc.message ?: "error") }
                } finally {
                    // MQTT holds a socket for the round; HTTP backends are stateless.
                    (transport as? MqttTransport)?.close()
                }
                _state.value = UiState(
                    running = false,
                    lastReport = report,
                    lastMessage = if (report.ok) report.summary() else report.errors.first(),
                    failed = !report.ok,
                )
                onFinished?.invoke(report)
            }
        }
    }

    /** Called when the app comes to the foreground. */
    fun syncIfAuto() {
        scope.launch {
            val settings = prefs.currentSync()
            if (settings.enabled && settings.auto) syncNow()
        }
    }
}
