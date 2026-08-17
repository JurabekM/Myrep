package uz.buildcontrol.mobile.ui.screens

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import kotlinx.coroutines.launch
import uz.buildcontrol.mobile.BuildControlApp
import uz.buildcontrol.mobile.core.Fmt
import uz.buildcontrol.mobile.core.I18n
import uz.buildcontrol.mobile.core.tr
import uz.buildcontrol.mobile.data.SyncSettings
import uz.buildcontrol.mobile.data.sync.MqttTransport
import uz.buildcontrol.mobile.data.sync.TransportException
import uz.buildcontrol.mobile.domain.CurrentUser
import uz.buildcontrol.mobile.ui.components.BcCard
import uz.buildcontrol.mobile.ui.components.ConfirmDialog
import uz.buildcontrol.mobile.ui.components.Field
import uz.buildcontrol.mobile.ui.components.GhostButton
import uz.buildcontrol.mobile.ui.components.KeyValue
import uz.buildcontrol.mobile.ui.components.Picker
import uz.buildcontrol.mobile.ui.components.PrimaryButton
import uz.buildcontrol.mobile.ui.components.SectionTitle
import uz.buildcontrol.mobile.ui.components.SwitchRow
import uz.buildcontrol.mobile.ui.theme.BcColors

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(user: CurrentUser?, onLogout: () -> Unit, onBack: (() -> Unit)?) {
    val container = BuildControlApp.container
    val scope = rememberCoroutineScope()

    val stored by container.prefs.syncSettings
        .collectAsStateWithLifecycle(initialValue = SyncSettings())
    val syncState by container.sync.state.collectAsStateWithLifecycle()
    val engineState by container.db.syncDao().observeState()
        .collectAsStateWithLifecycle(initialValue = null)
    val pending by container.db.syncDao().observePendingCount()
        .collectAsStateWithLifecycle(initialValue = 0)

    var backend by remember { mutableStateOf(stored.backend) }
    var url by remember { mutableStateOf(stored.url) }
    var apiKey by remember { mutableStateOf(stored.apiKey) }
    var tenant by remember { mutableStateOf(stored.tenant) }
    var deviceName by remember { mutableStateOf(stored.deviceName) }
    var auto by remember { mutableStateOf(stored.auto) }
    var mqttHost by remember { mutableStateOf(stored.mqttHost) }
    var mqttPort by remember { mutableStateOf(stored.mqttPort.toString()) }
    var mqttPrefix by remember { mutableStateOf(stored.mqttPrefix) }
    var mqttTls by remember { mutableStateOf(stored.mqttTls) }
    var passphrase by remember { mutableStateOf(stored.passphrase) }
    var message by remember { mutableStateOf("") }
    var confirmUpload by remember { mutableStateOf(false) }

    LaunchedEffect(stored) {
        backend = stored.backend
        url = stored.url
        apiKey = stored.apiKey
        tenant = stored.tenant
        deviceName = stored.deviceName
        auto = stored.auto
        mqttHost = stored.mqttHost
        mqttPort = stored.mqttPort.toString()
        mqttPrefix = stored.mqttPrefix
        mqttTls = stored.mqttTls
        passphrase = stored.passphrase
    }

    fun current() = SyncSettings(
        backend = backend,
        url = url.trim(),
        apiKey = apiKey.trim(),
        tenant = tenant.trim(),
        deviceName = deviceName.trim(),
        auto = auto,
        mqttHost = mqttHost.trim().ifBlank { MqttTransport.DEFAULT_HOST },
        mqttPort = mqttPort.toIntOrNull() ?: MqttTransport.DEFAULT_PORT,
        mqttPrefix = mqttPrefix.trim().ifBlank { MqttTransport.DEFAULT_PREFIX },
        mqttTls = mqttTls,
        passphrase = passphrase,
    )

    Scaffold(
        containerColor = BcColors.Background,
        topBar = {
            TopAppBar(
                title = { Text(tr("settings")) },
                navigationIcon = {
                    if (onBack != null) {
                        IconButton(onClick = onBack) {
                            Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = BcColors.BackgroundAlt,
                    titleContentColor = BcColors.Text,
                    navigationIconContentColor = BcColors.TextMuted,
                ),
            )
        },
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(14.dp)
        ) {
            if (user != null) {
                BcCard {
                    SectionTitle(user.label)
                    KeyValue(tr("username"), user.username)
                    KeyValue("", I18n.enum("role", user.roleCode))
                    Spacer(Modifier.height(8.dp))
                    GhostButton(tr("logout"), onClick = onLogout, modifier = Modifier.fillMaxWidth())
                }
                Spacer(Modifier.height(12.dp))
            }

            BcCard {
                SectionTitle(tr("language"))
                Picker(
                    tr("language"),
                    listOf("uz" to "O'zbekcha", "en" to "English"),
                    I18n.language,
                    { code ->
                        I18n.apply(code)
                        scope.launch { container.prefs.setLanguage(code) }
                    },
                )
            }
            Spacer(Modifier.height(12.dp))

            BcCard {
                SectionTitle(tr("sync"))
                Text(
                    tr("sync_intro"),
                    style = MaterialTheme.typography.bodySmall,
                    color = BcColors.TextMuted,
                )
                Spacer(Modifier.height(8.dp))
                Picker(
                    tr("sync_backend"),
                    listOf(
                        "off" to tr("sync_off_option"),
                        "mqtt" to tr("sync_mqtt_option"),
                        "supabase" to tr("sync_supabase_option"),
                    ),
                    backend,
                    { backend = it },
                )
                if (backend == "supabase") {
                    Field(tr("sync_url"), url, { url = it })
                    Field(tr("sync_api_key"), apiKey, { apiKey = it })
                }
                if (backend == "mqtt") {
                    Text(
                        tr("mqtt_warning"),
                        style = MaterialTheme.typography.bodySmall,
                        color = BcColors.Warning,
                    )
                    Picker(
                        tr("mqtt_broker"),
                        MqttTransport.PUBLIC_BROKERS.map { (host, port, label) ->
                            "$host:$port" to label
                        } + listOf("" to tr("mqtt_custom")),
                        MqttTransport.PUBLIC_BROKERS
                            .firstOrNull { it.first == mqttHost && it.second.toString() == mqttPort }
                            ?.let { "${it.first}:${it.second}" } ?: "",
                        { chosen ->
                            if (chosen.isNotBlank()) {
                                mqttHost = chosen.substringBefore(':')
                                mqttPort = chosen.substringAfter(':')
                                mqttTls = mqttPort == "8883" || mqttPort == "8886"
                            }
                        },
                    )
                    Field(tr("mqtt_host"), mqttHost, { mqttHost = it })
                    Field(tr("mqtt_port"), mqttPort, { mqttPort = it }, numeric = true)
                    Field(tr("mqtt_prefix"), mqttPrefix, { mqttPrefix = it })
                    SwitchRow(tr("mqtt_tls"), mqttTls, onChange = { mqttTls = it })
                }
                if (backend != "off") {
                    Field(tr("sync_passphrase"), passphrase, { passphrase = it })
                }
                Field(tr("sync_tenant"), tenant, { tenant = it })
                Field(tr("sync_device_name"), deviceName, { deviceName = it })
                SwitchRow(tr("sync_auto"), auto, onChange = { auto = it })
                Text(
                    tr("sync_help"),
                    style = MaterialTheme.typography.labelSmall,
                    color = BcColors.TextFaint,
                )
                Spacer(Modifier.height(10.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    PrimaryButton(
                        tr("save"),
                        onClick = {
                            scope.launch {
                                container.prefs.saveSync(current())
                                container.engine.setDeviceName(deviceName)
                                message = tr("saved")
                            }
                        },
                        modifier = Modifier.weight(1f),
                    )
                    GhostButton(
                        tr("sync_test"),
                        onClick = {
                            scope.launch {
                                message = try {
                                    container.sync.test(current())
                                } catch (exc: TransportException) {
                                    exc.message ?: tr("sync_failed")
                                } catch (exc: Exception) {
                                    exc.message ?: "${tr("sync_failed")}: ${exc.javaClass.simpleName}"
                                }
                            }
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
                if (message.isNotBlank()) {
                    Spacer(Modifier.height(8.dp))
                    Text(
                        message,
                        style = MaterialTheme.typography.bodySmall,
                        color = BcColors.Info,
                    )
                }
            }
            Spacer(Modifier.height(12.dp))

            BcCard {
                SectionTitle(tr("sync_status"))
                KeyValue(
                    tr("sync_status"),
                    when {
                        syncState.running -> tr("sync_running")
                        !stored.enabled -> tr("sync_disabled")
                        syncState.failed -> tr("sync_failed")
                        else -> tr("sync_ok")
                    },
                    when {
                        syncState.running -> BcColors.Warning
                        syncState.failed -> BcColors.Danger
                        stored.enabled -> BcColors.Success
                        else -> BcColors.TextMuted
                    },
                )
                KeyValue(
                    tr("sync_pending"),
                    pending.toString(),
                    if (pending > 0) BcColors.Warning else BcColors.Text,
                )
                KeyValue(tr("sync_last_push"), engineState?.lastPushAt?.let { Fmt.dateTime(it) }
                    ?: tr("sync_never"))
                KeyValue(tr("sync_last_pull"), engineState?.lastPullAt?.let { Fmt.dateTime(it) }
                    ?: tr("sync_never"))
                KeyValue(tr("sync_cursor"), engineState?.cursor?.ifBlank { "—" } ?: "—")
                KeyValue(tr("device_id"), engineState?.deviceId.orEmpty())
                if (!engineState?.lastError.isNullOrBlank()) {
                    Text(
                        engineState?.lastError.orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        color = BcColors.Danger,
                    )
                }
                Spacer(Modifier.height(10.dp))
                PrimaryButton(
                    tr("sync_now"),
                    onClick = { container.sync.syncNow() },
                    enabled = stored.enabled && !syncState.running,
                    modifier = Modifier.fillMaxWidth(),
                )
                Spacer(Modifier.height(6.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    GhostButton(
                        tr("sync_upload_all"),
                        onClick = { confirmUpload = true },
                        modifier = Modifier.weight(1f),
                    )
                    GhostButton(
                        tr("sync_reset"),
                        onClick = {
                            scope.launch {
                                container.engine.resetCursor()
                                message = tr("saved")
                            }
                        },
                        modifier = Modifier.weight(1f),
                    )
                }
            }
            Spacer(Modifier.height(12.dp))

            BcCard {
                SectionTitle(tr("about"))
                KeyValue("BuildControl", "v1.0.0")
                Text(
                    if (I18n.language == "uz") {
                        "Kompyuterdagi BuildControl bilan bir xil ma'lumot bazasi ustida ishlaydi."
                    } else {
                        "Works on the same data as the BuildControl desktop application."
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = BcColors.TextMuted,
                )
            }
            Spacer(Modifier.height(40.dp))
        }
    }

    if (confirmUpload) {
        ConfirmDialog(
            title = tr("sync_upload_all"),
            text = if (I18n.language == "uz") {
                "Telefondagi barcha yozuvlar serverga yuboriladi."
            } else {
                "Every row on this phone will be sent to the server."
            },
            onConfirm = {
                confirmUpload = false
                scope.launch {
                    val queued = container.engine.queueFullUpload()
                    message = "${tr("sync_pending")}: $queued"
                }
            },
            onDismiss = { confirmUpload = false },
        )
    }
}
