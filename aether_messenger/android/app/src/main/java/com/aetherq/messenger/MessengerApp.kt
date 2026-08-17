package com.aetherq.messenger

import android.app.Application
import android.content.Context
import com.aetherq.messenger.crypto.Identity
import com.aetherq.messenger.crypto.IdentityStore
import com.aetherq.messenger.data.MessengerRepository
import com.aetherq.messenger.data.SessionManager
import com.aetherq.messenger.data.local.AppDatabase
import com.aetherq.messenger.mqtt.MqttClient

/** Hilt'siz, qo'lda ulanadigan (manual DI) qaramliklar konteyneri — PoC uchun yetarli. */
class AppContainer(context: Context) {
    val identity: Identity = IdentityStore(context).getOrCreate()
    val database: AppDatabase = AppDatabase.build(context)
    val sessionManager: SessionManager = SessionManager()
    val mqttClient: MqttClient = MqttClient(identity.userId)
    val repository: MessengerRepository =
        MessengerRepository(
            identity = identity,
            contactDao = database.contactDao(),
            messageDao = database.messageDao(),
            sessionManager = sessionManager,
            mqttClient = mqttClient,
        )
}

class MessengerApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
