package uz.distribos.app

import android.app.Application
import android.content.Context
import android.content.SharedPreferences
import androidx.core.content.edit
import uz.distribos.app.ui.SyncState
import uz.distribos.crypto.MlDsa65
import uz.distribos.data.db.DistribosDatabase
import uz.distribos.data.db.PeerDeviceEntity
import uz.distribos.sync.AndroidAetherQProvider
import uz.distribos.sync.CommandService
import uz.distribos.sync.EventProjector
import uz.distribos.sync.KeyVault
import uz.distribos.sync.KeystoreVault
import uz.distribos.sync.MqttTransport
import uz.distribos.sync.SyncEngine
import uz.distribos.sync.Topics
import java.security.SecureRandom
import android.util.Base64

/**
 * Bog'lash nuqtasi (composition root).
 *
 * Hilt ishlatilmadi: bu ilovada bog'liqliklar soni kam va ular ILOVA
 * UMRI davomida bitta nusxada yashaydi. Qo'lda bog'lash bu yerda
 * soddaroq va build vaqtini annotation processor bilan uzaytirmaydi.
 */
class AppContainer private constructor(context: Context) {

    private val appContext = context.applicationContext
    private val preferences: SharedPreferences =
        appContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)

    val database: DistribosDatabase = DistribosDatabase.build(appContext)
    val keyVault: KeyVault = KeystoreVault()

    /** Qurilma identiteti — birinchi ishga tushishda yaratiladi. */
    val deviceId: ByteArray
    private val signKeys: MlDsa65.KeyPair

    val role: String get() = preferences.getString(KEY_ROLE, "agent") ?: "agent"
    val tenantId: ByteArray

    init {
        val stored = preferences.getString(KEY_DEVICE_ID, null)
        if (stored == null) {
            deviceId = ByteArray(16).also { SecureRandom().nextBytes(it) }
            tenantId = ByteArray(16).also { SecureRandom().nextBytes(it) }
            signKeys = MlDsa65.generate()

            // Maxfiy kalit Keystore bilan O'RALGAN holda saqlanadi —
            // ochiq ko'rinishda hech qachon diskda yotmaydi.
            preferences.edit {
                putString(KEY_DEVICE_ID, deviceId.encode())
                putString(KEY_TENANT_ID, tenantId.encode())
                putString(KEY_SIGN_PUBLIC, signKeys.publicKey.encode())
                putString(
                    KEY_SIGN_PRIVATE,
                    keyVault.wrap(signKeys.privateKey, IDENTITY_CONTEXT).encode(),
                )
            }
        } else {
            deviceId = stored.decode()
            tenantId = preferences.getString(KEY_TENANT_ID, null)!!.decode()
            signKeys = MlDsa65.KeyPair(
                publicKey = preferences.getString(KEY_SIGN_PUBLIC, null)!!.decode(),
                privateKey = keyVault.unwrap(
                    preferences.getString(KEY_SIGN_PRIVATE, null)!!.decode(), IDENTITY_CONTEXT
                ),
            )
        }
    }

    val provider = AndroidAetherQProvider(
        dao = database.sync(),
        tenantId = tenantId,
        deviceId = deviceId,
        signPublicKey = signKeys.publicKey,
        signPrivateKey = signKeys.privateKey,
        keyVault = keyVault,
    )

    val projector = EventProjector(database)

    val commands = CommandService(
        database = database,
        projector = projector,
        deviceId = deviceId,
        actorId = preferences.getString(KEY_ACTOR_ID, null),
        role = role,
    )

    private val brokerSettings = MqttTransport.BrokerSettings()

    private val transport = MqttTransport(
        settings = brokerSettings,
        topics = Topics.Space.create(tenantId, "pilot"),
        deviceId = deviceId,
        onMessage = { payload, channel -> pendingInbound.add(payload to channel) },
    )

    /**
     * Kelgan xabarlar navbati.
     *
     * MQTT callback'i Netty oqimida chaqiriladi va u yerda `suspend`
     * funksiya chaqirib bo'lmaydi. Shuning uchun xabar navbatga tushadi
     * va sinxronizatsiya aylanishida qayta ishlanadi.
     */
    private val pendingInbound =
        java.util.concurrent.ConcurrentLinkedQueue<Pair<ByteArray, Topics.Channel?>>()

    val engine = SyncEngine(
        dao = database.sync(),
        provider = provider,
        transport = transport,
        projector = projector,
        deviceId = deviceId,
    )

    suspend fun ensureReady() {
        // Namuna ma'lumot FAQAT debug build'da. Reliz build'da
        // foydalanuvchi bo'sh bazadan boshlaydi.
        if (BuildConfig.DEBUG) {
            // Xato JIMGINA yutilmaydi: aynan shu `runCatching` namuna
            // ma'lumot yozilmayotganini yashirib turgan edi (agentda
            // mahsulot yaratish vakolati yo'q).
            runCatching { DemoData.seedIfEmpty(database, commands) }
                .onFailure { android.util.Log.e(TAG, "Namuna ma'lumot yozilmadi", it) }
        }
        if (database.sync().currentEpochKey() == null) {
            provider.rotateKeys()
        }
        // O'z-o'zini reyestrga qo'shamiz: o'z hodisalarimizni ham
        // proyektor bir xil yo'ldan qo'llaydi.
        val hex = deviceId.joinToString("") { "%02x".format(it) }
        if (database.sync().peer(hex) == null) {
            database.sync().upsertPeer(
                PeerDeviceEntity(
                    deviceIdHex = hex,
                    displayName = "Bu telefon",
                    platform = "android",
                    role = role,
                    state = "ACTIVE",
                    signPublicKey = signKeys.publicKey,
                    kemPublicKey = ByteArray(0),
                    lastSeenAtMs = System.currentTimeMillis(),
                    lastAppliedSequence = 0,
                    isFullReplica = false,
                    revokedReason = null,
                )
            )
        }
    }

    fun connect() {
        runCatching { transport.connect() }
    }

    /** Bitta sinxronizatsiya aylanishi. UI holatini qaytaradi. */
    suspend fun runSyncCycle(): SyncState {
        ensureReady()

        // Navbatdagi kelgan xabarlarni qayta ishlaymiz.
        while (true) {
            val (payload, channel) = pendingInbound.poll() ?: break
            engine.handleInbound(payload, channel)
        }

        engine.publishPending()
        commands.replayPending()

        val (queued, dead) = engine.queueDepth()
        val epoch = database.sync().currentEpochKey()?.epoch ?: 0
        val devices = database.sync().digest().size

        return SyncState(
            connected = transport.isConnected(),
            queued = queued,
            deadLetters = dead,
            devices = devices,
            publicPilot = brokerSettings.isPublicPilot,
            protocolVersion = "5.1.0",
            epoch = epoch,
        )
    }

    private fun ByteArray.encode(): String = Base64.encodeToString(this, Base64.NO_WRAP)

    private fun String.decode(): ByteArray = Base64.decode(this, Base64.NO_WRAP)

    companion object {
        private const val TAG = "DistribOS"
        private const val PREFS = "distribos_identity"
        private const val KEY_DEVICE_ID = "device_id"
        private const val KEY_TENANT_ID = "tenant_id"
        private const val KEY_SIGN_PUBLIC = "sign_public"
        private const val KEY_SIGN_PRIVATE = "sign_private"
        private const val KEY_ROLE = "role"
        private const val KEY_ACTOR_ID = "actor_id"

        private val IDENTITY_CONTEXT = "DistribOS/device-identity/v1".toByteArray()

        @Volatile
        private var instance: AppContainer? = null

        fun get(context: Context): AppContainer =
            instance ?: synchronized(this) {
                instance ?: AppContainer(context).also { instance = it }
            }
    }
}

class DistribosApplication : Application() {
    override fun onCreate() {
        super.onCreate()
        // Ulanishni ilova ishga tushishida boshlaymiz, lekin UI uni
        // KUTMAYDI — ilova ulanishsiz ham to'liq ishlaydi.
        AppContainer.get(this).connect()
    }
}
