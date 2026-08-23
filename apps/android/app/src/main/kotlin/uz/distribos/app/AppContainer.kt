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
import uz.distribos.sync.ProvisioningClient
import uz.distribos.sync.SyncEngine
import uz.distribos.sync.Topics
import java.security.SecureRandom
import android.util.Base64
import android.util.Log

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
    var tenantId: ByteArray
        private set

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

    /** Oxirgi ulash natijasi — UI shuni kuzatadi. */
    @Volatile
    var lastJoinResult: ProvisioningClient.Result? = null

    val engine = SyncEngine(
        dao = database.sync(),
        provider = provider,
        transport = transport,
        projector = projector,
        deviceId = deviceId,
    )

    val provisioning = ProvisioningClient(
        dao = database.sync(),
        provider = provider,
        transport = transport,
        deviceId = deviceId,
        signPublicKey = signKeys.publicKey,
        kemPublicKey = ByteArray(1184),   // ML-KEM hozircha ishlatilmaydi
        onTenantAdopted = ::adoptTenant,
    )

    /**
     * Kompyuterning kompaniyasini qabul qiladi.
     *
     * Ulanishgacha telefonning kompaniya identifikatori vaqtinchalik va
     * tasodifiy. Ulangach u DOIMIY ravishda kompyuternikiga almashadi:
     * topik fazosi, DES-1 muhri va epoch kaliti — hammasi shunga
     * bog'lanadi.
     */
    private fun adoptTenant(adopted: ByteArray) {
        if (adopted.contentEquals(tenantId)) return
        tenantId = adopted
        preferences.edit { putString(KEY_TENANT_ID, adopted.encode()) }
        provider.useTenant(adopted)
        transport.useTenantSpace(Topics.Space.create(adopted, "pilot"))
    }

    /**
     * Qurilma desktopga ulanganmi.
     *
     * Mezon: o'zimizdan boshqa FAOL qurilma bormi. Ulanmagan telefonda
     * birinchi ekran «Ulash» bo'ladi — bo'sh ro'yxatlar emas.
     */
    suspend fun isProvisioned(): Boolean =
        database.sync().activePeerCount(deviceIdHex) > 0

    val deviceIdHex: String = deviceId.joinToString("") { "%02x".format(it) }

    fun observeProvisioned() = database.sync().observeActivePeerCount(deviceIdHex)

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
        if (database.sync().peer(deviceIdHex) == null) {
            database.sync().upsertPeer(
                PeerDeviceEntity(
                    deviceIdHex = deviceIdHex,
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
        // Xato JIMGINA yutilmaydi. Aynan shu `runCatching` reliz
        // build'idagi ulanish nosozligini yashirdi: foydalanuvchi
        // «Internet yo'q» ko'rardi, sabab esa hech qayerda yozilmasdi.
        runCatching { transport.connect() }
            .onFailure { Log.e(TAG, "Brokerga ulanib bo'lmadi", it) }
    }

    /**
     * Oxirgi digest vaqti.
     *
     * Har aylanishda yubormaymiz: digest butun qurilmalar kesimini
     * tashiydi. Kechikish yo'qotish emas — hodisa keyingi almashuvda
     * baribir tiklanadi.
     */
    private var lastDigestAtMs = 0L

    /** Bitta sinxronizatsiya aylanishi. UI holatini qaytaradi. */
    suspend fun runSyncCycle(): SyncState {
        ensureReady()

        // Navbatdagi kelgan xabarlarni qayta ishlaymiz.
        while (true) {
            val (payload, channel) = pendingInbound.poll() ?: break
            if (channel == Topics.Channel.PROTOCOL_CONTROL) {
                // BOOT-1 DES-1 EMAS: ulash paytida epoch kaliti hali yo'q.
                lastJoinResult = provisioning.handleResponse(payload) ?: lastJoinResult
            } else {
                engine.handleInbound(payload, channel)
            }
        }

        engine.publishPending()
        commands.replayPending()

        // Anti-entropiya. Busiz telefon FAQAT o'zi tinglab turgan
        // paytdagi hodisalarni oladi — ulanishdan oldin yoki oflayn
        // paytda kompyuterda yaratilgan hodisalar unga hech qachon yetib
        // bormaydi. Bu aynan jonli sinovda ko'rindi: telefon buyurtmalarni
        // yubordi, lekin kompyuterning mahsulotini olmadi.
        val now = System.currentTimeMillis()
        if (now - lastDigestAtMs >= DIGEST_INTERVAL_MS) {
            lastDigestAtMs = now
            runCatching { engine.sendDigest() }
                .onFailure { android.util.Log.w(TAG, "Digest yuborilmadi", it) }
        }

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
        private const val DIGEST_INTERVAL_MS = 30_000L
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
