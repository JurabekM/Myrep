package com.aetherq.messenger.crypto

import kotlinx.serialization.Serializable
import kotlinx.serialization.decodeFromString
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json

/** QR-kod orqali almashiladigan ochiq kalitlar to'plami (Signal safety-number uslubida). */
@Serializable
data class ContactCard(
    val userId: String,
    val edPk: String,
    val xPk: String,
    val mlkemPk: String,
)

object ContactCardCodec {
    private val json = Json { ignoreUnknownKeys = true }

    fun encode(card: ContactCard): String = json.encodeToString(card)

    fun decode(raw: String): ContactCard = json.decodeFromString(raw)

    fun fromIdentity(identity: Identity): ContactCard =
        ContactCard(
            userId = identity.userId,
            edPk = identity.edPk.toHex(),
            xPk = identity.xPk.toHex(),
            mlkemPk = identity.mlkemPk.toHex(),
        )
}
